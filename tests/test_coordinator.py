from datetime import date
from types import MappingProxyType

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.pichler_pkom4_local import DOMAIN, Pkom4Coordinator


class FakeClient:
    def __init__(self, *args):
        self.data = {
            "VENTILATION": 2,
            "OP_MODE": 3,
            "OP_HOLIDAY_YEAR": 30,
            "OP_HOLIDAY_MONTH": 6,
            "OP_HOLIDAY_DAY": 15,
        }
        self.closed = False

    def read(self):
        return self.data.copy()

    def write(self, key, value):
        if key != "VENTILATION" or value != 0:
            self.data[key] = value

    def write_many(self, updates):
        self.data.update(updates)

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_coordinator_validates_readback_and_closes_client(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    entry = ConfigEntry(
        data={"host": "10.42.0.20", "device_id": "000000000001", "email": "test@example.invalid"},
        discovery_keys=MappingProxyType({}),
        domain=DOMAIN,
        minor_version=1,
        options={},
        source="user",
        title="Test device",
        unique_id="000000000001",
        version=1,
        subentries_data=None,
    )
    monkeypatch.setattr("custom_components.pichler_pkom4_local.Pkom4Client", FakeClient)
    coordinator = Pkom4Coordinator(hass, entry)
    try:
        await coordinator.async_refresh()
        await coordinator.async_write("VENTILATION", 3)
        assert coordinator.data["VENTILATION"] == 3
        with pytest.raises(HomeAssistantError, match="could not be confirmed"):
            await coordinator.async_write("VENTILATION", 0)
        assert coordinator.data["VENTILATION"] == 3
        await coordinator.async_set_holiday_date(date(2030, 6, 20))
        assert coordinator.data["OP_HOLIDAY_DAY"] == 20
        coordinator.data["OP_HOLIDAY_YEAR"] = 0
        with pytest.raises(HomeAssistantError, match="holiday end date"):
            await coordinator.async_write("OP_MODE", 4)
    finally:
        await coordinator.async_shutdown()
    assert coordinator.client.closed
