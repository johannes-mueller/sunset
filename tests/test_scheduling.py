"""Tests for the event-driven transition schedule."""

import datetime as dt
import zoneinfo

import homeassistant.util.dt as dt_util
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.sunset.const import DOMAIN

from .common import (
    async_fire_time_changed_now_time,
    async_setup,
    some_evening_time,
    some_night_time,
    turn_on_lights,
)

COLOR_SENSOR = "sensor.sunset_colour_temperature"
BRIGHTNESS_SENSOR = "sensor.sunset_brightness"


async def test_evening_transition_uses_interpolated_colour(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 4375
    assert len(turn_on_service) == 0
    assert float(hass.states.get(COLOR_SENSOR).state) == 4375


async def test_interpolation_updates_on_the_checkpoint(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()
    first = turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN]
    turn_on_service.clear()

    start_at_noon.tick(60)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    updated = turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN]
    assert updated == 4365
    assert updated != first


async def test_night_and_morning_transitions(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 2500
    assert call.data[ATTR_BRIGHTNESS] == 127
    assert len(turn_on_service) == 0
    assert float(hass.states.get(COLOR_SENSOR).state) == 2500
    assert float(hass.states.get(BRIGHTNESS_SENSOR).state) == 127

    start_at_noon.move_to(some_evening_time() - dt.timedelta(hours=6))
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert float(hass.states.get(COLOR_SENSOR).state) == 6250
    assert float(hass.states.get(BRIGHTNESS_SENSOR).state) == 254


async def test_restart_mid_evening_applies_immediately(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    await turn_on_lights(hass, ["light_1"])
    start_at_noon.move_to(some_evening_time())

    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 4375


async def test_midnight_wrap_keeps_night_until_morning(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()
    assert float(hass.states.get(COLOR_SENSOR).state) == 2500

    start_at_noon.move_to(some_evening_time() - dt.timedelta(hours=5))
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()
    assert float(hass.states.get(COLOR_SENSOR).state) == 6250


async def test_schedule_is_dst_aware(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    dt_util.set_default_time_zone(zoneinfo.ZoneInfo("Europe/Berlin"))
    # 14:00 in Berlin (CEST), noon UTC is 14:00 local.
    start_at_noon.move_to(dt.datetime(2026, 3, 29, 12, 0, tzinfo=dt.UTC))

    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    # 18:00 Berlin (CEST) is one hour into the evening window.
    evening_utc = dt.datetime(2026, 3, 29, 16, 0, tzinfo=dt.UTC)
    start_at_noon.move_to(evening_utc)
    async_fire_time_changed(hass, evening_utc)
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 5625
