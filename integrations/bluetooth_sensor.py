from __future__ import annotations

from typing import Any

try:
    from bleak import BleakClient
except ImportError:  # pragma: no cover
    BleakClient = None

from integrations.sensor_interface import SensorInterface


class BluetoothSensor(SensorInterface):
    """Placeholder interface for BLE-enabled sensors. Actual device discovery must be validated on target hardware."""

    def __init__(self, address: str, characteristic_uuid: str | None = None):
        self.address = address
        self.characteristic_uuid = characteristic_uuid
        self.available = BleakClient is not None

    def read_measurement(self):
        if not self.available:
            raise RuntimeError("Bleak is not installed; Bluetooth support is unavailable in this environment.")
        return {"source": "REAL_SENSOR_DATA", "status": "UNAVAILABLE"}

    def get_metadata(self):
        return {"sensor_name": "Bluetooth Sensor", "sensor_type": "BLE", "status": "ready"}
