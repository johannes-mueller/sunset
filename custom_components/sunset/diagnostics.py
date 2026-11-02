"""Diagnostics support for Sunset."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Sunset config entry."""
    coordinator = entry.runtime_data.coordinator
    controller = coordinator.controller

    return {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "controller": {
            "redshift_active": controller.redshift_active,
            "brightness_active": controller.brightness_active,
            "manual_color_temp": controller.manual_color_temp,
            "manual_brightness": controller.manual_brightness,
            "target_color_temp": controller.target_color_temp(),
            "target_brightness": controller.target_brightness(),
            "ignored_entities": sorted(controller.ignored),
            "tracked_lights": len(controller.tracked),
        },
        "schedule": {
            "next_event_time": coordinator.next_scheduled_event.isoformat(),
        },
    }
