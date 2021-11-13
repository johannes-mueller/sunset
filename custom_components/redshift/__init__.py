import logging

import datetime as DT

import homeassistant.core as HA
import homeassistant.helpers.event as EV

from homeassistant.const import (
    STATE_ON,
    SERVICE_TURN_ON,
    ATTR_ENTITY_ID
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP
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
        min_mired = hass.states.get(lgt).attributes['min_mireds']
        max_mired = hass.states.get(lgt).attributes['max_mireds']
        return min(max_mired, max(min_mired, current_target_color_temp()))

    async def apply_new_color_temp(lgt):
        color_temp = color_temp_in_limits(lgt)
        current_color_temp = _color_temp_of_state(hass.states.get(lgt))

        if color_temp == current_color_temp:
            return

        _LOGGER.debug("%s -> %s", lgt, color_temp)

        attrs = {ATTR_ENTITY_ID: lgt, ATTR_COLOR_TEMP: color_temp}
        known_states[lgt] = HA.State(lgt, STATE_ON, attrs)
        await hass.services.async_call('light', SERVICE_TURN_ON, attrs)

    def forget_off_lights(current_states):
        return dict(
            filter(lambda x: x[0] in current_states.keys(), known_states.items())
        )

    async def maybe_apply_new_color_temp(lgt, current_state):
        if lgt in lights_not_to_touch:
            return

        known_state = known_states.get(lgt)
        known_color_temp = _color_temp_of_state(known_state)
        current_color_temp = _color_temp_of_state(current_state)

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
        lights_not_to_touch.add(event.data.get(ATTR_ENTITY_ID))

    def handle_again(event):
        lights_not_to_touch.remove(event.data.get(ATTR_ENTITY_ID))

    def go_manual(event):
        nonlocal manual_color_temp
        manual_color_temp = event.data.get('color_temp')

        if manual_color_temp is not None:
            manual_color_temp = round(_kelvin_to_mired(manual_color_temp))

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
            _kelvin_to_mired(final_config['day_color_temp']),
            _kelvin_to_mired(final_config['night_color_temp']),
        )

    final_config = finalized_config()

    redshift_calculator = make_redshift_calculator()

    known_states = {}

    manual_color_temp = None

    lights_not_to_touch = set()

    hass.services.async_register(DOMAIN, 'dont_touch', dont_touch)
    hass.services.async_register(DOMAIN, 'handle_again', handle_again)
    hass.services.async_register(DOMAIN, 'manual', go_manual)
    hass.states.async_set(DOMAIN+'.active', True)
    EV.async_track_time_interval(hass, timer_event, DT.timedelta(seconds=1))

    return True


def _kelvin_to_mired(kelvin):
    return 1e6/kelvin


def _color_temp_of_state(state):
    if state is None:
        return None
    return state.attributes.get(ATTR_COLOR_TEMP)
