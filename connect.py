import asyncio
from bleak import BleakClient, BleakScanner

# Possible BrainLink service UUIDs
POSSIBLE_SERVICE_UUIDS = [
    '0000fee9-0000-1000-8000-00805f9b34fb',
    '0000180f-0000-1000-8000-00805f9b34fb',
    '0000180a-0000-1000-8000-00805f9b34fb',
    '0000ffe0-0000-1000-8000-00805f9b34fb',
    '6e400001-b5a3-f393-e0a9-e50e24dcca9e',
    '00001800-0000-1000-8000-00805f9b34fb',
    '00001801-0000-1000-8000-00805f9b34fb'
]

# Characteristic UUIDs for BrainLink
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"  # Example UUID for data stream

def parse_brainlink_data(data):
    """
    Parses the raw BrainLink EEG data packet.
    Expected format: [0x02, <ATTENTION>, <MEDITATION>, ...]
    """
    if len(data) < 3:
        return None  # Invalid data packet
    
    attention = data[1]
    meditation = data[2]
    return {
        "Attention": attention,
        "Meditation": meditation
    }

async def scan_for_brainlink():
    """
    Scans for BLE devices and returns the BrainLink device if found.
    """
    print("Scanning for Bluetooth devices...")
    devices = await BleakScanner.discover()

    if not devices:
        print("No devices found.")
        return None

    print("\nDiscovered Devices:")
    for device in devices:
        print(f"{device.name} ({device.address})")

    for device in devices:
        if device.name and "Brain" in device.name:
            print(f"\nBrainLink Device Found: {device.name} ({device.address})")
            return device

    print("\nNo BrainLink device found.")
    return None

async def handle_notifications(sender, data):
    """
    Callback function that receives and processes data from the BrainLink device.
    """
    parsed_data = parse_brainlink_data(data)
    if parsed_data:
        print(f"Attention: {parsed_data['Attention']} | Meditation: {parsed_data['Meditation']}")

async def connect_to_brainlink():
    """
    Connects to the BrainLink device, subscribes to data, and continuously displays EEG readings.
    """
    brainlink_device = await scan_for_brainlink()
    if not brainlink_device:
        return

    async with BleakClient(brainlink_device.address) as client:
        print("\nConnected to BrainLink successfully.")

        # Fetch services
        services = await client.get_services()
        found_service = None
        for service in services:
            if service.uuid in POSSIBLE_SERVICE_UUIDS:
                found_service = service
                break

        if not found_service:
            print("No known services found.")
            return

        print(f"Using service: {found_service.uuid}")

        # Enable notifications for BrainLink data stream
        await client.start_notify(CHARACTERISTIC_UUID, handle_notifications)

        print("\nReceiving BrainLink data... Press Ctrl+C to stop.\n")
        try:
            while True:
                await asyncio.sleep(1)  # Keep the loop running to receive data
        except KeyboardInterrupt:
            print("\nStopping...")
            await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    asyncio.run(connect_to_brainlink())
