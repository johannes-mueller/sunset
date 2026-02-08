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
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_COLOR_TEMP,
    COLOR_MODE_ONOFF,
)

from homeassistant.helpers.entity_component import (
    EntityComponent,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceRegistry, DeviceInfo
from homeassistant.helpers.entity_registry import EntityRegistry


from .const import (
    MIN_COLOR_TEMP_KELVIN,
    MAX_COLOR_TEMP_KELVIN,
    MINMAX_COLOR_TEMP_KELVIN
)

_LOGGER = logging.getLogger(__name__)


async def turn_on_lights(hass, lights, color_temp=None, brightness=None):
    """Turn on `lights`."""
    brightness = brightness or 254
    color_temp_attrs = {
        ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_COLOR_TEMP, COLOR_MODE_BRIGHTNESS],
        ATTR_MIN_COLOR_TEMP_KELVIN: MIN_COLOR_TEMP_KELVIN,
        ATTR_MAX_COLOR_TEMP_KELVIN: MAX_COLOR_TEMP_KELVIN,
        ATTR_BRIGHTNESS: brightness
    }
    bw_attrs = {
        ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_ONOFF]
    }
    dim_attrs = {
        ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_BRIGHTNESS],
        ATTR_BRIGHTNESS: brightness
    }
    for lgt in lights:
        state = hass.states.get('light.'+lgt)
        color_temp = color_temp or _color_temp_of_state(state) or 2630
        if lgt.startswith('bw'):
            attrs = bw_attrs
        elif lgt.startswith('dim'):
            attrs = dim_attrs
        else:
            attrs = color_temp_attrs
            attrs[ATTR_COLOR_TEMP_KELVIN] = color_temp

        hass.states.async_set('light.'+lgt, STATE_ON, attrs)


async def make_lights(hass, entity_registry: EntityRegistry, device_registry: DeviceRegistry, config_entry,  lights, area_name):
    """Setup light entities `lights`."""

    def _make_light(hass, light):
        device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id, identifiers={("light", "identifier-" + light)}
        )

        entity_entry = entity_registry.async_get_or_create('light', '', light, device_id=device.id)
        entity_id = entity_entry.entity_id
        print(light, entity_id)

        entity_registry.async_update_entity(entity_id, area_id=area_name, device_id=device.id)
        entity = MockEntity(entity_id=entity_id, area_id=area_name)
        print(entity.entity_id)
        return entity

    entities = [_make_light(hass, lgt) for lgt in lights]

    print("entities_0")
    for ent in entities:
        print(ent.entity_id)


    for lgt in lights:
        hass.states.async_set('light.'+lgt, STATE_OFF, attributes=MINMAX_COLOR_TEMP_KELVIN)

    print("entities_1")
    for ent in entities:
        print(ent.entity_id)

    return [entity_registry.async_get(entity.entity_id) for entity in entities]


def _time_forward(time_string):
    target_time = DT.datetime.combine(DT.datetime.today(), DT.time.fromisoformat(time_string))
    if target_time < DT.datetime.now():
        target_time += DT.timedelta(days=1)
    return target_time


def some_day_time():
    return _time_forward("14:00:00")


def some_evening_time():
    return _time_forward("20:00:00")


def some_night_time():
    return _time_forward("04:00:00")


def async_fire_time_changed_now_time(hass):
    async_fire_time_changed(hass, DT.datetime.now(), fire_all=True)


def _color_temp_of_state(state):
    if state is None:
        return None
    return state.attributes.get(ATTR_COLOR_TEMP_KELVIN)
