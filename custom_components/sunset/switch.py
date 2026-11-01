"""Switch entities exposing Sunset's activation flags."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity

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
    """Set up the Sunset switches."""
    coordinator: SunsetDataCoordinator = entry.runtime_data.coordinator
    entities = [
        SunsetRedshiftActiveSwitch(coordinator),
        SunsetBrightnessActiveSwitch(coordinator),
    ]
    coordinator.track_entities(entities)
    async_add_entities(entities)


class SunsetRedshiftActiveSwitch(SunsetEntity, SwitchEntity):
    """Switch for automatic colour temperature control."""

    _attr_translation_key = "redshift_active"

    def __init__(self, coordinator: SunsetDataCoordinator) -> None:
        """Initialise the redshift switch."""
        super().__init__(coordinator, "redshift_active")

    def _sync_state_attributes(self) -> None:
        self._attr_is_on = self.coordinator.controller.redshift_active

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Reactivate automatic redshifting."""
        await self.coordinator.async_activate_redshift()

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Deactivate automatic redshifting."""
        await self.coordinator.async_deactivate_redshift()


class SunsetBrightnessActiveSwitch(SunsetEntity, SwitchEntity):
    """Switch for automatic brightness control."""

    _attr_translation_key = "brightness_active"

    def __init__(self, coordinator: SunsetDataCoordinator) -> None:
        """Initialise the brightness switch."""
        super().__init__(coordinator, "brightness_active")

    def _sync_state_attributes(self) -> None:
        self._attr_is_on = self.coordinator.controller.brightness_active

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Reactivate automatic brightness control."""
        await self.coordinator.async_activate_brightness()

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Deactivate automatic brightness control."""
        await self.coordinator.async_deactivate_brightness()
