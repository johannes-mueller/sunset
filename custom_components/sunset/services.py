"""Registration of Sunset's services as compatibility shims.

The services stay registered under the ``sunset`` domain so existing
automations keep working; with PRs B they become thin aliases for the
switch entities. The handlers are thin shims over the coordinator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import (
    DOMAIN,
    SERVICE_ACTIVATE_BRIGHTNESS,
    SERVICE_ACTIVATE_REDSHIFT,
    SERVICE_DEACTIVATE_BRIGHTNESS,
    SERVICE_DEACTIVATE_REDSHIFT,
    SERVICE_DONT_TOUCH,
    SERVICE_HANDLE_AGAIN,
)

if TYPE_CHECKING:
    import homeassistant.core as HA

    from .coordinator import SunsetDataCoordinator


def async_register_services(
    hass: HA.HomeAssistant,
    coordinator: SunsetDataCoordinator,
) -> None:
    """Register all Sunset services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_DONT_TOUCH,
        coordinator.handle_dont_touch,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_HANDLE_AGAIN,
        coordinator.handle_handle_again,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_REDSHIFT,
        coordinator.handle_activate_redshift,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_REDSHIFT,
        coordinator.handle_deactivate_redshift,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_BRIGHTNESS,
        coordinator.handle_activate_brightness,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_BRIGHTNESS,
        coordinator.handle_deactivate_brightness,
    )
