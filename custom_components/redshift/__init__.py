import logging

import datetime as DT

import homeassistant.core as HA
import homeassistant.helpers.event as EV
from homeassistant.helpers import entity_registry

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
    COLOR_MODE_COLOR_TEMP,
)

from .calculator import RedshiftCalculator

DOMAIN = 'redshift'

_LOGGER = logging.getLogger('redshift')


async def async_setup(hass, config):

    def inactive():
        return hass.states.get(DOMAIN+'.active').state != 'True'

    def fetch_light_states():
        return {
            lgt: hass.states.get(lgt) for lgt in hass.states.async_entity_ids('light')
            if hass.states.get(lgt).state == STATE_ON
        }

    def current_target_color_temp():
        return manual_color_temp or round(redshift_calculator.color_temp())

    def color_temp_in_limits(lgt):
        min_color_temp_kelvin = hass.states.get(lgt).attributes[ATTR_MIN_COLOR_TEMP_KELVIN]
        max_color_temp_kelvin = hass.states.get(lgt).attributes[ATTR_MAX_COLOR_TEMP_KELVIN]
        return min(max_color_temp_kelvin, max(min_color_temp_kelvin, current_target_color_temp()))

    async def apply_new_color_temp(lgt):
        color_temp = color_temp_in_limits(lgt)
        current_color_temp_mired = _color_temp_mired_of_state(hass.states.get(lgt))

        if int(1e6/color_temp) == current_color_temp_mired:
            return

        _LOGGER.debug("%s -> %s", lgt, color_temp)

        attrs = {ATTR_ENTITY_ID: lgt, ATTR_COLOR_TEMP_KELVIN: color_temp}
        known_states[lgt] = HA.State(lgt, STATE_ON, attrs)
        await hass.services.async_call('light', SERVICE_TURN_ON, attrs)

    def forget_off_lights(current_states):
        return dict(
            filter(lambda x: x[0] in current_states.keys(), known_states.items())
        )

    def is_not_color_temp_light(lgt):
        return COLOR_MODE_COLOR_TEMP not in hass.states.get(lgt).attributes[ATTR_SUPPORTED_COLOR_MODES]

    async def maybe_apply_new_color_temp(lgt, current_state):
        if lgt in lights_not_to_touch or is_not_color_temp_light(lgt):
            return

        known_state = known_states.get(lgt)
        known_color_temp = _color_temp_mired_of_state(known_state)
        current_color_temp = _color_temp_mired_of_state(current_state)

        light_just_went_on = known_state is None
        nobody_changed_color_temp_since_last_time = known_color_temp == current_color_temp

        _LOGGER.debug("%s: %s %s" % (lgt, known_color_temp, current_color_temp))
        if nobody_changed_color_temp_since_last_time or light_just_went_on:
            await apply_new_color_temp(lgt)

    async def timer_event(event):
        nonlocal known_states

        await hass.async_block_till_done()

        current_states = fetch_light_states()
        known_states = forget_off_lights(current_states)

        if inactive():
            return

        for lgt, current_state in current_states.items():
            await maybe_apply_new_color_temp(lgt, current_state)

    def dont_touch(event):
        for entity_id in entities_ids_from_event(event):
            lights_not_to_touch.add(entity_id)

    def handle_again(event):
        for entity_id in entities_ids_from_event(event):
            if entity_id not in lights_not_to_touch:
                _LOGGER.warning("Unknown entity_id: %s" % entity_id)
                continue
            lights_not_to_touch.remove(entity_id)

    def entities_ids_from_event(event):
        entity_reg = entity_registry.async_get(hass)

        device_id = event.data.get(ATTR_DEVICE_ID)
        if device_id is not None:
            for entry in entity_registry.async_entries_for_device(entity_reg, device_id):
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

    async def deactivate(event):
        nonlocal manual_color_temp
        manual_color_temp = event.data.get('color_temp')

        if manual_color_temp is not None:
            await timer_event(None)

        hass.states.async_set(DOMAIN+'.active', False)

    async def activate(_):
        nonlocal manual_color_temp
        manual_color_temp = None
        hass.states.async_set(DOMAIN+'.active', True)
        await timer_event(None)

    def finalized_config():
        final_config = dict(
            evening_time="17:00",
            night_time="23:00",
            morning_time="06:00",
            day_color_temp=6250,
            night_color_temp=2500
        )
        final_config.update(config[DOMAIN])
        return final_config

    def make_redshift_calculator():
        return RedshiftCalculator(
            final_config['evening_time'],
            final_config['night_time'],
            final_config['morning_time'],
            final_config['day_color_temp'],
            final_config['night_color_temp'],
        )

    final_config = finalized_config()

    redshift_calculator = make_redshift_calculator()

    known_states = {}

    manual_color_temp = None

    lights_not_to_touch = set()

    hass.services.async_register(DOMAIN, 'dont_touch', dont_touch)
    hass.services.async_register(DOMAIN, 'handle_again', handle_again)
    hass.services.async_register(DOMAIN, 'activate', activate)
    hass.services.async_register(DOMAIN, 'deactivate', deactivate)

    hass.states.async_set(DOMAIN+'.active', True)
    EV.async_track_time_interval(hass, timer_event, DT.timedelta(seconds=1))

    return True


def _color_temp_mired_of_state(state):
    if state is None:
        return None
    return int(1e6/state.attributes.get(ATTR_COLOR_TEMP_KELVIN))
