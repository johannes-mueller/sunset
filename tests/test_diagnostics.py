"""Tests for the diagnostics support."""

import json

from homeassistant.const import ATTR_ENTITY_ID

from custom_components.sunset.const import DOMAIN
from custom_components.sunset.diagnostics import async_get_config_entry_diagnostics

from .common import async_setup, turn_on_lights


async def test_diagnostics_snapshot(hass, lights, turn_on_service, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"]
    assert diagnostics["controller"]["redshift_active"] is True
    assert diagnostics["controller"]["brightness_active"] is True
    assert diagnostics["controller"]["manual_color_temp"] is None
    assert diagnostics["controller"]["manual_brightness"] is None
    assert diagnostics["controller"]["target_color_temp"] == 6250
    assert diagnostics["controller"]["target_brightness"] == 254
    assert diagnostics["controller"]["tracked_lights"] == 1
    assert diagnostics["controller"]["ignored_entities"] == []
    assert diagnostics["schedule"]["next_event_time"]
    json.dumps(diagnostics)


async def test_diagnostics_contain_temporary_exclusions(
    hass,
    lights,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})

    await hass.services.async_call(
        "sunset",
        "dont_touch",
        {ATTR_ENTITY_ID: ["light.light_1"]},
    )
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["controller"]["ignored_entities"] == ["light.light_1"]


async def test_diagnostics_with_brightness_disabled(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {"brightness_enabled": False}})

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["controller"]["target_brightness"] is None
    json.dumps(diagnostics)
