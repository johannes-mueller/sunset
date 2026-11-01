"""Sensor entities exposing Sunset's current targets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from .entity import SunsetEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SunsetDataCoordinator


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sunset sensors."""
    coordinator: SunsetDataCoordinator = entry.runtime_data.coordinator
    entities = [
        SunsetColorTempSensor(coordinator),
        SunsetBrightnessSensor(coordinator),
    ]
    coordinator.track_entities(entities)
    async_add_entities(entities)


class SunsetColorTempSensor(SunsetEntity, SensorEntity):
    """Sensor for the current target colour temperature."""

    _attr_translation_key = "color_temp_kelvin"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.KELVIN
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SunsetDataCoordinator) -> None:
        """Initialise the colour temperature sensor."""
        super().__init__(coordinator, "color_temp_kelvin")

    def _sync_state_attributes(self) -> None:
        self._attr_native_value = self.coordinator.controller.target_color_temp()


class SunsetBrightnessSensor(SunsetEntity, SensorEntity):
    """Sensor for the current target brightness."""

    _attr_translation_key = "brightness"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SunsetDataCoordinator) -> None:
        """Initialise the brightness sensor."""
        super().__init__(coordinator, "brightness")

    def _sync_state_attributes(self) -> None:
        self._attr_native_value = self.coordinator.controller.target_brightness()
