import logging

from typing import (
    Any,
    Generator
)

import datetime as DT

import homeassistant.core as HA
import homeassistant.helpers.event as EV
from homeassistant.helpers import entity_registry
from homeassistant.helpers.typing import ConfigType

from homeassistant.const import (
    STATE_ON,
    SERVICE_TURN_ON,
    ATTR_AREA_ID,
    ATTR_ENTITY_ID,
    ATTR_DEVICE_ID,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    COLOR_MODES_BRIGHTNESS,
    COLOR_MODE_COLOR_TEMP,
)

from .calculator import RedshiftCalculator, DaytimeCalculator

DOMAIN = 'sunset'

_LOGGER = logging.getLogger('sunset')


async def async_setup(hass: HA.HomeAssistant, config: ConfigType) -> bool:

    def redshift_inactive() -> bool:
        return hass.states.get(DOMAIN+'.redshift_active').state != 'True'

    def brightness_inactive() -> bool:
        return hass.states.get(DOMAIN+'.brightness_active').state != 'True'

    def fetch_light_states() -> dict[str, HA.State]:
        return {
            lgt: hass.states.get(lgt) for lgt in hass.states.async_entity_ids('light')
            if hass.states.get(lgt).state == STATE_ON
        }

    def current_target_color_temp() -> int:
        return manual_color_temp or round(redshift_calculator.color_temp())

    def color_temp_in_limits(state: HA.State) -> int:
        min_color_temp_kelvin = state.attributes[ATTR_MIN_COLOR_TEMP_KELVIN]
        max_color_temp_kelvin = state.attributes[ATTR_MAX_COLOR_TEMP_KELVIN]
        return min(
            max_color_temp_kelvin,
            max(min_color_temp_kelvin, current_target_color_temp())
        )

    def new_brightness() -> int | None:
        if manual_brightness is not None:
            return manual_brightness
        if brightness_calculator is None:
            return None
        if brightness_calculator.is_night():
            return final_config['night_brightness']
        return 254

    def forget_off_lights(current_states: dict[str, HA.State]) -> dict[str, HA.State]:
        return {
            lgt: state for lgt, state in known_states.items() if lgt in current_states
        }

    def is_not_color_temp_light(lgt: str) -> bool:
        supported_modes = hass.states.get(lgt).attributes[ATTR_SUPPORTED_COLOR_MODES]
        return COLOR_MODE_COLOR_TEMP not in supported_modes

    def is_not_dimmable_light(lgt: str) -> bool:
        supported_modes = hass.states.get(lgt).attributes[ATTR_SUPPORTED_COLOR_MODES]
        return COLOR_MODES_BRIGHTNESS.isdisjoint(supported_modes)

    def new_color_temp_state(
        lgt: str, known_state: HA.State | None, current_state: HA.State
    ) -> dict[str, Any]:
        known_color_temp = _color_temp_mired_of_state(known_state)
        current_color_temp = _color_temp_mired_of_state(current_state)

        light_was_on_before = known_state is not None
        somebody_changed_color_temp_since_last_time = (
            known_color_temp != current_color_temp
        )

        if is_not_color_temp_light(lgt):
            return dict()

        if somebody_changed_color_temp_since_last_time and light_was_on_before:
            return dict()

        state = hass.states.get(lgt)
        color_temp = color_temp_in_limits(state)
        current_color_temp_mired = _color_temp_mired_of_state(state)

        if redshift_inactive() or int(1e6 / color_temp) == current_color_temp_mired:
            return dict()

        _LOGGER.debug("color temp of %s -> %s", lgt, color_temp)

        return {ATTR_COLOR_TEMP_KELVIN: color_temp}

    def new_brightness_state(
        lgt: str, known_state: HA.State | None, current_state: HA.State
    ) -> dict[str, Any]:
        known_brightness = _brightness_of_state(known_state)
        current_brightness = _brightness_of_state(current_state)

        light_was_on_before = known_state is not None
        somebody_changed_brightness_since_last_time = (
            known_brightness != current_brightness
        )

        if is_not_dimmable_light(lgt):
            return dict()

        if somebody_changed_brightness_since_last_time and light_was_on_before:
            return dict()

        brightness = current_brightness if brightness_inactive() else new_brightness()

        if (
            brightness_inactive()
            or brightness is None
            or brightness == current_brightness
        ):
            return dict()

        _LOGGER.debug("brightness of %s -> %s", lgt, brightness)

        return {ATTR_BRIGHTNESS: brightness}

    async def maybe_apply_new_state(lgt: str, current_state: HA.State):
        if lgt in lights_not_to_touch:
            return

        known_state = known_states.get(lgt)

        attrs = new_color_temp_state(
            lgt, known_state, current_state
        ) | new_brightness_state(lgt, known_state, current_state)

        if attrs != dict():
            current_attrs = current_state.attributes
            call_attrs = {
                key: current_attrs[key]
                for key in [ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN]
                if key in current_attrs
            } | {ATTR_ENTITY_ID: lgt}
            call_attrs.update(attrs)
            known_attributes = known_state.attributes if known_state is not None else current_state.attributes
            known_states[lgt] = HA.State(lgt, STATE_ON, known_attributes | attrs)
            await hass.services.async_call("light", SERVICE_TURN_ON, call_attrs)

    async def timer_event(_: DT.datetime | None) -> None:
        nonlocal known_states

        hass.states.async_set(DOMAIN + ".color_temp_kelvin", current_target_color_temp())
        hass.states.async_set(DOMAIN + ".brightness", new_brightness())

        current_states = fetch_light_states()
        known_states = forget_off_lights(current_states)

        for lgt, current_state in current_states.items():
            await maybe_apply_new_state(lgt, current_state)

    def dont_touch(event: HA.Event) -> None:
        for entity_id in entity_ids_from_event(event):
            lights_not_to_touch.add(entity_id)

    def handle_again(event: HA.Event) -> None:
        for entity_id in entity_ids_from_event(event):
            if entity_id not in lights_not_to_touch:
                _LOGGER.warning("Unknown entity_id: %s" % entity_id)
                continue
            lights_not_to_touch.remove(entity_id)

    def entity_ids_from_event(event: HA.Event) -> Generator[str, None, None]:
        entity_reg = entity_registry.async_get(hass)

        device_id = event.data.get(ATTR_DEVICE_ID)
        if device_id is not None:
            for entry in entity_registry.async_entries_for_device(
                entity_reg, device_id
            ):
                yield entry.entity_id

        area_id = event.data.get(ATTR_AREA_ID)
        if area_id is not None:
            for entry in entity_registry.async_entries_for_area(entity_reg, area_id):
                yield entry.entity_id

        entity_ids = event.data.get(ATTR_ENTITY_ID, [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        for entity_id in entity_ids:
            yield entity_id

    async def deactivate_redshift(event: HA.Event) -> None:
        nonlocal manual_color_temp
        manual_color_temp = event.data.get("color_temp")

        if manual_color_temp is not None:
            await timer_event(None)

        hass.states.async_set(DOMAIN + ".redshift_active", False)

    async def activate_redshift(_: HA.Event) -> None:
        nonlocal manual_color_temp
        manual_color_temp = None
        hass.states.async_set(DOMAIN + ".redshift_active", True)
        await timer_event(None)

    async def deactivate_brightness(event: HA.Event) -> None:
        nonlocal manual_brightness
        manual_brightness = event.data.get("brightness")
        if manual_brightness is not None:
            await timer_event(None)
        hass.states.async_set(DOMAIN + ".brightness_active", False)

    async def activate_brightness(event) -> None:
        nonlocal manual_brightness
        manual_brightness = None
        hass.states.async_set(DOMAIN + ".brightness_active", True)
        await timer_event(None)

    def finalized_config() -> dict[str, Any]:
        final_config = dict(
            evening_time="17:00",
            night_time="23:00",
            bed_time="00:00",
            morning_time="06:00",
            day_color_temp=6250,
            night_color_temp=2500,
            night_brightness=127,
        )
        final_config.update(config[DOMAIN])
        return final_config

    def make_redshift_calculator() -> RedshiftCalculator:
        return RedshiftCalculator(
            final_config["evening_time"],
            final_config["night_time"],
            final_config["morning_time"],
            final_config["day_color_temp"],
            final_config["night_color_temp"],
        )

    def make_brightness_calculator() -> DaytimeCalculator | None:
        if final_config["bed_time"] == "null":
            return None
        return DaytimeCalculator(final_config["bed_time"], final_config["morning_time"])

    final_config = finalized_config()

    redshift_calculator = make_redshift_calculator()
    brightness_calculator = make_brightness_calculator()

    known_states: dict[str, HA.State] = {}

    manual_color_temp: int | None = None
    manual_brightness: int | None = None

    lights_not_to_touch: set[str] = set()

    hass.services.async_register(DOMAIN, "dont_touch", dont_touch)
    hass.services.async_register(DOMAIN, "handle_again", handle_again)
    hass.services.async_register(DOMAIN, "activate_redshift", activate_redshift)
    hass.services.async_register(DOMAIN, "deactivate_redshift", deactivate_redshift)
    hass.services.async_register(DOMAIN, "activate_brightness", activate_brightness)
    hass.services.async_register(DOMAIN, "deactivate_brightness", deactivate_brightness)

    hass.states.async_set(DOMAIN + ".redshift_active", True)
    hass.states.async_set(DOMAIN + ".brightness_active", True)

    hass.states.async_set(DOMAIN + ".color_temp_kelvin", current_target_color_temp())
    hass.states.async_set(DOMAIN + ".brightness", new_brightness())

    EV.async_track_time_interval(hass, timer_event, DT.timedelta(seconds=1))

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
