"""Common fixtures for test suite."""

import pytest

import freezegun as FG

import homeassistant.core as HA

from homeassistant.const import (
    STATE_ON,
    SERVICE_TURN_ON,
    ATTR_ENTITY_ID,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_COLOR_MODE,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    COLOR_MODE_COLOR_TEMP,
    COLOR_MODE_ONOFF
)


from .common import (
    make_lights,
)
from .const import (
    MIN_COLOR_TEMP_KELVIN,
    MAX_COLOR_TEMP_KELVIN,
)


@pytest.fixture
async def lights(hass):
    """Provide lights 'light.light_1' and 'light.light_2'."""
    await make_lights(hass, ['light_1', 'light_2'], area_name="area_1")


@pytest.fixture
async def more_lights(hass, lights):
    """Provide lights 'light.light_3' and 'light.light_4'."""
    await make_lights(hass, ['light_3', 'light_4'], area_name="area_2")



@pytest.fixture
async def bw_light(hass):
    await make_lights(hass, ['bwlight_1'], area_name="foo_area")


@pytest.fixture
async def turn_on_service(hass):
    """Mock SERVICE_TURN_ON for lights."""
    calls = []

    @HA.callback
    def mock_service_log(call):
        """Mock service call."""
        entity = call.data[ATTR_ENTITY_ID]

        color_temp = min(MAX_COLOR_TEMP_KELVIN, max(MIN_COLOR_TEMP_KELVIN, round(call.data.get(ATTR_COLOR_TEMP_KELVIN))))

        actual_color_temp = int(1e6/int(1e6/color_temp))

        color_tmp_attrs = {
            ATTR_COLOR_MODE: COLOR_MODE_COLOR_TEMP,
            ATTR_COLOR_TEMP_KELVIN: actual_color_temp,
            ATTR_MIN_COLOR_TEMP_KELVIN: MIN_COLOR_TEMP_KELVIN,
            ATTR_MAX_COLOR_TEMP_KELVIN: MAX_COLOR_TEMP_KELVIN
        }

        bw_attrs = {
            ATTR_COLOR_MODE: COLOR_MODE_ONOFF
        }

        attrs = bw_attrs if entity.startswith('light.bw') else color_tmp_attrs
        hass.states.async_set(entity, STATE_ON, attrs)

        calls.append(call)

    hass.services.async_register('light', SERVICE_TURN_ON, mock_service_log)

    return calls


@pytest.fixture
def start_at_noon():
    """Fake noon time."""
    with FG.freeze_time("2020-12-13 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture
def start_at_night():
    """Fake night time (3am)."""
    with FG.freeze_time("2020-12-13 03:00:00") as frozen_time:
        yield frozen_time
