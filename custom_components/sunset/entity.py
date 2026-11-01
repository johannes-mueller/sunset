"""Shared entity base for Sunset."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import SunsetDataCoordinator


class SunsetEntity(Entity, ABC):
    """Base entity with Sunset device info and change-only state writes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: SunsetDataCoordinator, key: str) -> None:
        """Initialise the entity for a config entry."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Sunset",
            manufacturer="Sunset",
            model="Colour temperature and brightness controller",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Reflect the current target before the initial state write."""
        await super().async_added_to_hass()
        self._sync_state_attributes()

    @abstractmethod
    def _sync_state_attributes(self) -> None:
        """Copy the controller state into this entity's state attributes."""

    def async_write_state_if_changed(self) -> None:
        """Write this entity's state only when the rendered value changed."""
        self._sync_state_attributes()
        current = self.hass.states.get(self.entity_id) if self.hass else None
        if current is None or current.state != self._stringify_state(available=True):
            self.async_write_ha_state()
