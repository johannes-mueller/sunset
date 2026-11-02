"""Registration of Sunset's services as compatibility shims.

The services stay registered under the ``sunset`` domain so existing
automations keep working; they are thin aliases for the switch
entities. The handlers are thin shims over the coordinator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import probatio
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_ACTIVATE_BRIGHTNESS,
    SERVICE_ACTIVATE_REDSHIFT,
    SERVICE_DEACTIVATE_BRIGHTNESS,
    SERVICE_DEACTIVATE_REDSHIFT,
    SERVICE_DONT_TOUCH,
    SERVICE_FIELD_BRIGHTNESS,
    SERVICE_FIELD_COLOR_TEMP,
    SERVICE_HANDLE_AGAIN,
)

if TYPE_CHECKING:
    import homeassistant.core as HA

    from .coordinator import SunsetDataCoordinator

NO_DATA_SCHEMA = probatio.Schema({}, extra=probatio.PREVENT_EXTRA)

DEACTIVATE_REDSHIFT_SCHEMA = probatio.Schema(
    {
        probatio.Optional(SERVICE_FIELD_COLOR_TEMP): probatio.All(
            probatio.Coerce(int),
            probatio.Range(min=2000, max=6500),
        ),
    },
    extra=probatio.PREVENT_EXTRA,
)

DEACTIVATE_BRIGHTNESS_SCHEMA = probatio.Schema(
    {
        probatio.Optional(SERVICE_FIELD_BRIGHTNESS): probatio.All(
            probatio.Coerce(int),
            probatio.Range(min=0, max=255),
        ),
    },
    extra=probatio.PREVENT_EXTRA,
)

TARGET_SCHEMA = cv.make_entity_service_schema(None)


def async_register_services(
    hass: HA.HomeAssistant,
    coordinator: SunsetDataCoordinator,
) -> None:
    """Register all Sunset services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_DONT_TOUCH,
        coordinator.handle_dont_touch,
        schema=TARGET_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_HANDLE_AGAIN,
        coordinator.handle_handle_again,
        schema=TARGET_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_REDSHIFT,
        coordinator.handle_activate_redshift,
        schema=NO_DATA_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_REDSHIFT,
        coordinator.handle_deactivate_redshift,
        schema=DEACTIVATE_REDSHIFT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_BRIGHTNESS,
        coordinator.handle_activate_brightness,
        schema=NO_DATA_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_BRIGHTNESS,
        coordinator.handle_deactivate_brightness,
        schema=DEACTIVATE_BRIGHTNESS_SCHEMA,
    )
