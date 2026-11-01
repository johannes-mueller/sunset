"""Tests for service target normalization."""

from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN
from homeassistant.const import ATTR_ENTITY_ID

from custom_components.sunset.const import DOMAIN

from .common import (
    async_fire_time_changed_now_time,
    async_setup,
    some_evening_time,
    some_night_time,
    turn_on_lights,
)


async def test_dont_touch_accepts_a_single_entity_id_string(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1", "light_2"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    await hass.services.async_call(
        "sunset",
        "dont_touch",
        {ATTR_ENTITY_ID: "light.light_1"},
    )
    await hass.async_block_till_done()

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert [call.data[ATTR_ENTITY_ID] for call in turn_on_service] == ["light.light_2"]


async def test_dont_touch_accepts_a_list_of_entity_ids(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1", "light_2"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    await hass.services.async_call(
        "sunset",
        "dont_touch",
        {ATTR_ENTITY_ID: ["light.light_1", "light.light_2"]},
    )
    await hass.async_block_till_done()

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call(
        "sunset",
        "handle_again",
        {ATTR_ENTITY_ID: ["light.light_1", "light.light_2"]},
    )
    await hass.async_block_till_done()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert {call.data[ATTR_ENTITY_ID] for call in turn_on_service} == {
        "light.light_1",
        "light.light_2",
    }
    assert all(call.data[ATTR_COLOR_TEMP_KELVIN] == 2500 for call in turn_on_service)
