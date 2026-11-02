"""Tests for the validation schemas of Sunset's services."""

import probatio
import pytest
from homeassistant.const import ATTR_ENTITY_ID

from .common import async_setup
from .const import DOMAIN


async def test_deactivate_redshift_rejects_out_of_range_values(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    for color_temp in (1000, 1999, 6501, 9000):
        with pytest.raises(probatio.Invalid):
            await hass.services.async_call(
                "sunset",
                "deactivate_redshift",
                {"color_temp": color_temp},
                blocking=True,
            )


async def test_deactivate_redshift_rejects_non_numeric_values(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    with pytest.raises(probatio.Invalid):
        await hass.services.async_call(
            "sunset",
            "deactivate_redshift",
            {"color_temp": "cold"},
            blocking=True,
        )


async def test_deactivate_brightness_rejects_out_of_range_values(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    for brightness in (-1, 256, 2000):
        with pytest.raises(probatio.Invalid):
            await hass.services.async_call(
                "sunset",
                "deactivate_brightness",
                {"brightness": brightness},
                blocking=True,
            )


async def test_deactivate_brightness_rejects_non_numeric_values(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    with pytest.raises(probatio.Invalid):
        await hass.services.async_call(
            "sunset",
            "deactivate_brightness",
            {"brightness": "bright"},
            blocking=True,
        )


async def test_dont_touch_requires_a_target(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    with pytest.raises(probatio.Invalid):
        await hass.services.async_call("sunset", "dont_touch", {}, blocking=True)


async def test_dont_touch_rejects_malformed_entity_ids(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    with pytest.raises(probatio.Invalid):
        await hass.services.async_call(
            "sunset",
            "dont_touch",
            {ATTR_ENTITY_ID: ["some_stupidity"]},
            blocking=True,
        )


async def test_handle_again_rejects_malformed_entity_ids(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    with pytest.raises(probatio.Invalid):
        await hass.services.async_call(
            "sunset",
            "handle_again",
            {ATTR_ENTITY_ID: "not an entity"},
            blocking=True,
        )


async def test_activate_services_reject_extra_data(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    with pytest.raises(probatio.Invalid):
        await hass.services.async_call(
            "sunset",
            "activate_redshift",
            {"color_temp": 4000},
            blocking=True,
        )


async def test_valid_manual_values_are_accepted(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    await hass.services.async_call(
        "sunset",
        "deactivate_redshift",
        {"color_temp": "4000"},
        blocking=True,
    )
    await hass.services.async_call(
        "sunset",
        "deactivate_brightness",
        {"brightness": 100},
        blocking=True,
    )

    assert hass.states.get("switch.sunset_redshift_active").state == "off"
    assert hass.states.get("switch.sunset_brightness_active").state == "off"
