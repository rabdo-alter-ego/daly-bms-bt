import asyncio
import json

from bleak import BleakClient
from parser import parse_bms_message
from splunk import create_splunk_event, post_to_splunk

DEVICE_ADDRS = [
    "41:19:06:01:65:82",  # bms1
    "41:19:06:01:36:59",  # bms2
    "41:19:06:01:71:60"   # bms3
]

NOTIFY_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"

WRITES = [
    "d20300800029965f",
    "d2030000003ed7b9",
]

event_list = []


async def handle_device(addr):
    try:
        async with BleakClient(addr) as client:

            def handle_notification(sender, data):
                try:
                    print(f"[{addr}] {data.hex()}")
                    results = parse_bms_message(data.hex())
                    event = create_splunk_event({**results, "mac": sender})
                    event_list.append(event)

                    for result in results:
                        print(f"\n\t✅ **PARSING RESULT ({addr}) sender: {sender}**")
                        print(json.dumps(result, indent=4))

                except Exception as parse_err:
                    # Catch errors in parsing and send to Splunk
                    error_event = create_splunk_event({
                        "mac": sender,
                        "error": str(parse_err),
                        "stage": "parse_bms_message"
                    })
                    event_list.append(error_event)
                    print(f"[{addr}] ❌ Error parsing data: {parse_err}")

            await client.start_notify(NOTIFY_CHAR_UUID, handle_notification)

            # Send writes sequentially
            for w in WRITES:
                await client.write_gatt_char(WRITE_CHAR_UUID, bytes.fromhex(w))
                await asyncio.sleep(0.1)

            # Wait for notifications
            await asyncio.sleep(10)
            await client.stop_notify(NOTIFY_CHAR_UUID)

    except Exception as conn_err:
        # Catch connection-level errors
        error_event = create_splunk_event({
            "mac": addr,
            "error": str(conn_err),
            "stage": "ble_connection"
        })
        event_list.append(error_event)
        print(f"[{addr}] ❌ BLE connection error: {conn_err}")


async def main():
    global event_list
    event_list = []
    tasks = [asyncio.create_task(handle_device(addr)) for addr in DEVICE_ADDRS]
    await asyncio.gather(*tasks)
    print(event_list)
    post_to_splunk(event_list)


if __name__ == "__main__":
    asyncio.run(main())
