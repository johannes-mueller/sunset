"""Tests for Sunset's switch and sensor entities."""

import homeassistant.core as HA
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_STATE_CHANGED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.sunset.const import DOMAIN

from .common import (
    async_fire_time_changed_now_time,
    async_setup,
    some_evening_time,
    some_night_time,
    turn_on_lights,
)

REDSHIFT_SWITCH = "switch.sunset_redshift_active"
BRIGHTNESS_SWITCH = "switch.sunset_brightness_active"
COLOR_SENSOR = "sensor.sunset_colour_temperature"
BRIGHTNESS_SENSOR = "sensor.sunset_brightness"
ALL_ENTITIES = (REDSHIFT_SWITCH, BRIGHTNESS_SWITCH, COLOR_SENSOR, BRIGHTNESS_SENSOR)


async def test_entities_are_created(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    assert hass.states.get(REDSHIFT_SWITCH).state == STATE_ON
    assert hass.states.get(BRIGHTNESS_SWITCH).state == STATE_ON
    assert float(hass.states.get(COLOR_SENSOR).state) == 6250
    assert float(hass.states.get(BRIGHTNESS_SENSOR).state) == 254

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    entity_reg = er.async_get(hass)
    device_ids = set()
    for entity_id in ALL_ENTITIES:
        registry_entry = entity_reg.async_get(entity_id)
        assert registry_entry is not None
        assert registry_entry.unique_id.startswith(entry.entry_id)
        assert registry_entry.device_id is not None
        device_ids.add(registry_entry.device_id)
    assert len(device_ids) == 1

    device = dr.async_get(hass).async_get(device_ids.pop(), include_child_devices=False)
    assert device is not None
    assert device.name == "Sunset"
    assert device.manufacturer == "Sunset"


async def test_entities_are_removed_with_the_entry(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    for entity_id in ALL_ENTITIES:
        assert hass.states.get(entity_id) is None


async def test_unload_marks_entities_unavailable(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(REDSHIFT_SWITCH).state == STATE_UNAVAILABLE
    assert hass.states.get(COLOR_SENSOR).state == STATE_UNAVAILABLE


async def test_brightness_sensor_unknown_when_disabled(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {"brightness_enabled": False}})
    await hass.async_block_till_done()

    assert hass.states.get(BRIGHTNESS_SENSOR).state == STATE_UNKNOWN
    assert float(hass.states.get(COLOR_SENSOR).state) == 6250


async def test_redshift_switch_turns_off_and_on(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    # Keep brightness out of the picture.
    await hass.services.async_call(
        "switch",
        "turn_off",
        {ATTR_ENTITY_ID: BRIGHTNESS_SWITCH},
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {ATTR_ENTITY_ID: REDSHIFT_SWITCH},
    )
    await hass.async_block_till_done()

    assert hass.states.get(REDSHIFT_SWITCH).state == STATE_OFF

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: REDSHIFT_SWITCH},
    )
    await hass.async_block_till_done()

    assert hass.states.get(REDSHIFT_SWITCH).state == STATE_ON
    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 4375


async def test_brightness_switch_turns_off_and_on(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {ATTR_ENTITY_ID: BRIGHTNESS_SWITCH},
    )
    await hass.async_block_till_done()
    assert hass.states.get(BRIGHTNESS_SWITCH).state == STATE_OFF

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 254
    assert len(turn_on_service) == 0

    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: BRIGHTNESS_SWITCH},
    )
    await hass.async_block_till_done()

    assert hass.states.get(BRIGHTNESS_SWITCH).state == STATE_ON
    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127


async def test_sensors_are_only_written_when_values_change(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()

    events: list[str] = []

    @HA.callback
    def record(event: HA.Event) -> None:
        if event.data["entity_id"] in (COLOR_SENSOR, BRIGHTNESS_SENSOR):
            events.append(event.data["entity_id"])

    unsub = hass.bus.async_listen(EVENT_STATE_CHANGED, record)

    # Applying an unchanged target must not write the sensors.
    await hass.services.async_call("sunset", "activate_redshift", {})
    await hass.async_block_till_done()
    assert events == []

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert events == [COLOR_SENSOR]
    unsub()
