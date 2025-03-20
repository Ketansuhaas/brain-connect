import asyncio
from bleak import BleakClient, BleakScanner

# Multiple possible service UUIDs for BrainLink devices
POSSIBLE_SERVICE_UUIDS = [
    "0000fee9-0000-1000-8000-00805f9b34fb",
    "0000180f-0000-1000-8000-00805f9b34fb",
    "0000180a-0000-1000-8000-00805f9b34fb",
    "0000ffe0-0000-1000-8000-00805f9b34fb",
    "6e400001-b5a3-f393-e0a9-e50e24dcca9e",
    "00001800-0000-1000-8000-00805f9b34fb",
    "00001801-0000-1000-8000-00805f9b34fb",
]

# Possible characteristic UUIDs
POSSIBLE_CHARACTERISTIC_UUIDS = [
    "0000fee1-0000-1000-8000-00805f9b34fb",
    "00002a19-0000-1000-8000-00805f9b34fb",
    "00002a29-0000-1000-8000-00805f9b34fb",
    "6e400003-b5a3-f393-e0a9-e50e24dcca9e",
    "00002a00-0000-1000-8000-00805f9b34fb",
    "00002a01-0000-1000-8000-00805f9b34fb",
]

# Global variables
connected_client = None


async def find_device():
    """Scans for available Bluetooth devices and returns the first BrainLink device found."""
    print("Scanning for BrainLink devices...")
    devices = await BleakScanner.discover()
    for device in devices:
        if any(prefix in (device.name or "").lower() for prefix in ["brainlink", "brain", "eeg", "neuro"]):
            print(f"Found BrainLink device: {device.name} ({device.address})")
            return device
    return None


async def connect_to_device():
    """Connects to a BrainLink Pro device and sets up notifications."""
    global connected_client

    device = await find_device()
    if not device:
        print("No BrainLink device found.")
        return False

    client = BleakClient(device.address)
    try:
        print(f"Connecting to {device.name}...")
        await client.connect()
        print("Connected successfully.")

        # Corrected service discovery logic
        services = await client.get_services()  # Await the get_services() coroutine
        service = None
        for service_uuid in POSSIBLE_SERVICE_UUIDS:
            try:
                service = services.get_service(service_uuid)  # Access the service from the result
                if service:
                    print(f"Connected to service: {service_uuid}")
                    break
            except Exception:
                continue

        if not service:
            print("No known services found.")
            return False

        # Find a valid characteristic
        characteristic = None
        for char_uuid in POSSIBLE_CHARACTERISTIC_UUIDS:
            try:
                characteristic = service.get_characteristic(char_uuid)
                if characteristic:
                    print(f"Connected to characteristic: {char_uuid}")
                    break
            except Exception:
                continue

        if not characteristic:
            print("No valid characteristic found.")
            return False

        # Subscribe to notifications
        await client.start_notify(characteristic.uuid, handle_data_changed)
        connected_client = client
        return True

    except Exception as e:
        print(f"Connection error: {e}")
        return False


async def disconnect_from_device():
    """Disconnects from the BrainLink device."""
    global connected_client
    if connected_client:
        print("Disconnecting from BrainLink device...")
        await connected_client.disconnect()
        connected_client = None
        print("Disconnected successfully.")


def handle_data_changed(sender, data):
    """Handles incoming data from the BrainLink device."""
    parsed_data = parse_brainlink_data(data)
    print(f"Received Data: {parsed_data}")


def parse_brainlink_data(data):
    """Parses BrainLink Pro EEG data."""
    if len(data) < 10:
        return {"error": "Incomplete data"}

    result = {}

    # Attention (Byte 8)
    result["attention"] = min(max(data[8], 0), 100)

    # Meditation (Byte 9)
    result["meditation"] = min(max(data[9], 0), 100)

    # Brainwave bands
    result["delta"] = min((data[10] / 255) * 100, 100)
    result["theta"] = min((data[11] / 255) * 100, 100)
    result["alpha"] = min((data[12] / 255) * 100, 100)
    result["beta"] = min((data[13] / 255) * 100, 100)
    result["gamma"] = min((data[14] / 255) * 100, 100)

    result["signal_quality"] = calculate_signal_quality(data)
    result["timestamp"] = asyncio.get_event_loop().time()

    return result


def calculate_signal_quality(data):
    """Calculates the signal quality based on raw data."""
    if len(data) < 2:
        return 30  # Default to low quality

    has_valid_sync = data[0] == 0xAA
    has_non_zero_data = any(byte > 0 for byte in data[2:])
    has_variation = len(set(data[2:])) > 2

    if has_valid_sync and has_non_zero_data and has_variation:
        return 95  # Excellent signal
    elif has_valid_sync and has_non_zero_data:
        return 80  # Good signal
    elif has_valid_sync:
        return 60  # Medium signal
    elif has_non_zero_data:
        return 40  # Poor signal
    else:
        return 20  # Very poor signal


async def main():
    """Main function to connect and receive data."""
    success = await connect_to_device()
    if not success:
        print("Could not connect to BrainLink device.")
        return

    # Run until manually stopped
    try:
        while True:
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        print("Disconnecting...")
        await disconnect_from_device()


if __name__ == "__main__":
    asyncio.run(main())
