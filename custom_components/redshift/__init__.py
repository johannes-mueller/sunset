import datetime as DT

import homeassistant.core as HA
import homeassistant.helpers.event as EV

from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    STATE_ON,
    STATE_OFF,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    ATTR_ENTITY_ID
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP
)

from .const import *
from .calculator import RedshiftCalculator


async def async_setup(hass, config):

    def fetch_light_states():
        return {
            lgt: hass.states.get(lgt) for lgt in hass.states.async_entity_ids('light')
            if hass.states.get(lgt).state == STATE_ON
        }

    async def apply_new_color_temp(lgt):
        color_temp = redshift_calculator.color_temp()
        attrs = {ATTR_ENTITY_ID: lgt, ATTR_COLOR_TEMP: color_temp}
        known_states[lgt] = HA.State(lgt, STATE_ON, attrs)
        await hass.services.async_call('light', SERVICE_TURN_ON, attrs)

    async def timer_event(event):
        nonlocal known_states

        await hass.async_block_till_done()

        new_states = fetch_light_states()
        known_states = dict(
            filter(lambda x: x[0] in new_states.keys(), known_states.items())
        )

        for lgt, new_state in new_states.items():
            known_state = known_states.get(lgt)
            known_color_temp = None if known_state is None else known_state.attributes.get(ATTR_COLOR_TEMP)
            new_color_temp = new_state.attributes.get(ATTR_COLOR_TEMP)

            light_just_went_on = known_state is None
            nobody_changed_color_temp_since_last_time = known_color_temp == new_color_temp

            if nobody_changed_color_temp_since_last_time or light_just_went_on:
                await apply_new_color_temp(lgt)

    final_config = dict(
        evening_time="17:00",
        night_time="23:00",
        morning_time="06:00",
        day_color_temp=6500,
        night_color_temp=2500
    )
    final_config.update(config[DOMAIN])

    redshift_calculator = RedshiftCalculator(**final_config)

    known_states = {}

    hass.states.async_set(DOMAIN+'.active', True)

    EV.async_track_time_interval(hass, timer_event, DT.timedelta(seconds=1))

    return True
