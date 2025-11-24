import struct
import json
from collections import defaultdict

from error_codes import decode_bms_alarms



# --- FUNZIONE DI UTILITÀ ---
def hex_to_int16_be(hex_string):
    """Converte una stringa esadecimale di 4 caratteri (2 byte) in un intero senza segno (Big Endian, >H)."""
    if len(hex_string) != 4:
        if len(hex_string) < 4:
            return 0
        raise ValueError(f"Attesi 4 caratteri esadecimali, ottenuti {len(hex_string)}: {hex_string}")
    try:
        # '>H' significa Big Endian (>) Short Intero Senza Segno (H, 2 byte)
        return struct.unpack('>H', bytes.fromhex(hex_string))[0]
    except Exception as e:
        # L'errore verrà intercettato durante l'analisi del pacchetto
        return 0


def format_batteries(cell_voltages):
    return {
        key.lstrip("C"): value
        for key, value in cell_voltages.items()
        if value > 0
    }


# --- FUNZIONI DI ANALISI ---
def parse_set_data_52(payload):
    """
    Analizza il payload per il comando '52' (Info Dati di Configurazione).
    I dati di configurazione vengono analizzati in Big Endian.
    """
    print("\n\t--- Analisi Dati di Configurazione (52) ---")
    data_points = defaultdict(str)

    registers = []
    # Tutti i registri del Comando 52 usano Big Endian
    for i in range(0, len(payload), 4):
        hex_reg = payload[i:i + 4]
        registers.append(hex_to_int16_be(hex_reg))

    # Il payload inizia al Registro R44
    REG_OFFSET = 44

    def get_reg_value(r_num):
        index = r_num - REG_OFFSET
        if index < 0 or index >= len(registers):
            return None
        return registers[index]

    # --- Registri di Configurazione (R44-R79) ---

    # R44: Capacità Nominale (Ah) - x0.001
    r44 = get_reg_value(44)
    if r44 is not None:
        # Valore grezzo 3100 -> 3.1 Ah
        data_points["rated_capacity_Ah"] = round(r44 * 0.001, 3)

    # R47: Numero di Celle
    r47 = get_reg_value(47)
    if r47 is not None:
        # Valore grezzo 16 -> 16 Celle
        data_points["cell_number"] = r47

    # R64: Abilitazione Carica/Scarica (Bitmask)
    r64 = get_reg_value(64)
    if r64 is not None:
        data_points["charge_enabled"] = bool(r64 & 0x01)
        data_points["discharge_enabled"] = bool(r64 & 0x02)

    print(f"\tTotale Registri Trovati: {len(registers)}")
    print(f"\tRegistri Grezzi (primi 20): {registers[:20]}")

    return dict(data_points)


def parse_run_data_7c(payload):
    """
    Analizza il payload per il comando '7C' (Info Dati di Esecuzione).
    Utilizza Big Endian per tutti i registri.

    NOTA: In base ai dati forniti, questo BMS invia solo 62 registri (R0-R61).
    L'aspettativa minima è regolata a 62.
    """
    print("\n\t--- Analisi Dati di Esecuzione (7C) ---")
    data_points = defaultdict(str)

    # 1. Converte il payload in una lista di registri interi a 16 bit usando Big Endian
    registers = []
    for i in range(0, len(payload), 4):
        hex_reg = payload[i:i + 4]
        # Logica Big Endian per i dati di esecuzione 7C
        registers.append(hex_to_int16_be(hex_reg))

    # Imposta i registri minimi attesi a 62 (R0 a R61), in base ai dati osservati.
    EXPECTED_MIN_REGISTERS = 62

    if len(registers) < EXPECTED_MIN_REGISTERS:
        data_points[
            "Error"] = f"Dati insufficienti per i dati di esecuzione (attesi almeno {EXPECTED_MIN_REGISTERS} registri, ottenuti {len(registers)})"
        data_points["Raw_Registers_Count"] = len(registers)
        return dict(data_points)

    # 2. Estrai le Tensioni delle Celle (Registri 0-31)
    cell_voltages_raw = registers[0:32]
    data_points["cell_voltages_V"] = {f'{i + 1}': round(v * 0.001, 3) for i, v in enumerate(cell_voltages_raw) if v > 0}
    data_points["max_cell_V"] = round(max(cell_voltages_raw) * 0.001, 3)
    data_points["min_cell_V"] = round(min(cell_voltages_raw) * 0.001, 3)
    data_points["delta_V"] = round((max(cell_voltages_raw) - min(cell_voltages_raw)) * 0.001, 3)

    # 3. Estrai le Temperature (Registri 32-39, 8 sensori) - Valore - 40
    temp_raw = registers[32:40]
    data_points["temperatures_C"] = {f'T{i + 1}': t - 40 for i, t in enumerate(temp_raw)}

    mosfet_temp_raw = registers[33] if len(registers) > 33 else 0  # Use T2 (R33) as a guess

    if mosfet_temp_raw > 0:
        data_points["MOS_temperature_C"] = mosfet_temp_raw - 40
    else:
        # Use the original N/A if T2 is 0 or packet is too short
        data_points["MOS_temperature_C"] = "N/A (R66/Misaligned)"

    # 4. Estrai i Valori di Stato Generali

    # R40: Tensione Totale - x0.001
    data_points["total_voltage_V"] = round(registers[40] / 10, 3)

    # R41: Corrente - (Valore - 30000) * 0.1
    current_raw = registers[41]
    current_A = (current_raw - 30000) * 0.1
    data_points["current_A"] = round(current_A, 2)
    data_points["status"] = 'Charging' if current_A > 0.01 else ('Discharging' if current_A < -0.01 else 'Idle')

    # R42: SOC / Capacità Residua - x0.1
    data_points["soc"] = round(registers[42] * 0.1, 1)

    tail = bytes.fromhex(payload)[-32:]   # adjust length if needed

    # Cycle count is at offset 10 (0x0A)
    cycle_count = int.from_bytes(tail[10:12], byteorder='big')

    data_points["cycle_count"] = cycle_count


    # 5. Estrai le Informazioni di Allarme (Registri 58-61)
    r58_val = registers[58] if len(registers) > 58 else 0
    r59_val = registers[59] if len(registers) > 59 else 0
    r60_val = registers[60] if len(registers) > 60 else 0
    r61_val = registers[61] if len(registers) > 61 else 0

    data_points["alarm_R58"] = f"{r58_val:016b}"
    data_points["alarm_R59"] = f"{r59_val:016b}"
    data_points["alarm_R60"] = f"{r60_val:016b}"
    data_points["alarm_R61"] = f"{r61_val:016b}"

    data_points["decoded_alarms"] = decode_bms_alarms(r58_val, r59_val, r60_val, r61_val)

    print(f"\tTotale Registri Trovati: {len(registers)}")
    print(f"\tRegistri Grezzi (primi 45): {registers[:45]}")

    if len(registers) == EXPECTED_MIN_REGISTERS:
        data_points[
            "Warning"] = "Trovati solo 62 registri (R0-R61). I dati sono troncati rispetto alla specifica completa (R0-R66)."

    return dict(data_points)


def parse_bms_message(hex_message):
    """Funzione principale per pulire e inviare il messaggio esadecimale al parser corretto."""

    packets = []
    parts = hex_message.split('d203')

    for part in parts:
        if part and part.strip():
            if len(part) >= 6:
                packets.append('d203' + part)

    # ⛔ ERROR: no valid packets found
    if not packets:
        raise ValueError("Nessun pacchetto valido che inizia con 'd203' trovato.")

    results = []

    for packet in packets:
        command_code_hex = packet[4:6].upper()
        payload = packet[6:-4]

        # ⛔ ERROR: empty or invalid payload
        if len(payload) < 2:
            raise ValueError(f"Payload vuoto o troppo corto nel pacchetto: {packet}")

        if command_code_hex == '52':
            data = parse_set_data_52(payload)
            data["Command"] = "SET_INFO (52)"
            results.append(data)

        elif command_code_hex == '7C':
            data = parse_run_data_7c(payload)
            data["Command"] = "RUN_INFO (7C)"
            results.append(data)

        else:
            # ⛔ ERROR: unknown command
            raise ValueError(f"Comando BMS sconosciuto: {command_code_hex}")

    # ⛔ ERROR: parser returned nothing useful
    if not results:
        raise ValueError("Impossibile decodificare alcun pacchetto valido.")

    return results


if __name__ == "__main__":
    # --- Dati di Input (Replicati per il controllo finale) ---
    HEX_MESSAGE_1 = "d203520c1c0c80000100100000000000020000000000000e100dac0e100a2809c4022f023f01aa019a6ef06d607b707d0000640069000a00050069006e000a000501f40320000a000f0d4800140001000100310057c197"
    HEX_MESSAGE_2 = "d203520c1c0c80000100100000000000020000000000000e100dac0e100a2809c4022f023f01aa019a6ef06d607b707d0000640069000a00050069006e000a000501f40320000a000f0d48001400010001005700572188d2037c0c740c7f0c7f0c7f0c7f0c800c800c7f0c7e0c7e0c7e0c800c7e0c7e0c7e0c7c0000000000000000000000000000000000000000000000000000000000000000003f003f00ff00ff00ff00ff00ff00ff01ff753000570c800c74003f003f0000010d0010000200020000000100010c7e000c0000000000800000000065a9d2037c0c740c7f0c7f0c7f0c7f0c800c800c7f0c7e0c7e0c7e0c800c7e0c7e0c7e0c7c0000000000000000000000000000000000000000000000000000000000000000003f003f00ff00ff00ff00ff00ff00ff01ff753000570c800c74003f003f0000010d0010000200020000000100010c7e000c0000000000800000000065a9d2037c0c740c7f0c7f0c7f0c7f0c800c800c7f0c7e0c7e0c7e0c800c7e0c7e0c7e0c7c0000000000000000000000000000000000000000000000000000000000000000003f003f00ff00ff00ff00ff00ff00ff01ff753000570c800c74003f003f0000010d0010000200020000000100010c7e000c00000000008000000000d757d2037c0c740c7f0c7f0c7f0c7f0c800c800c7f0c7e0c7e0c7e0c800c7e0c7e0c7e0c7c0000000000000000000000000000000000000000000000000000000000000000003f003f00ff00ff00ff00ff00ff00ff01ff753000570c800c74003f003f0000010d0010000200020000000100010c7e000c00000000008000000000d757d2037c0c740c7f0c7f0c7f0c7f0c800c800c7f0c7e0c7e0c7e0c800c7e0c7e0c7e0c7c0000000000000000000000000000000000000000000000000000000000000000003f003f00ff00ff00ff00ff00ff00ff01ff753000570c800c74003f003f0000010d0010000200020000000100010c7e000c00000000008000000000b560d2037c0c740c7f0c7f0c7f0c7f0c800c800c7f0c7e0c7e0c7e0c800c7e0c7e0c7e0c7c0000000000000000000000000000000000000000000000000000000000000000003f003f00ff00ff00ff00ff00ff00ff01ff753000570c800c74003f003f0000010d0010000200020000000100010c7e000c00000000008000000000b560"

    # --- Execution ---
    print("--- STARTING BMS DATA PARSING ---")

    print("\n\n--- Processing Message 1 (Configuration Data) ---")
    results1 = parse_bms_message(HEX_MESSAGE_1)
    for result in results1:
        print("\n\t✅ **PARSING RESULT**")
        print(json.dumps(result, indent=4))

    print("\n" + "=" * 50 + "\n")

    print("\n\n--- Processing Message 2 (Real-time & Configuration Data) ---")
    results2 = parse_bms_message(HEX_MESSAGE_2)
    for result in results2:
        print("\n\t✅ **PARSING RESULT**")
        print(json.dumps(result, indent=4))