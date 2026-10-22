"""Domestic hot-water boost."""

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from .entity import Pkom4Entity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        Pkom4Switch(
            entry.runtime_data, entry, SwitchEntityDescription(key=key, translation_key=key.lower())
        )
        for key in ["HOTWATER_FAST_HEATING", "HOTWATER_E_HEATING"]
    )


class Pkom4Switch(Pkom4Entity, SwitchEntity):
    @property
    def is_on(self):
        return self.coordinator.data.get(self.entity_description.key) == 1

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_write(self.entity_description.key, 1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_write(self.entity_description.key, 0)
