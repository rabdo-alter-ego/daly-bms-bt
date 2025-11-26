import asyncio
import json

from bleak import BleakClient
from parser import parse_bms_message

from splunk import create_splunk_event, post_to_splunk


DEVICE_ADDRS = [
    "41:19:06:01:65:82",  #5 #25  #bms1
    "41:19:06:01:36:59",  #4 #23  #bms2
    "41:19:06:01:71:60"   #3 #23  #bms3
]

NOTIFY_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"  # 0x0010
WRITE_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"   # 0x0014

# Full sequence from final logs
WRITES = [
    "d20300800029965f",
    "d2030000003ed7b9",
]



async def handle_device(addr):
    async with BleakClient(addr) as client:
        def handle_notification(sender, data):
            print(f"[{addr}] {data.hex()}")
            results = parse_bms_message(data.hex())
            for result in results:
                print(f"\n\t✅ **PARSING RESULT ({addr}) sender: {sender}**")
                print(json.dumps(result, indent=4))

        await client.start_notify(NOTIFY_CHAR_UUID, handle_notification)

        # Send writes sequentially
        for w in WRITES:
            await client.write_gatt_char(WRITE_CHAR_UUID, bytes.fromhex(w))
            await asyncio.sleep(0.1)

        # Wait for notifications
        await asyncio.sleep(10)
        await client.stop_notify(NOTIFY_CHAR_UUID)


async def main():
    # Create one task per device
    tasks = [asyncio.create_task(handle_device(addr)) for addr in DEVICE_ADDRS]
    # Run them all concurrently
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())