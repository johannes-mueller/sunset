"""Test Light Sunset setup process."""


from .const import DOMAIN

from custom_components.sunset import async_setup


async def test_setup(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    assert hass.states.get('sunset.redshift_active').state == 'True'
    assert hass.states.get('sunset.brightness_active').state == 'True'
