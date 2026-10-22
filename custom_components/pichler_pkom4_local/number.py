"""Temperature setpoints, written only on an explicit user action."""

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import UnitOfTemperature

from .entity import Pkom4Entity

DESCRIPTIONS = tuple(
    NumberEntityDescription(
        key=key,
        translation_key=key.lower(),
        native_min_value=low,
        native_max_value=high,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
    )
    for key, low, high in [
        ("TEMPERATURE_SOLL_NORMAL", 10, 30),
        ("HOTWATER", 20, 75),
        ("TEMPERATURE_SOLL_ACTIVE_COOLING", 15, 40),
    ]
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(Pkom4Number(entry.runtime_data, entry, d) for d in DESCRIPTIONS)


class Pkom4Number(Pkom4Entity, NumberEntity):
    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value):
        await self.coordinator.async_write(self.entity_description.key, value)
