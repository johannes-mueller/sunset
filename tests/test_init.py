"""Test Light Redshift setup process."""
import pytest
import logging

import datetime as DT

import freezegun as FG

from custom_components.redshift import async_setup

from custom_components.redshift.const import DOMAIN
from homeassistant.exceptions import ConfigEntryNotReady

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    ATTR_ENTITY_ID
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP
)

from homeassistant.helpers.entity_component import (
    EntityComponent,
)

import homeassistant.core as HA

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockEntity,
    async_fire_time_changed
)

from .const import MOCK_CONFIG

_LOGGER = logging.getLogger(__name__)


async def test_setup(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    assert hass.states.get('redshift.active').state == 'True'


async def turn_on_lights(hass, lights):
    attrs = {
        ATTR_COLOR_TEMP: 6300
    }
    for lgt in lights:
        hass.states.async_set('light.'+lgt, STATE_ON, attrs)


async def make_lights(hass, lights):
    component = EntityComponent(_LOGGER, 'light', hass)

    await component.async_add_entities([
        MockEntity(entity_id='light.'+lgt) for lgt in lights
    ])

    for lgt in lights:
        hass.states.async_set('light.'+lgt, STATE_OFF)


@pytest.fixture
async def lights(hass):
    await make_lights(hass, ['light_1', 'light_2'])


@pytest.fixture
async def more_lights(hass, lights):
    await make_lights(hass, ['light_3', 'light_4'])


@pytest.fixture
async def turn_on_service(hass):
    calls = []

    @HA.callback
    def mock_service_log(call):
        """Mock service call."""
        entity = call.data[ATTR_ENTITY_ID]
        attrs = {
            ATTR_COLOR_TEMP: call.data.get(ATTR_COLOR_TEMP)
        }

        hass.states.async_set(entity, STATE_ON, attrs)

        calls.append(call)

    hass.services.async_register('light', SERVICE_TURN_ON, mock_service_log)

    return calls


@pytest.fixture
def start_at_noon():
    with FG.freeze_time("2020-12-13 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture
def start_at_night():
    with FG.freeze_time("2020-12-13 03:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture
def some_day_time():
    return DT.datetime.fromisoformat("2020-12-13 14:00:00")


@pytest.fixture
def some_evening_time():
    return DT.datetime.fromisoformat("2020-12-13 20:00:00")


@pytest.fixture
def some_night_time():
    return DT.datetime.fromisoformat("2020-12-14 04:00:00")


async def test_no_call_right_after_setup(hass, turn_on_service, lights, some_day_time):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_service_turn_on_call_two_lights_two_on(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 2


async def test_service_turn_on_call_four_lights_four_on(
        hass,
        more_lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2', 'light_3', 'light_4'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 4


async def test_service_turn_on_call_four_lights_1_3_on(
        hass,
        more_lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_3'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 2

    on_lights = set([call.data[ATTR_ENTITY_ID] for call in turn_on_service])
    assert on_lights == {'light.light_1', 'light.light_3'}


async def test_service_turn_on_call_four_lights_3_manually_set_color_temp(
        hass,
        more_lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_3'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    turn_on_service.pop()
    turn_on_service.pop()

    hass.states.async_set('light.light_3', STATE_ON, attributes={ATTR_COLOR_TEMP: 6200})
    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1'}

    turn_on_service.pop()

    hass.states.async_set('light.light_3', STATE_OFF)
    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1'}

    turn_on_service.pop()

    await turn_on_lights(hass, ['light_3'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 2
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1', 'light.light_3'}


async def test_redshift_day_to_night(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_night_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time)
    async_fire_time_changed(hass, some_night_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 2500


async def test_redshift_night_to_day(
        hass,
        lights,
        turn_on_service,
        start_at_night,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time)
    async_fire_time_changed(hass, some_day_time, fire_all=True)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 6500


async def test_redshift_day_to_night_non_default_night_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_night_time
):
    config = dict(night_color_temp=2700)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time)
    async_fire_time_changed(hass, some_night_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 2700


async def test_redshift_night_to_day_non_default_day_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_night,
        some_day_time
):
    config = dict(day_color_temp=6000)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time)
    async_fire_time_changed(hass, some_day_time, fire_all=True)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 6000


async def test_redshift_to_evening(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_evening_time
):
    config = dict()
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time)
    async_fire_time_changed(hass, some_evening_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 4500


async def test_redshift_to_evening_non_default_evening_range(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_evening_time
):
    config = dict(
        evening_time="18:00",
        night_time="00:00",
        day_color_temp=6500,
        night_color_temp=2600
    )
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time)
    async_fire_time_changed(hass, some_evening_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 5200


@pytest.mark.parametrize('morning_time, expected_color_temps', [
    ("05:00", [2500, 6500, 6500]),
    ("06:00", [2500, 2500, 6500]),
    ("07:00", [2500, 2500, 2500]),
])
async def test_redshift_night_to_day_non_default_morning_time(
        morning_time,
        expected_color_temps,
        hass,
        lights,
        turn_on_service,
        start_at_night
):
    config = dict(morning_time=morning_time)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    for time, expected in zip(["04:30", "05:30", "06:30"], expected_color_temps):
        time = DT.datetime.fromisoformat("2020-12-13 %s:00" % time)

        start_at_night.move_to(time)
        async_fire_time_changed(hass, time, fire_all=True)

        await hass.async_block_till_done()

        assert len(turn_on_service) == 1
        assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == expected
