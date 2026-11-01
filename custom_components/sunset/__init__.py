"""Sunset integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import probatio
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.helpers import config_validation as cv

if TYPE_CHECKING:
    import homeassistant.core as HA
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_BED_TIME,
    CONF_BRIGHTNESS_ENABLED,
    CONF_DAY_COLOR_TEMP,
    CONF_EVENING_TIME,
    CONF_EXCLUDED_ENTITIES,
    CONF_MORNING_TIME,
    CONF_NIGHT_BRIGHTNESS,
    CONF_NIGHT_COLOR_TEMP,
    CONF_NIGHT_TIME,
    DOMAIN,
)
from .coordinator import SunsetDataCoordinator, SunsetRuntimeData

_LOGGER = logging.getLogger("sunset")

CONFIG_SCHEMA = probatio.Schema(
    {
        DOMAIN: probatio.Schema(
            {
                probatio.Optional(CONF_EVENING_TIME): probatio.Any(str, cv.time),
                probatio.Optional(CONF_NIGHT_TIME): probatio.Any(str, cv.time),
                probatio.Optional(CONF_BED_TIME): probatio.Any(
                    str,
                    cv.time,
                    probatio.Equal(None),
                ),
                probatio.Optional(CONF_MORNING_TIME): probatio.Any(str, cv.time),
                probatio.Optional(CONF_DAY_COLOR_TEMP): probatio.All(
                    probatio.Coerce(int),
                    probatio.Range(min=2000, max=6500),
                ),
                probatio.Optional(CONF_NIGHT_COLOR_TEMP): probatio.All(
                    probatio.Coerce(int),
                    probatio.Range(min=2000, max=6500),
                ),
                probatio.Optional(CONF_NIGHT_BRIGHTNESS): probatio.All(
                    probatio.Coerce(int),
                    probatio.Range(min=0, max=255),
                ),
                probatio.Optional(CONF_BRIGHTNESS_ENABLED): bool,
                probatio.Optional(CONF_EXCLUDED_ENTITIES): probatio.Any(
                    str,
                    [str],
                ),
            },
            extra=probatio.ALLOW_EXTRA,
        )
    },
    extra=probatio.ALLOW_EXTRA,
)


async def async_setup(hass: HA.HomeAssistant, config: ConfigType) -> bool:
    """Import YAML configuration into a config entry."""
    if DOMAIN not in config:
        return True

    if hass.config_entries.async_entries(DOMAIN):
        _LOGGER.warning(
            "Sunset is already configured through the UI; ignoring YAML configuration"
        )
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config[DOMAIN] or {},
        ),
        "sunset import yaml configuration",
    )
    return True


async def async_setup_entry(hass: HA.HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Sunset config entry."""
    coordinator = SunsetDataCoordinator(hass, entry)
    coordinator.register()
    entry.runtime_data = SunsetRuntimeData(coordinator=coordinator)
    return True


async def async_unload_entry(_hass: HA.HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a Sunset config entry."""
    return True
