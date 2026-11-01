"""Tests for light state tracking and override handling."""

import homeassistant.core as HA
import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.exceptions import HomeAssistantError

from custom_components.sunset.const import DOMAIN

from .common import (
    async_fire_time_changed_now_time,
    async_setup,
    some_evening_time,
    turn_on_lights,
)
from .const import MINMAX_COLOR_TEMP_KELVIN

LIGHT = "light.light_1"


async def test_light_turned_on_gets_the_target_immediately(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_ENTITY_ID] == LIGHT
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 6250


async def test_external_change_is_not_reverted(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    await turn_on_lights(hass, ["light_1"], color_temp=3000)
    await hass.async_block_till_done()
    assert len(turn_on_service) == 0

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert hass.states.get(LIGHT).attributes[ATTR_COLOR_TEMP_KELVIN] == 3000
    assert len(turn_on_service) == 0


async def test_off_and_on_clears_the_override(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    await turn_on_lights(hass, ["light_1"], color_temp=3000)
    await hass.async_block_till_done()
    turn_on_service.clear()

    hass.states.async_set(LIGHT, STATE_OFF)
    await hass.async_block_till_done()

    await turn_on_lights(hass, ["light_1"], color_temp=3000)
    await hass.async_block_till_done()

    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == 6250


@pytest.mark.internal
async def test_own_command_does_not_trigger_another_cycle(
    hass,
    lights,
    turn_on_service,
    start_at_noon,
):
    """Internal: inject a state change carrying Sunset's own context.

    There is no public way to produce a context-tagged state change from
    a test, and the context filter can only be exercised this way.
    """
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1"])
    await hass.async_block_till_done()
    turn_on_service.clear()

    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data.coordinator

    own_context = HA.Context(id=coordinator._own_context_ids[-1])  # noqa: SLF001
    hass.states.async_set(
        LIGHT,
        STATE_ON,
        {
            ATTR_COLOR_TEMP_KELVIN: 3000,
            ATTR_BRIGHTNESS: 254,
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP],
            **MINMAX_COLOR_TEMP_KELVIN,
        },
        context=own_context,
    )
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_failed_light_update_is_logged_and_retried(
    hass,
    lights,
    caplog,
    start_at_noon,
):
    await turn_on_lights(hass, ["light_1"])

    attempts: list[str] = []

    @HA.callback
    def fail(call: HA.ServiceCall) -> None:
        attempts.append(call.data[ATTR_ENTITY_ID])
        raise HomeAssistantError

    hass.services.async_register("light", "turn_on", fail)

    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    assert attempts == ["light.light_1"]
    warnings = [
        record
        for record in caplog.records
        if record.name == "sunset" and "Could not update light" in record.message
    ]
    assert len(warnings) == 1

    # The light is not tracked after the failure, so the next cycle
    # retries the command.
    await hass.services.async_call("sunset", "activate_redshift", {})
    await hass.async_block_till_done()

    assert attempts == ["light.light_1", "light.light_1"]
    warnings = [
        record
        for record in caplog.records
        if record.name == "sunset" and "Could not update light" in record.message
    ]
    assert len(warnings) == 2


async def test_failing_light_does_not_abort_other_lights(
    hass,
    lights,
    start_at_noon,
):
    handled: list[str] = []

    @HA.callback
    def fail_light_1(call: HA.ServiceCall) -> None:
        entity_id = call.data[ATTR_ENTITY_ID]
        if entity_id == "light.light_1":
            raise HomeAssistantError
        handled.append(entity_id)

    hass.services.async_register("light", "turn_on", fail_light_1)

    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ["light_1", "light_2"])
    await hass.async_block_till_done()

    assert handled == ["light.light_2"]
