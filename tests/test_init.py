"""Test Sunset setup, import and unload paths."""

import logging

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunset import async_setup
from custom_components.sunset.const import DEFAULT_OPTIONS, DOMAIN


async def test_setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("switch.sunset_redshift_active").state == "on"
    assert hass.states.get("switch.sunset_brightness_active").state == "on"
    assert entry.runtime_data is not None


async def test_setup_via_home_assistant(hass):
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert hass.states.get("switch.sunset_redshift_active").state == "on"
    assert hass.states.get("switch.sunset_brightness_active").state == "on"


async def test_setup_without_yaml(hass):
    assert await async_setup(hass, {})
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_yaml_ignored_when_entry_exists(hass, caplog):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)

    with caplog.at_level(logging.WARNING):
        assert await async_setup(hass, {DOMAIN: {"night_brightness": 100}})

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert "ignoring YAML configuration" in caplog.text


async def test_unload_removes_services_and_states(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "activate_redshift")
    assert hass.states.get("switch.sunset_redshift_active").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.sunset_brightness").state == STATE_UNAVAILABLE


async def test_reload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("switch.sunset_redshift_active").state == "on"
