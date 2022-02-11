import pytest

import datetime as DT

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_DEVICE_ID,
    STATE_OFF,
    STATE_ON
)

from homeassistant.components.light import (
    ATTR_COLOR_TEMP
)

from homeassistant.helpers import device_registry, entity_registry

from .const import (
    DOMAIN,
    MINMAX_MIREDS
)

from .common import (
    async_fire_time_changed_now_time,
    turn_on_lights,
    some_day_time,
    some_night_time,
    some_evening_time
)

from custom_components.redshift import async_setup


async def test_no_call_right_after_setup(
        hass,
        turn_on_service,
        lights,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.async_block_till_done()

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_service_turn_on_call_two_lights_two_on(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 2


async def test_service_active_inactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    hass.states.async_set('redshift.active', False)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', True)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_light_goes_on_while_inactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    hass.states.async_set('redshift.active', False)

    hass.states.async_set('light.light_1', STATE_OFF, attributes=MINMAX_MIREDS)

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    attrs = {ATTR_COLOR_TEMP: 390}
    attrs.update(MINMAX_MIREDS)
    hass.states.async_set('light.light_1', STATE_ON, attrs)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', True)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_override_while_active_then_reactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    await turn_on_lights(hass, ['light_1'], color_temp=390)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', False)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('redshift.active', True)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_service_turn_on_call_four_lights_four_on(
        hass,
        more_lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2', 'light_3', 'light_4'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 4


async def test_service_turn_on_call_four_lights_1_3_on(
        hass,
        more_lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_3'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 2

    on_lights = set([call.data[ATTR_ENTITY_ID] for call in turn_on_service])
    assert on_lights == {'light.light_1', 'light.light_3'}


async def test_service_turn_on_call_four_lights_3_manually_set_color_temp(
        hass,
        more_lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_3'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    turn_on_service.pop()
    turn_on_service.pop()

    hass.states.async_set('light.light_3', STATE_ON, attributes={ATTR_COLOR_TEMP: 390})
    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1'}

    turn_on_service.pop()

    hass.states.async_set('light.light_3', STATE_OFF, attributes=MINMAX_MIREDS)
    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1'}

    turn_on_service.pop()

    await turn_on_lights(hass, ['light_3'])

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 2
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1', 'light.light_3'}


async def test_redshift_day_to_night(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 400


async def test_redshift_night_to_day(
        hass,
        lights,
        turn_on_service,
        start_at_night
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 160


async def test_redshift_day_to_night_non_default_night_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    config = dict(night_color_temp=2571)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 389


async def test_redshift_night_to_day_non_default_day_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_night
):
    config = dict(day_color_temp=5000)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 200


async def test_redshift_to_evening(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    config = dict()
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 280


async def test_redshift_to_evening_non_default_evening_range(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    config = dict(
        evening_time="18:00",
        night_time="00:00"
    )
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
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

    old_color_temp = None
    for time, expected in zip(["04:30", "05:30", "06:30"], expected_color_temps):
        time = DT.datetime.fromisoformat("2020-12-13 %s:00" % time)

        start_at_night.move_to(time)
        async_fire_time_changed_now_time(hass)

        await hass.async_block_till_done()

        assert hass.states.get('light.light_1').attributes.get(ATTR_COLOR_TEMP) == expected


async def test_redshift_during_evening_rounding_error(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    config = dict()
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == 280

    for i in range(10):
        start_at_noon.tick(120.0)
        async_fire_time_changed_now_time(hass)
        await hass.async_block_till_done()
        assert len(turn_on_service) == 1

        turn_on_service.pop()


async def test_redshift_day_to_night_exceed_mired(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    config = dict(night_color_temp=2000)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 400


async def test_redshift_night_to_day_exceed_mired(
        hass,
        lights,
        turn_on_service,
        start_at_night
):
    config = dict(day_color_temp=6500)
    assert await async_setup(hass, {DOMAIN: config})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    assert turn_on_service[0].data[ATTR_COLOR_TEMP] == 160



async def test_redshift_no_change(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    turn_on_service.pop()

    start_at_noon.tick(1)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_redshift_dont_touch(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('redshift', 'dont_touch', {ATTR_ENTITY_ID: 'light.light_2'})
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_ENTITY_ID] == 'light.light_1'
    assert len(turn_on_service) == 0

    await hass.services.async_call('redshift', 'dont_touch', {ATTR_ENTITY_ID: 'light.light_1'})
    await hass.async_block_till_done()

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call('redshift', 'handle_again', {ATTR_ENTITY_ID: 'light.light_2'})
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_redshift_dont_touch_devices(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])

    await hass.services.async_call(
        'redshift',
        'dont_touch',
        {ATTR_DEVICE_ID: 'device_id_light_1'}
    )

    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_ENTITY_ID] == 'light.light_2'
    assert len(turn_on_service) == 0

    await hass.services.async_call(
        'redshift',
        'dont_touch',
        {ATTR_DEVICE_ID: 'device_id_light_2'}
    )

    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call('redshift', 'handle_again', {ATTR_DEVICE_ID: 'device_id_light_1'})
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_redshift_handle_again_non_ignored(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.services.async_call('redshift', 'handle_again', {ATTR_ENTITY_ID: 'light.light_2'})


async def test_redshift_deactivate_with_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('redshift', 'deactivate', {'color_temp': 2571})
    await hass.async_block_till_done()

    assert hass.states.get('redshift.active').state == 'False'

    assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == 389
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == 389

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_redshift_deactivate_no_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('redshift', 'deactivate', {})
    await hass.async_block_till_done()

    assert hass.states.get('redshift.active').state == 'False'

    assert len(turn_on_service) == 0


async def test_redshift_go_redshift(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('redshift', 'deactivate', {'color_temp': 2571})
    await hass.async_block_till_done()
    assert hass.states.get('redshift.active').state == 'False'

    await hass.services.async_call('redshift', 'activate', {})
    await hass.async_block_till_done()

    assert hass.states.get('redshift.active').state == 'True'

    assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == 160
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP] == 160
