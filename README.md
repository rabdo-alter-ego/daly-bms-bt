# daly-bms-bt
This repo demostrates how to connect and parse most of the live data coming from a daly-bms device using bleak library.

# installation
    pip3 install bleak

# changes
Modify the script executor.py (or parallel_executor.py if you have more than 1 device)

# usage
    python3 executor.py
    or
    python3 parallel_executor.py


<img width="720" height="1280" alt="immagine" src="https://github.com/user-attachments/assets/af4db66a-b6d3-419c-bbb0-8a39aaf06287" />

# Hardware
In order to use the script you need a device like mine in the photo, i have 3 of them and i can provide more information about them if needed: 
- 16s
- 200A charge
- 200A discharge
- internal passive balancer
- parallel support (dio port)
- dual uart port (1 and 2)
- dual ntc port (A and B)

# data extracted
I successfully extracted most of the live data I was able to see in the app (who cares about for example SN number if it doesn t change at all?)
- rated_capacity_Ah (max batteries capacity)
- cell_number (total number of batteries)
- charge_enabled (charge mos switch)
- discharge_enabled (discharge mos switch)
- cell_voltages_V (all cells voltage)
- max_cell_V (max cell)
- min_cell_V (min cell)
- delta_V (cell max difference)
- temperatures_C (temperatures array based on number of temp sensor)
- total_voltage_V (pack total voltage)
- current_A (current flowing from/to pack)
- status (Charging, Idle or Discharging)
- soc
- cycle_count (number of cycles of the pack)
- group alarm codes (alarm_R58, alarm_R59, alarm_R60, alarm_R61)
- 2 alarm messages from the group R59 (SOC Too Low (Stage 1), SOC Too Low (Stage 2)). This message were the only one i could see in the app

# data not extracted
I was still not able to extract some live data and I really like to have it extracted in my script:
- MOS_temperature_C
- All alarm messages except for SOC Too Low (Stage 1) and SOC Too Low (Stage 2)
- CRC: there should be a "checksum of a message" for each response sent from the bms

# Motivation
I have a solar panel System with 3 lithium batteries packs in parallel composed each by 16 batteries in series. For almost 2 years I was able to connect all of them in parallel using 3 daly-bms without parallel module; I don't suggest this! I knew the risks and accepted them (1 or more packs can unbalance and disconnect from others reconnecting when done and risking high dangerous current flow between packs).

I was able to monitor the system via bluetooth so I could see if 1 of the pack disconnected and quickly intervene using:
- https://github.com/dreadnought/python-daly-bms
- https://github.com/KevinEeckman/python-daly-bms .
After 2 years i finally decided to use parallel bms just to be extra safe. I bought 3 new bms (my old ones didn t had the DIO port necessary for parallel module) and 3 daly parallel systems! After the assebly I found out my old script was unusable on new devices (i just keep getting this error: "cannot read characteristic 17"), so I rolled up my sleeves and reversed engeneer this script inspecting android hci snoop logs (with wireshark) and destructuring their apk with jadx
