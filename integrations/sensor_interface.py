from __future__ import annotations

from abc import ABC, abstractmethod


class SensorInterface(ABC):
    """Base interface for future physical sensors and simulated sources."""

    @abstractmethod
    def read_measurement(self):
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self):
        raise NotImplementedError
