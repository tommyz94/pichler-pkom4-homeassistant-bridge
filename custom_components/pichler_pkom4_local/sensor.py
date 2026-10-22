"""PKOM4 measurements and read-only settings."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

T = SensorDeviceClass.TEMPERATURE
P = SensorDeviceClass.POWER
E = SensorDeviceClass.ENERGY
M = SensorStateClass.MEASUREMENT


def desc(key, name, unit=None, device_class=None, state_class=None, diagnostic=False):
    return SensorEntityDescription(
        key=key,
        translation_key=key.lower(),
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=state_class,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


SENSORS = (
    desc("TEMPERATURE_IST", "Temperatura ambiente", "°C", T, M),
    desc("T1_ZULUFT", "Temperatura mandata", "°C", T, M),
    desc("T3_AUSSENZULUFT", "Temperatura esterna", "°C", T, M),
    desc("T4_FORTLUFT", "Temperatura espulsione", "°C", T, M),
    desc("T7_ABLUFT", "Temperatura ripresa", "°C", T, M),
    desc("T21_SPEICHER_MITTE", "Boiler centro", "°C", T, M),
    desc("T20_SPEICHER_UNTEN", "Boiler fondo", "°C", T, M),
    desc("LUFTMENGE_ZU", "Portata mandata", "m³/h", SensorDeviceClass.VOLUME_FLOW_RATE, M),
    desc("LUFTMENGE_AB", "Portata ripresa", "m³/h", SensorDeviceClass.VOLUME_FLOW_RATE, M),
    desc("ENERGIEVERBRAUCH", "Energia consumata", "kWh", E, SensorStateClass.TOTAL),
    desc("LEISTUNG_HK_KOMPR", "Potenza compressore clima", "W", P, M),
    desc("LEISTUNG_BW_KOMPR", "Potenza compressore acqua calda", "W", P, M),
    desc("LEISTUNG_PLAT_VENT", "Potenza ventilazione", "W", P, M),
    desc("POWER_TOTAL", "Potenza totale", "W", P, M),
    desc("VENTILATION_IST", "Livello ventilazione attuale"),
    desc("VENTILATION", "Livello ventilazione impostato"),
    desc("TEMPERATURE_SOLL_NORMAL", "Temperatura ambiente impostata", "°C", T),
    desc("HOTWATER", "Temperatura boiler impostata", "°C", T),
    desc("OP_MODE", "Codice modalità", diagnostic=True),
    desc("MALFUNCTION", "Codice anomalia", diagnostic=True),
    desc("STATUS_BITS", "Stato grezzo", diagnostic=True),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        Pkom4Sensor(entry.runtime_data, entry, description) for description in SENSORS
    )


class Pkom4Sensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key.lower()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            manufacturer="Pichler",
            model="PKOM4",
            name="Pichler PKOM4",
        )

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.entity_description.key)
        if self.entity_description.key == "ENERGIEVERBRAUCH" and value is not None and value < 0:
            return None
        return value
