"""Common functions for test suite."""

import logging

import datetime as DT

from pytest_homeassistant_custom_component.common import (
    MockEntity,
    async_fire_time_changed
)

from homeassistant.const import (
    STATE_ON,
    STATE_OFF
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP
)

from homeassistant.helpers.entity_component import (
    EntityComponent,
)

from .const import (
    MIN_MIRED,
    MAX_MIRED,
    MINMAX_MIREDS
)

_LOGGER = logging.getLogger(__name__)


async def turn_on_lights(hass, lights, color_temp=None):
    """Turn on `lights`."""
    attrs = {
        'min_mireds': MIN_MIRED,
        'max_mireds': MAX_MIRED
    }
    for lgt in lights:
        state = hass.states.get(lgt)
        color_temp = color_temp or _color_temp_of_state(state) or 380
        attrs[ATTR_COLOR_TEMP] = color_temp

        hass.states.async_set('light.'+lgt, STATE_ON, attrs)


async def make_lights(hass, lights):
    """Setup light entities `lights`."""
    component = EntityComponent(_LOGGER, 'light', hass)

    await component.async_add_entities([
        MockEntity(entity_id='light.'+lgt) for lgt in lights
    ])

    for lgt in lights:
        hass.states.async_set('light.'+lgt, STATE_OFF, attributes=MINMAX_MIREDS)


def some_day_time():
    return DT.datetime.fromisoformat("2020-12-13 14:00:00")


def some_evening_time():
    return DT.datetime.fromisoformat("2020-12-13 20:00:00")


def some_night_time():
    return DT.datetime.fromisoformat("2020-12-14 04:00:00")


def async_fire_time_changed_now_time(hass):
    async_fire_time_changed(hass, DT.datetime.now(), fire_all=True)
def _color_temp_of_state(state):
    if state is None:
        return None
    return state.attributes.get(ATTR_COLOR_TEMP)

