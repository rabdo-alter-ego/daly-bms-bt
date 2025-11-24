"""
bms_error_decoder.py - Funzioni e costanti per la decodifica degli allarmi Daly.
**MODIFIED**: Adopts the 16-bit inverted mapping (15 - iNumber) from the Kotlin code.
"""

# --- MAPPATURA CODICI DI ERRORE COMPLETA (16-bit / Register) ---
# Each list now corresponds to a full 16-bit register (R58, R59, R60, R61)
# and contains 16 elements, ordered by the CASE INDEX (0 to 15) which
# corresponds to the inverted bit position (Bit 15 -> Case 0, Bit 0 -> Case 15).
# The original "Gruppo" names are used as comments for reference.

ERROR_REGISTERS = {
    # REGISTER 1 (R58) - Tensione/Temperatura (MANTENUTO)
    1: [
        # Case 0-7: Tensione Cella/Totale
        "Cell Over Voltage (Stage 1)", "Cell Over Voltage (Stage 2)", "Cell Under Voltage (Stage 1)",
        "Cell Under Voltage (Stage 2)",
        "Total Voltage Too High (Stage 1)", "Total Voltage Too High (Stage 2)", "Total Voltage Too Low (Stage 1)",
        "Total Voltage Too Low (Stage 2)",
        # Case 8-15: Temperatura Carica/Scarica
        "Charging Temp Too High (Stage 1)", "Charging Temp Too High (Stage 2)", "Charging Temp Too Low (Stage 1)",
        "Charging Temp Too Low (Stage 2)",
        "Discharge Temp Too High (Stage 1)", "Discharge Temp Too High (Stage 2)", "Discharge Temp Too Low (Stage 1)",
        "Discharge Temp Too Low (Stage 2)",
    ],

    # REGISTER 2 (R59) - Corrente/SOC/Differenziale (INVERSIONE APPLICATA)
    2: [
        # Case 0-5 (Bit 15-10): Corrente/SOC Too High (Mantenuto)
        "Charge Over Current (Stage 1)",
        "Charge Over Current (Stage 2)",
        "Discharge Over Current (Stage 1)",
        "Discharge Over Current (Stage 2)",
        "SOC Too High (Stage 1)",
        "SOC Too High (Stage 2)",

        # ******** INVERSIONE Case 6-7 (Bit 9-8) con Case 8-9 (Bit 7-6) ********
        # Case 6/7 ora sono Differenziale Tensione (prima era SOC Too Low)
        "Excessive Differential Voltage (Stage 1)",  # <--- Mappato a Bit 9
        "Excessive Differential Voltage (Stage 2)",  # <--- Mappato a Bit 8

        # Case 8/9 ora sono SOC Too Low (prima era Differenziale Tensione)
        "SOC Too Low (Stage 2)",  # <--- Mappato a Bit 7 (Attivo nei tuoi dati)
        "SOC Too Low (Stage 1)",  # <--- Mappato a Bit 6 (Attivo nei tuoi dati)
        # ************************************************************************

        # Case 10-15 (Bit 5-0): Resto (Mantenuto)
        "Excessive Temperature Difference (Stage 1)",
        "Excessive Temperature Difference (Stage 2)",
        "RESERVED",
        "RESERVED",
        "RESERVED",
        "RESERVED",
    ],

    # REGISTER 3 (R60) - MOS/Chip (MANTENUTO)
    3: [
        "AFE Acquisition Chip Malfunction", "Single Cell Collection Drop Off", "Single Temperature Sensor Fault",
        "EEPROM Storage Failure",
        "RTC Clock Malfunction", "Precharge Failure", "Vehicle Communications Malfunction",
        "Intranet Communication Module Malfunction",
        "Charging MOS Over-temperature Warning", "Discharge MOS Over-temperature Warning",
        "Charging MOS Temperature Sensor Failure",
        "Discharge MOS Temperature Sensor Failure", "Charging MOS Adhesion Failure", "Discharge MOS Adhesion Failure",
        "Charging MOS Breaker Failure", "Discharge MOS Breaker Failure",
    ],

    # REGISTER 4 (R61) - Moduli/Riservato (MANTENUTO)
    4: [
        "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED", "RESERVED",
        "Current Module Failure", "Main Pressure Detection Module Failure", "Short Circuit Protection Failure",
        "Low Voltage No Charging",
        "RESERVED", "RESERVED", "RESERVED", "RESERVED",
    ],
}


# --- FUNZIONE DI DECODIFICA ERRORI MODIFICATA ---
def decode_bms_alarms(r58_value, r59_value, r60_value, r61_value):
    """
    Decodifica i registri di allarme (R58-R61) applicando la logica di
    mappatura invertita a 16-bit (15 - iNumber) del codice Kotlin.
    """
    active_alarms = []

    registers = {
        1: r58_value,
        2: r59_value,
        3: r60_value,
        4: r61_value
    }

    for reg_number, reg_value in registers.items():
        if reg_number in ERROR_REGISTERS:
            alarm_map = ERROR_REGISTERS[reg_number]

            # Itera su tutti i 16 bit
            for iNumber in range(16):
                # 1. Verifica se il bit è attivo (allarme attivo)
                if (reg_value >> iNumber) & 1:

                    # 2. **APPLICA LA MAPPATURA INVERTITA** (Cruciale per il matching con Kotlin)
                    # iNumber 15 -> Case 0
                    # iNumber 0 -> Case 15
                    case_index = 15 - iNumber

                    # 3. Cerca il messaggio d'allarme corrispondente nell'indice Case
                    if case_index < len(alarm_map):
                        alarm_message = alarm_map[case_index]
                        # Aggiungi l'allarme attivo con le sue coordinate
                        active_alarms.append(f"R{reg_number} Bit {iNumber} (Case {case_index}): {alarm_message}")

    return active_alarms