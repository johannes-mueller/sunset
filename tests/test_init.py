"""Test Light Redshift setup process."""


from .const import DOMAIN

from custom_components.redshift import async_setup


async def test_setup(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    assert hass.states.get('redshift.active').state == 'True'
