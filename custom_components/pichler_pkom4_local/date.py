"""Holiday end date shared with the device's holiday mode."""

from datetime import date

from homeassistant.components.date import DateEntity, DateEntityDescription

from .entity import Pkom4Entity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            Pkom4Date(
                entry.runtime_data,
                entry,
                DateEntityDescription(key="holiday_end", translation_key="holiday_end"),
            )
        ]
    )


class Pkom4Date(Pkom4Entity, DateEntity):
    @property
    def native_value(self):
        data = self.coordinator.data
        try:
            return date(
                2000 + int(data["OP_HOLIDAY_YEAR"]),
                int(data["OP_HOLIDAY_MONTH"]),
                int(data["OP_HOLIDAY_DAY"]),
            )
        except (ValueError, KeyError):
            return None

    async def async_set_value(self, value):
        await self.coordinator.async_set_holiday_date(value)
