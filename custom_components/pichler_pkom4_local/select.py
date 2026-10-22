"""PKOM4 operation modes and fan levels. Zero ventilation means automatic."""

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .entity import Pkom4Entity

OPTIONS = {
    "OP_MODE": {"off": 0, "summer": 1, "winter": 2, "automatic": 3, "holiday": 4},
    "VENTILATION": {"automatic": 0, "level_1": 1, "level_2": 2, "level_3": 3, "level_4": 4},
    "TEMPERATURE_IS_ACTIVE_COOLING": {"no": 0, "yes": 1, "eco": 2},
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        Pkom4Select(
            entry.runtime_data,
            entry,
            SelectEntityDescription(key=key, translation_key=key.lower(), options=list(values)),
        )
        for key, values in OPTIONS.items()
    )


class Pkom4Select(Pkom4Entity, SelectEntity):
    @property
    def current_option(self):
        current = self.coordinator.data.get(self.entity_description.key)
        return next(
            (
                name
                for name, value in OPTIONS[self.entity_description.key].items()
                if value == current
            ),
            None,
        )

    async def async_select_option(self, option):
        await self.coordinator.async_write(
            self.entity_description.key, OPTIONS[self.entity_description.key][option]
        )
