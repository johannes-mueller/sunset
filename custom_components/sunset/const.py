"""Constants and configuration helpers for the Sunset integration."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

DOMAIN = "sunset"

CONF_EVENING_TIME = "evening_time"
CONF_NIGHT_TIME = "night_time"
CONF_BED_TIME = "bed_time"
CONF_MORNING_TIME = "morning_time"
CONF_DAY_COLOR_TEMP = "day_color_temp"
CONF_NIGHT_COLOR_TEMP = "night_color_temp"
CONF_NIGHT_BRIGHTNESS = "night_brightness"
CONF_BRIGHTNESS_ENABLED = "brightness_enabled"
CONF_EXCLUDED_ENTITIES = "excluded_entities"

SERVICE_DONT_TOUCH = "dont_touch"
SERVICE_HANDLE_AGAIN = "handle_again"
SERVICE_ACTIVATE_REDSHIFT = "activate_redshift"
SERVICE_DEACTIVATE_REDSHIFT = "deactivate_redshift"
SERVICE_ACTIVATE_BRIGHTNESS = "activate_brightness"
SERVICE_DEACTIVATE_BRIGHTNESS = "deactivate_brightness"

SERVICES = (
    SERVICE_DONT_TOUCH,
    SERVICE_HANDLE_AGAIN,
    SERVICE_ACTIVATE_REDSHIFT,
    SERVICE_DEACTIVATE_REDSHIFT,
    SERVICE_ACTIVATE_BRIGHTNESS,
    SERVICE_DEACTIVATE_BRIGHTNESS,
)

# The day/bed-window brightness target. Core lights may report up to
# 255 (`homeassistant`'s brightness range is 1..255), but some bulbs
# misbehaved when commanded 255 directly. The value maps onto Zigbee's
# ZCL `MoveToLevel`, whose level range only reaches 254, so 254 is the
# maximum safe brightness. Test the affected bulb types before ever
# considering a change here.
MAX_DAY_BRIGHTNESS = 254

TIME_KEYS = (
    CONF_EVENING_TIME,
    CONF_NIGHT_TIME,
    CONF_MORNING_TIME,
)

DEFAULT_OPTIONS: dict[str, Any] = {
    CONF_EVENING_TIME: "17:00",
    CONF_NIGHT_TIME: "23:00",
    CONF_BED_TIME: "00:00",
    CONF_MORNING_TIME: "06:00",
    CONF_DAY_COLOR_TEMP: 6250,
    CONF_NIGHT_COLOR_TEMP: 2500,
    CONF_NIGHT_BRIGHTNESS: 127,
    CONF_BRIGHTNESS_ENABLED: True,
    CONF_EXCLUDED_ENTITIES: [],
}


def _time_string(value: object, default: str) -> str:
    """Return an ISO-formatted time string."""
    if value in (None, ""):
        return default
    if isinstance(value, dt.time):
        return value.isoformat(timespec="minutes")
    return dt.time.fromisoformat(str(value)).isoformat(timespec="minutes")


def normalize_config(data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Merge user configuration with defaults and normalize its values."""
    source = dict(data or {})
    config = dict(DEFAULT_OPTIONS)

    for key in TIME_KEYS:
        config[key] = _time_string(source.get(key), DEFAULT_OPTIONS[key])

    brightness_enabled = source.get(CONF_BRIGHTNESS_ENABLED)
    bed_time = source.get(CONF_BED_TIME, DEFAULT_OPTIONS[CONF_BED_TIME])
    if brightness_enabled is None:
        brightness_enabled = bed_time not in (None, "", "null")
    config[CONF_BRIGHTNESS_ENABLED] = bool(brightness_enabled)
    config[CONF_BED_TIME] = (
        _time_string(bed_time, DEFAULT_OPTIONS[CONF_BED_TIME])
        if config[CONF_BRIGHTNESS_ENABLED]
        else None
    )

    for key in (
        CONF_DAY_COLOR_TEMP,
        CONF_NIGHT_COLOR_TEMP,
        CONF_NIGHT_BRIGHTNESS,
    ):
        config[key] = int(source.get(key, DEFAULT_OPTIONS[key]))

    excluded = source.get(CONF_EXCLUDED_ENTITIES, [])
    if isinstance(excluded, str):
        excluded = [excluded]
    config[CONF_EXCLUDED_ENTITIES] = list(excluded or [])

    return config
