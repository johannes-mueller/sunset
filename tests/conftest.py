"""Common fixtures for test suite."""

from typing import TYPE_CHECKING

import freezegun as FG
import homeassistant.core as HA
import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    COLOR_MODE_COLOR_TEMP,
    COLOR_MODE_ONOFF,
    COLOR_MODE_XY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.helpers.entity_registry import EntityRegistry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .common import (
    make_lights,
)
from .const import (
    MAX_COLOR_TEMP_KELVIN,
    MIN_COLOR_TEMP_KELVIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.device_registry import DeviceRegistry
    from homeassistant.helpers.entity_registry import EntityRegistry


@pytest.fixture
async def config_entry(hass: HA.HomeAssistant, device_registry: DeviceRegistry) -> ConfigEntry:
    config_entry = MockConfigEntry(domain="light")
    config_entry.add_to_hass(hass)

    return config_entry


@pytest.fixture
async def lights(hass: HA.HomeAssistant, entity_registry: EntityRegistry, device_registry: DeviceRegistry, config_entry: ConfigEntry):
    """Provide lights "light.light_1" and "light.light_2"."""
    return await make_lights(
        hass,
        entity_registry,
        device_registry,
        config_entry,
        ["light_1", "light_2"],
        area_name="area_1",
    )


@pytest.fixture
async def more_lights(hass, entity_registry, device_registry, config_entry, lights):
    """Provide lights "light.light_3" and "light.light_4"."""
    await make_lights(
        hass,
        entity_registry,
        device_registry,
        config_entry,
        ["light_3", "light_4"],
        area_name="area_2",
    )


@pytest.fixture
async def bw_light(hass, entity_registry, device_registry, config_entry):
    await make_lights(
        hass,
        entity_registry,
        device_registry,
        config_entry,
        ["bwlight_1"],
        area_name="foo_area",
    )


@pytest.fixture
async def dim_light(hass, entity_registry, device_registry, config_entry):
    await make_lights(
        hass,
        entity_registry,
        device_registry,
        config_entry,
        ["dimlight_1"],
        area_name="foo_area",
    )



@pytest.fixture
def turn_on_service(hass):
    """Mock SERVICE_TURN_ON for lights."""
    light_states = {}
    calls = []

    @HA.callback
    def mock_service_log(call):
        """Mock service call."""
        entity = call.data[ATTR_ENTITY_ID]

        last_state = light_states.get(entity)
        color_temp = call.data.get(ATTR_COLOR_TEMP_KELVIN)
        if color_temp is None:
            if last_state is None or last_state.get(ATTR_COLOR_TEMP_KELVIN) is None:
                color_temp = MAX_COLOR_TEMP_KELVIN
            else:
                color_temp = last_state.get(ATTR_COLOR_TEMP_KELVIN)
        color_temp = min(MAX_COLOR_TEMP_KELVIN, max(MIN_COLOR_TEMP_KELVIN, round(color_temp)))
        actual_color_temp = int(1e6/int(1e6/color_temp))

        brightness = call.data.get(ATTR_BRIGHTNESS)
        assert brightness is not None
        if brightness is None:
            if last_state is None or last_state.get(ATTR_BRIGHTNESS) is None:
                brightness = 254
            else:
                brightness = last_state.get(ATTR_BRIGHTNESS)

        color_tmp_attrs = {
            ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_COLOR_TEMP, COLOR_MODE_XY],
            ATTR_COLOR_TEMP_KELVIN: actual_color_temp,
            ATTR_MIN_COLOR_TEMP_KELVIN: MIN_COLOR_TEMP_KELVIN,
            ATTR_MAX_COLOR_TEMP_KELVIN: MAX_COLOR_TEMP_KELVIN,
            ATTR_BRIGHTNESS: brightness,
        }

        bw_attrs = {
            ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_ONOFF],
            ATTR_BRIGHTNESS: brightness,
        }

        attrs = bw_attrs if entity.startswith("light.bw") else color_tmp_attrs

        light_states[entity] = attrs
        calls.append(call)

        attrs[ATTR_BRIGHTNESS] = min(brightness, 254)
        hass.states.async_set(entity, STATE_ON, attrs)

    hass.services.async_register("light", SERVICE_TURN_ON, mock_service_log)

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
