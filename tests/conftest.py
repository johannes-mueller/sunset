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
    ATTR_COLOR_TEMP,
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
async def turn_on_service(hass):
    """Mock SERVICE_TURN_ON for lights."""
    calls = []

    @HA.callback
    def mock_service_log(call):
        """Mock service call."""
        entity = call.data[ATTR_ENTITY_ID]

        color_temp = min(MAX_COLOR_TEMP_KELVIN, max(MIN_COLOR_TEMP_KELVIN, round(call.data.get(ATTR_COLOR_TEMP))))

        attrs = {
            ATTR_COLOR_TEMP: color_temp,
            'min_color_temp_kelvin': MIN_COLOR_TEMP_KELVIN,
            'max_color_temp_kelvin': MAX_COLOR_TEMP_KELVIN
        }
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
