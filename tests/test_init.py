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

MIN_MIRED = 160
MAX_MIRED = 400
MINMAX_MIREDS = {
    'min_mireds': MIN_MIRED,
    'max_mireds': MAX_MIRED
}

_LOGGER = logging.getLogger(__name__)


async def test_setup(hass):
    assert await async_setup(hass, {DOMAIN: {}})

    assert hass.states.get('redshift.active').state == 'True'


async def turn_on_lights(hass, lights):
    attrs = {
        ATTR_COLOR_TEMP: 380,
        'min_mireds': MIN_MIRED,
        'max_mireds': MAX_MIRED
    }
    for lgt in lights:
        hass.states.async_set('light.'+lgt, STATE_ON, attrs)


async def make_lights(hass, lights):
    component = EntityComponent(_LOGGER, 'light', hass)

    await component.async_add_entities([
        MockEntity(entity_id='light.'+lgt) for lgt in lights
    ])

    for lgt in lights:
        hass.states.async_set('light.'+lgt, STATE_OFF, attributes=MINMAX_MIREDS)


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

        color_temp = min(MAX_MIRED, max(MIN_MIRED, round(call.data.get(ATTR_COLOR_TEMP))))

        attrs = {
            ATTR_COLOR_TEMP: color_temp,
            'min_mireds': MIN_MIRED,
            'max_mireds': MAX_MIRED
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


async def test_service_active_inactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    hass.states.async_set('redshift.active', False)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', True)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_light_goes_on_while_inactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    hass.states.async_set('redshift.active', False)

    hass.states.async_set('light.light_1', STATE_OFF, attributes=MINMAX_MIREDS)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    attrs = {ATTR_COLOR_TEMP: 390}
    attrs.update(MINMAX_MIREDS)
    hass.states.async_set('light.light_1', STATE_ON, attrs)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', True)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_override_while_active_then_reactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_day_time
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    hass.states.async_set('light.light_1', STATE_ON, attributes={ATTR_COLOR_TEMP: 390})

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', False)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', True)

    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


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

    hass.states.async_set('light.light_3', STATE_ON, attributes={ATTR_COLOR_TEMP: 390})
    async_fire_time_changed(hass, some_day_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1'}

    turn_on_service.pop()

    hass.states.async_set('light.light_3', STATE_OFF, attributes=MINMAX_MIREDS)
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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 400


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 160


async def test_redshift_day_to_night_non_default_night_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_night_time
):
    config = dict(night_color_temp=2571)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time)
    async_fire_time_changed(hass, some_night_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 389


async def test_redshift_night_to_day_non_default_day_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_night,
        some_day_time
):
    config = dict(day_color_temp=5000)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time)
    async_fire_time_changed(hass, some_day_time, fire_all=True)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 200


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 280


async def test_redshift_to_evening_non_default_evening_range(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_evening_time
):
    config = dict(
        evening_time="18:00",
        night_time="00:00"
    )
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time)
    async_fire_time_changed(hass, some_evening_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 240


@pytest.mark.parametrize('morning_time, expected_color_temps', [
    ("05:00", [400, 160, 160]),
    ("06:00", [400, 400, 160]),
    ("07:00", [400, 400, 400]),
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


async def test_redshift_during_evening_rounding_error(
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
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == 280

    for i in range(10):
        start_at_noon.tick(10.0)
        print(start_at_noon())
        async_fire_time_changed(hass, start_at_noon(), fire_all=True)

        await hass.async_block_till_done()
        assert len(turn_on_service) == 1

        turn_on_service.pop()


async def test_redshift_day_to_night_exceed_mired(
        hass,
        lights,
        turn_on_service,
        start_at_noon,
        some_night_time
):
    config = dict(night_color_temp=2000)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time)
    async_fire_time_changed(hass, some_night_time, fire_all=True)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 400



async def test_redshift_night_to_day_exceed_mired(
        hass,
        lights,
        turn_on_service,
        start_at_night,
        some_day_time
):
    config = dict(day_color_temp=6500)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time)
    async_fire_time_changed(hass, some_day_time, fire_all=True)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 160
