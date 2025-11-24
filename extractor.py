import asyncio
import json

from bleak import BleakClient
from parser import parse_bms_message

from splunk import create_splunk_event, post_to_splunk


DEVICE_ADDR2 = "41:19:06:01:71:60" #3 #23  #bms3
DEVICE_ADDR3 = "41:19:06:01:36:59" #4 #23  #bms2
DEVICE_ADDR = "41:19:06:01:65:82"  #5 #25  #bms1


NOTIFY_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"  # 0x0010
WRITE_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"   # 0x0014

# Full sequence from final logs
WRITES = [
    "d20300800029965f",
    "d2030000003ed7b9",
]


async def main():
    event_list = []
    async with BleakClient(DEVICE_ADDR) as client:
        # Handle notifications exactly like in logs

        def handle_notification(sender, data):
            print(data.hex())
            results = parse_bms_message(data.hex())
            event = create_splunk_event({**results, "mac": sender})
            nonlocal event_list
            event_list.append(event)
            for result in results:
                print("\n\t✅ **PARSING RESULT**")
                print(json.dumps(result, indent=4))

        await client.start_notify(NOTIFY_CHAR_UUID, handle_notification)

        # Send each write in sequence
        for w in WRITES:
            await client.write_gatt_char(WRITE_CHAR_UUID, bytes.fromhex(w))
            await asyncio.sleep(0.1)

        # Give device time to send all notifications
        await asyncio.sleep(10)
        await client.stop_notify(NOTIFY_CHAR_UUID)
        post_to_splunk(event_list)


asyncio.run(main())
