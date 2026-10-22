"""Local Pichler PKOM4 integration."""

import asyncio
import logging
from datetime import date, timedelta

from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import Pkom4Client, Pkom4Error

DOMAIN = "pichler_pkom4_local"
PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH, Platform.DATE]
_LOGGER = logging.getLogger(__name__)


class Pkom4Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name="Pichler PKOM4",
            config_entry=entry,
            update_interval=timedelta(seconds=30),
        )
        self.write_lock = asyncio.Lock()
        self.client = Pkom4Client(entry.data["host"], entry.data["device_id"], entry.data["email"])

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.read)
        except Pkom4Error as err:
            raise UpdateFailed("PKOM4 local reading unavailable") from err

    async def async_write(self, key, value):
        if key == "OP_MODE" and value == 4:
            try:
                holiday = date(
                    2000 + int(self.data["OP_HOLIDAY_YEAR"]),
                    int(self.data["OP_HOLIDAY_MONTH"]),
                    int(self.data["OP_HOLIDAY_DAY"]),
                )
            except (ValueError, KeyError) as err:
                raise HomeAssistantError("Set a valid holiday end date first.") from err
            if holiday < dt_util.now().date():
                raise HomeAssistantError("Set a current or future holiday end date first.")
        async with self.write_lock:
            try:
                await self.hass.async_add_executor_job(self.client.write, key, value)
            except (Pkom4Error, ValueError) as err:
                raise HomeAssistantError(
                    "PKOM4 command was not confirmed. Check the device before retrying."
                ) from err
            await self.async_refresh()
            if not self.last_update_success or self.data.get(key) != value:
                raise HomeAssistantError(
                    "The command was accepted but the requested state could not be confirmed by the device."
                )

    async def async_set_holiday_date(self, value):
        if value < dt_util.now().date():
            raise HomeAssistantError("Holiday end date cannot be in the past.")
        updates = {
            "OP_HOLIDAY_YEAR": value.year - 2000,
            "OP_HOLIDAY_MONTH": value.month,
            "OP_HOLIDAY_DAY": value.day,
        }
        async with self.write_lock:
            try:
                await self.hass.async_add_executor_job(self.client.write_many, updates)
            except (Pkom4Error, ValueError) as err:
                raise HomeAssistantError("Holiday date was not confirmed.") from err
            await self.async_refresh()
            if not self.last_update_success or any(
                self.data.get(k) != v for k, v in updates.items()
            ):
                raise HomeAssistantError(
                    "The requested holiday date could not be confirmed by the device."
                )

    async def async_shutdown(self):
        await super().async_shutdown()
        await self.hass.async_add_executor_job(self.client.close)


async def async_setup_entry(hass, entry):
    coordinator = Pkom4Coordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await coordinator.async_shutdown()
        raise
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded
