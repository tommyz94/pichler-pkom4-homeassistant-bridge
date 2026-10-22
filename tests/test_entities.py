from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.select import SelectEntityDescription

from custom_components.pichler_pkom4_local.number import DESCRIPTIONS, Pkom4Number
from custom_components.pichler_pkom4_local.select import OPTIONS, Pkom4Select
from custom_components.pichler_pkom4_local.sensor import SENSORS, Pkom4Sensor


@pytest.mark.asyncio
async def test_controls_route_through_coordinator_and_read_actual_state():
    coordinator = SimpleNamespace(
        data={"HOTWATER": 48.0, "VENTILATION": 0}, async_write=AsyncMock()
    )
    entry = SimpleNamespace(unique_id="000000000001")
    number = Pkom4Number(coordinator, entry, next(d for d in DESCRIPTIONS if d.key == "HOTWATER"))
    await number.async_set_native_value(50.0)
    coordinator.async_write.assert_awaited_once_with("HOTWATER", 50.0)
    assert number.native_value == 48.0
    select = Pkom4Select(
        coordinator,
        entry,
        SelectEntityDescription(key="VENTILATION", options=list(OPTIONS["VENTILATION"])),
    )
    assert select.current_option == "automatic"
    await select.async_select_option("level_4")
    coordinator.async_write.assert_awaited_with("VENTILATION", 4)


def test_sensors_have_stable_unique_ids_and_read_coordinator_data():
    coordinator = SimpleNamespace(data={"TEMPERATURE_IST": 21.5})
    entry = SimpleNamespace(unique_id="000000000001")
    sensors = [Pkom4Sensor(coordinator, entry, d) for d in SENSORS]
    assert len({s.unique_id for s in sensors}) == 21
    assert (
        next(s for s in sensors if s.entity_description.key == "TEMPERATURE_IST").native_value
        == 21.5
    )


def test_holiday_date_entity_reports_device_calendar():
    from datetime import date

    from homeassistant.components.date import DateEntityDescription

    from custom_components.pichler_pkom4_local.date import Pkom4Date

    coordinator = SimpleNamespace(
        data={"OP_HOLIDAY_YEAR": 30, "OP_HOLIDAY_MONTH": 6, "OP_HOLIDAY_DAY": 15}
    )
    entry = SimpleNamespace(unique_id="000000000001")
    entity = Pkom4Date(coordinator, entry, DateEntityDescription(key="holiday_end"))
    assert entity.native_value == date(2030, 6, 15)
    coordinator.data["OP_HOLIDAY_MONTH"] = 13
    assert entity.native_value is None


@pytest.mark.asyncio
async def test_hot_water_switch_uses_confirmed_state():
    from homeassistant.components.switch import SwitchEntityDescription

    from custom_components.pichler_pkom4_local.switch import Pkom4Switch

    coordinator = SimpleNamespace(data={"HOTWATER_FAST_HEATING": 0}, async_write=AsyncMock())
    entry = SimpleNamespace(unique_id="000000000001")
    entity = Pkom4Switch(coordinator, entry, SwitchEntityDescription(key="HOTWATER_FAST_HEATING"))
    await entity.async_turn_on()
    coordinator.async_write.assert_awaited_once_with("HOTWATER_FAST_HEATING", 1)
    assert entity.is_on is False
