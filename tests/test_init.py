"""Test Light Sunset setup process."""

from homeassistant.setup import async_setup_component

from custom_components.sunset import async_setup

from .const import DOMAIN


async def test_setup(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    assert hass.states.get("sunset.redshift_active").state == "True"
    assert hass.states.get("sunset.brightness_active").state == "True"


async def test_setup_via_home_assistant(hass):
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    assert hass.states.get("sunset.redshift_active").state == "True"
    assert hass.states.get("sunset.brightness_active").state == "True"
