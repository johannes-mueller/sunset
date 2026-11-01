"""Sunset integration for Home Assistant."""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import homeassistant.core as HA
import homeassistant.helpers.event as EV
import probatio
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    COLOR_MODES_BRIGHTNESS,
    ColorMode,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.typing import ConfigType

from .calculator import DaytimeCalculator, RedshiftCalculator
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
    SERVICE_ACTIVATE_BRIGHTNESS,
    SERVICE_ACTIVATE_REDSHIFT,
    SERVICE_DEACTIVATE_BRIGHTNESS,
    SERVICE_DEACTIVATE_REDSHIFT,
    SERVICE_DONT_TOUCH,
    SERVICE_HANDLE_AGAIN,
    SERVICES,
    normalize_config,
)

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


@dataclass(slots=True)
class SunsetRuntimeData:
    """Runtime data for the Sunset integration."""


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
    return await _async_setup_runtime(hass, entry)


async def _async_setup_runtime(hass: HA.HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Sunset runtime."""
    final_config = normalize_config({**entry.data, **entry.options})

    def redshift_inactive() -> bool:
        state = hass.states.get(DOMAIN + ".redshift_active")
        return state is None or state.state != "True"

    def brightness_inactive() -> bool:
        state = hass.states.get(DOMAIN + ".brightness_active")
        return state is None or state.state != "True"

    def fetch_light_states() -> dict[str, HA.State]:
        states: dict[str, HA.State] = {}
        for lgt in hass.states.async_entity_ids("light"):
            state = hass.states.get(lgt)
            if state is not None and state.state == STATE_ON:
                states[lgt] = state
        return states

    def current_target_color_temp() -> int:
        return manual_color_temp or round(redshift_calculator.color_temp())

    def color_temp_in_limits(state: HA.State) -> int:
        min_color_temp_kelvin = state.attributes[ATTR_MIN_COLOR_TEMP_KELVIN]
        max_color_temp_kelvin = state.attributes[ATTR_MAX_COLOR_TEMP_KELVIN]
        return min(
            max_color_temp_kelvin,
            max(min_color_temp_kelvin, current_target_color_temp()),
        )

    def new_brightness() -> int | None:
        if manual_brightness is not None:
            return manual_brightness
        if brightness_calculator is None:
            return None
        if brightness_calculator.is_night():
            return final_config["night_brightness"]
        return 254

    def forget_off_lights(current_states: dict[str, HA.State]) -> dict[str, HA.State]:
        return {
            lgt: state for lgt, state in known_states.items() if lgt in current_states
        }

    def is_not_color_temp_light(state: HA.State) -> bool:
        supported_modes = state.attributes.get(ATTR_SUPPORTED_COLOR_MODES, [])
        return ColorMode.COLOR_TEMP not in supported_modes

    def is_not_dimmable_light(state: HA.State) -> bool:
        supported_modes = state.attributes.get(ATTR_SUPPORTED_COLOR_MODES, [])
        return COLOR_MODES_BRIGHTNESS.isdisjoint(supported_modes)

    def new_color_temp_state(
        lgt: str,
        known_state: HA.State | None,
        current_state: HA.State,
    ) -> dict[str, Any]:
        known_color_temp = _color_temp_mired_of_state(known_state)
        current_color_temp = _color_temp_mired_of_state(current_state)

        light_was_on_before = known_state is not None
        somebody_changed_color_temp_since_last_time = (
            known_color_temp != current_color_temp
        )

        if is_not_color_temp_light(current_state):
            return {}

        if somebody_changed_color_temp_since_last_time and light_was_on_before:
            return {}

        color_temp = color_temp_in_limits(current_state)
        current_color_temp_mired = _color_temp_mired_of_state(current_state)

        if redshift_inactive() or int(1e6 / color_temp) == current_color_temp_mired:
            return {}

        _LOGGER.debug("color temp of %s -> %s", lgt, color_temp)

        return {ATTR_COLOR_TEMP_KELVIN: color_temp}

    def new_brightness_state(
        lgt: str,
        known_state: HA.State | None,
        current_state: HA.State,
    ) -> dict[str, Any]:
        known_brightness = _brightness_of_state(known_state)
        current_brightness = _brightness_of_state(current_state)

        light_was_on_before = known_state is not None
        somebody_changed_brightness_since_last_time = (
            known_brightness != current_brightness
        )

        if is_not_dimmable_light(current_state):
            return {}

        if somebody_changed_brightness_since_last_time and light_was_on_before:
            return {}

        brightness = current_brightness if brightness_inactive() else new_brightness()

        if (
            brightness_inactive()
            or brightness is None
            or brightness == current_brightness
        ):
            return {}

        _LOGGER.debug("brightness of %s -> %s", lgt, brightness)

        return {ATTR_BRIGHTNESS: brightness}

    async def maybe_apply_new_state(lgt: str, current_state: HA.State) -> None:
        if lgt in lights_not_to_touch:
            return

        known_state = known_states.get(lgt)

        attrs = new_color_temp_state(
            lgt,
            known_state,
            current_state,
        ) | new_brightness_state(lgt, known_state, current_state)

        if attrs:
            current_attrs = current_state.attributes
            call_attrs = {
                key: current_attrs[key]
                for key in [ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN]
                if key in current_attrs
            } | {ATTR_ENTITY_ID: lgt}
            call_attrs.update(attrs)
            known_attributes = (
                known_state.attributes
                if known_state is not None
                else current_state.attributes
            )
            known_states[lgt] = HA.State(lgt, STATE_ON, known_attributes | attrs)
            await hass.services.async_call("light", SERVICE_TURN_ON, call_attrs)

    async def timer_event(_: dt.datetime | None) -> None:
        nonlocal known_states

        hass.states.async_set(
            DOMAIN + ".color_temp_kelvin", str(current_target_color_temp())
        )
        brightness = new_brightness()
        hass.states.async_set(
            DOMAIN + ".brightness",
            STATE_UNKNOWN if brightness is None else str(brightness),
        )

        current_states = fetch_light_states()
        known_states = forget_off_lights(current_states)

        for lgt, current_state in current_states.items():
            await maybe_apply_new_state(lgt, current_state)

    async def dont_touch(event: HA.ServiceCall) -> None:
        for entity_id in entity_ids_from_event(event):
            lights_not_to_touch.add(entity_id)

    async def handle_again(event: HA.ServiceCall) -> None:
        for entity_id in entity_ids_from_event(event):
            if entity_id not in lights_not_to_touch:
                _LOGGER.warning("Unknown entity_id: %s", entity_id)
                continue
            lights_not_to_touch.remove(entity_id)

    def entity_ids_from_event(event: HA.ServiceCall) -> Generator[str]:
        entity_reg = entity_registry.async_get(hass)

        device_id = event.data.get(ATTR_DEVICE_ID)
        if device_id is not None:
            for entity_entry in entity_registry.async_entries_for_device(
                entity_reg,
                device_id,
            ):
                yield entity_entry.entity_id

        area_id = event.data.get(ATTR_AREA_ID)
        if area_id is not None:
            for entity_entry in entity_registry.async_entries_for_area(
                entity_reg,
                area_id,
            ):
                yield entity_entry.entity_id

        entity_ids = event.data.get(ATTR_ENTITY_ID, [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        yield from entity_ids

    async def deactivate_redshift(event: HA.ServiceCall) -> None:
        nonlocal manual_color_temp
        manual_color_temp = event.data.get("color_temp")

        if manual_color_temp is not None:
            await timer_event(None)

        hass.states.async_set(DOMAIN + ".redshift_active", str(False))

    async def activate_redshift(_: HA.ServiceCall) -> None:
        nonlocal manual_color_temp
        manual_color_temp = None
        hass.states.async_set(DOMAIN + ".redshift_active", str(True))
        await timer_event(None)

    async def deactivate_brightness(event: HA.ServiceCall) -> None:
        nonlocal manual_brightness
        manual_brightness = event.data.get("brightness")
        if manual_brightness is not None:
            await timer_event(None)
        hass.states.async_set(DOMAIN + ".brightness_active", str(False))

    async def activate_brightness(_event: HA.ServiceCall) -> None:
        nonlocal manual_brightness
        manual_brightness = None
        hass.states.async_set(DOMAIN + ".brightness_active", str(True))
        await timer_event(None)

    def make_redshift_calculator() -> RedshiftCalculator:
        return RedshiftCalculator(
            final_config[CONF_EVENING_TIME],
            final_config[CONF_NIGHT_TIME],
            final_config[CONF_MORNING_TIME],
            final_config[CONF_DAY_COLOR_TEMP],
            final_config[CONF_NIGHT_COLOR_TEMP],
        )

    def make_brightness_calculator() -> DaytimeCalculator | None:
        if not final_config[CONF_BRIGHTNESS_ENABLED]:
            return None
        return DaytimeCalculator(
            final_config[CONF_BED_TIME],
            final_config[CONF_MORNING_TIME],
        )

    redshift_calculator = make_redshift_calculator()
    brightness_calculator = make_brightness_calculator()

    known_states: dict[str, HA.State] = {}

    manual_color_temp: int | None = None
    manual_brightness: int | None = None

    lights_not_to_touch: set[str] = set(final_config[CONF_EXCLUDED_ENTITIES])

    hass.services.async_register(DOMAIN, SERVICE_DONT_TOUCH, dont_touch)
    hass.services.async_register(DOMAIN, SERVICE_HANDLE_AGAIN, handle_again)
    hass.services.async_register(DOMAIN, SERVICE_ACTIVATE_REDSHIFT, activate_redshift)
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_REDSHIFT,
        deactivate_redshift,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ACTIVATE_BRIGHTNESS, activate_brightness
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DEACTIVATE_BRIGHTNESS,
        deactivate_brightness,
    )

    hass.states.async_set(DOMAIN + ".redshift_active", str(True))
    hass.states.async_set(DOMAIN + ".brightness_active", str(True))

    hass.states.async_set(
        DOMAIN + ".color_temp_kelvin", str(current_target_color_temp())
    )
    initial_brightness = new_brightness()
    hass.states.async_set(
        DOMAIN + ".brightness",
        STATE_UNKNOWN if initial_brightness is None else str(initial_brightness),
    )

    unsub = EV.async_track_time_interval(
        hass, timer_event, dt.timedelta(seconds=1), cancel_on_shutdown=True
    )

    def async_unload_runtime() -> None:
        unsub()
        for service in SERVICES:
            hass.services.async_remove(DOMAIN, service)
        for state in (
            "redshift_active",
            "brightness_active",
            "color_temp_kelvin",
            "brightness",
        ):
            hass.states.async_remove(f"{DOMAIN}.{state}")

    entry.async_on_unload(async_unload_runtime)
    entry.runtime_data = SunsetRuntimeData()
    return True


async def async_unload_entry(_hass: HA.HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a Sunset config entry."""
    return True


def _color_temp_mired_of_state(state: HA.State | None) -> int | None:
    if state is None:
        return None
    color_temp = state.attributes.get(ATTR_COLOR_TEMP_KELVIN)
    if color_temp is None:
        return None
    return int(1e6 / color_temp)


def _brightness_of_state(state: HA.State | None) -> int | None:
    if state is None:
        return None

    return state.attributes.get(ATTR_BRIGHTNESS)
