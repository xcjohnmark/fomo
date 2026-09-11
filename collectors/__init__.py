"""Collectors package containing data provider abstractions and implementations."""

from collectors.base import BaseCollector
from collectors.mock_pump_collector import MockPumpCollector

__all__ = ["BaseCollector", "MockPumpCollector"]
