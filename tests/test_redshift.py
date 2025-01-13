import pytest

import datetime as DT

from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_ENTITY_ID,
    ATTR_DEVICE_ID,
    STATE_OFF,
    STATE_ON
)

from homeassistant.components.light import (
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_NAME,
    ATTR_COLOR_TEMP_KELVIN,
    COLOR_MODE_COLOR_TEMP
)

from homeassistant.helpers import device_registry, entity_registry

from .const import (
    DOMAIN,
    MINMAX_COLOR_TEMP_KELVIN,
    MAX_COLOR_TEMP_KELVIN,
    MIN_COLOR_TEMP_KELVIN
)

from .common import (
    async_fire_time_changed_now_time,
    turn_on_lights,
    some_day_time,
    some_night_time,
    some_evening_time
)

from custom_components.sunset import async_setup


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


async def test_service_catch_rounding_error(
        hass, lights, turn_on_service, start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    turn_on_service.pop()

    start_at_noon.tick(5)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


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

    hass.states.async_set('sunset.redshift_active', False)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('sunset.redshift_active', True)

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

    hass.states.async_set('sunset.redshift_active', False)

    hass.states.async_set('light.light_1', STATE_OFF, attributes=MINMAX_COLOR_TEMP_KELVIN)

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    attrs = {
        ATTR_COLOR_TEMP_KELVIN: 390,
        ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_COLOR_TEMP],
        ATTR_BRIGHTNESS: 254
    }
    attrs.update(MINMAX_COLOR_TEMP_KELVIN)
    hass.states.async_set('light.light_1', STATE_ON, attrs)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('sunset.redshift_active', True)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_override_brightness_do_touch(
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

    call = turn_on_service.pop()
    color_temp = call.data[ATTR_COLOR_TEMP_KELVIN]
    assert color_temp < MAX_COLOR_TEMP_KELVIN

    await turn_on_lights(hass, ['light_1'], brightness=192)

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    call = turn_on_service.pop()
    assert call.data[ATTR_COLOR_TEMP_KELVIN] == MIN_COLOR_TEMP_KELVIN


async def test_override_while_active_then_reactivate(
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

    hass.states.async_set('sunset.redshift_active', False)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('sunset.redshift_active', True)

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


async def test_service_turn_on_call_four_lights_3_override_color_temp(
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

    attrs = {ATTR_COLOR_TEMP_KELVIN: 390, ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_COLOR_TEMP]}
    hass.states.async_set('light.light_3', STATE_ON, attributes=attrs)
    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    on_lights = [call.data[ATTR_ENTITY_ID] for call in turn_on_service]
    assert set(on_lights) == {'light.light_1'}

    turn_on_service.pop()

    hass.states.async_set('light.light_3', STATE_OFF, attributes=MINMAX_COLOR_TEMP_KELVIN)
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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 2500


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 6250


async def test_redshift_bwlight(
        hass,
        bw_light,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['bwlight_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_redshift_dimlight(
        hass,
        dim_light,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['dimlight_1'])

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_redshift_light_in_color(
        hass,
        bw_light,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    attrs = {ATTR_COLOR_NAME: "green", ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_COLOR_TEMP]}
    attrs.update(MINMAX_COLOR_TEMP_KELVIN)
    hass.states.async_set('light.light_1', STATE_ON, attrs)

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 2571


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 5000


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 4375


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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 5000


@pytest.mark.parametrize('morning_time, expected_color_temps', [
    ("05:00", [2500, 6250, 6250]),
    ("06:00", [2500, 2500, 6250]),
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

    old_color_temp = None
    for time, expected in zip(["04:30", "05:30", "06:30"], expected_color_temps):
        time = DT.datetime.fromisoformat("2020-12-13 %s:00" % time)

        start_at_night.move_to(time)
        async_fire_time_changed_now_time(hass)

        await hass.async_block_till_done()

        assert hass.states.get('light.light_1').attributes.get(ATTR_COLOR_TEMP_KELVIN) == expected


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
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 4375

    for i in range(10):
        start_at_noon.tick(120.0)
        async_fire_time_changed_now_time(hass)
        await hass.async_block_till_done()
        assert len(turn_on_service) == 1

        turn_on_service.pop()


async def test_redshift_day_to_night_exceed_color_temp_kelvin(
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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 2500


async def test_redshift_night_to_day_exceed_color_temp_kelvin(
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
    assert turn_on_service[0].data[ATTR_COLOR_TEMP_KELVIN] == 6250



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
    await hass.services.async_call('sunset', 'dont_touch', {ATTR_ENTITY_ID: ['light.light_2']})
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_ENTITY_ID] == 'light.light_1'
    assert len(turn_on_service) == 0

    await hass.services.async_call('sunset', 'dont_touch', {ATTR_ENTITY_ID: ['light.light_1']})
    await hass.async_block_till_done()

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call('sunset', 'handle_again', {ATTR_ENTITY_ID: ['light.light_2']})
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_redshift_handle_again_key_error(
        hass,
        caplog
):
    assert await async_setup(hass, {DOMAIN: {}})

    await hass.services.async_call('sunset', 'handle_again', {ATTR_ENTITY_ID: ['some_stupidity']})
    await hass.async_block_till_done()

    assert not any(r.levelname == 'ERROR' for r in caplog.records)
    assert sum(1 for r in caplog.records if r.levelname == 'WARNING') == 1
    assert any(
        r.levelname == 'WARNING' and r.message == "Unknown entity_id: some_stupidity"
        for r in caplog.records
    )

    caplog.clear()

    assert not any(r.levelname == 'ERROR' for r in caplog.records)
    await hass.services.async_call('sunset', 'handle_again', {ATTR_ENTITY_ID: ['another_stupidity']})
    await hass.async_block_till_done()

    assert sum(1 for r in caplog.records if r.levelname == 'WARNING') == 1
    assert any(
        r.levelname == 'WARNING' and r.message == "Unknown entity_id: another_stupidity"
        for r in caplog.records
    )


async def test_redshift_handle_again_no_key_error(
        hass,
        caplog
):
    assert await async_setup(hass, {DOMAIN: {}})

    await hass.services.async_call('sunset', 'dont_touch', {ATTR_ENTITY_ID: ['some_stupidity']})
    await hass.async_block_till_done()
    await hass.services.async_call('sunset', 'handle_again', {ATTR_ENTITY_ID: ['some_stupidity']})
    await hass.async_block_till_done()

    assert not any(r.levelname == 'ERROR' for r in caplog.records)
    assert not any(
        r.levelname == 'WARNING' and r.message == "Unknown entity_id: some_stupidity"
        for r in caplog.records
    )


async def test_redshift_dont_touch_entity_id_not_as_list(
        hass,
        caplog
):
    assert await async_setup(hass, {DOMAIN: {}})
    await hass.services.async_call('sunset', 'dont_touch', {ATTR_ENTITY_ID: 'some_stupidity'})
    await hass.services.async_call('sunset', 'handle_again', {ATTR_ENTITY_ID: 'some_stupidity'})

    await hass.async_block_till_done()

    assert not any(r.levelname == 'WARNING' for r in caplog.records)


async def test_redshift_dont_touch_devices(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])

    await hass.services.async_call(
        'sunset',
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
        'sunset',
        'dont_touch',
        {ATTR_DEVICE_ID: 'device_id_light_2'}
    )

    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call(
        'sunset',
        'handle_again',
        {ATTR_DEVICE_ID: 'device_id_light_1'}
    )
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_redshift_dont_touch_areas(
        hass,
        lights,
        more_lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})
    await turn_on_lights(hass, ['light_1', 'light_2', 'light_3', 'light_4'])

    await hass.services.async_call(
        'sunset',
        'dont_touch',
        {ATTR_AREA_ID: 'area_1'}
    )

    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert {
        turn_on_service.pop().data[ATTR_ENTITY_ID],
        turn_on_service.pop().data[ATTR_ENTITY_ID]
    } == {'light.light_3', 'light.light_4'}

    assert len(turn_on_service) == 0

    await hass.services.async_call(
        'sunset',
        'dont_touch',
        {ATTR_AREA_ID: 'area_2'}
    )

    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    await hass.services.async_call(
        'sunset',
        'handle_again',
        {ATTR_AREA_ID: 'area_1'}
    )
    await hass.async_block_till_done()

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert {
        turn_on_service.pop().data[ATTR_ENTITY_ID],
        turn_on_service.pop().data[ATTR_ENTITY_ID]
    } == {'light.light_1', 'light.light_2'}

    assert len(turn_on_service) == 0


async def test_redshift_deactivate_with_color_temp(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('sunset', 'deactivate_redshift', {'color_temp': 2571})
    await hass.async_block_till_done()

    assert hass.states.get('sunset.redshift_active').state == 'False'

    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 2571
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 2571

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
    await hass.services.async_call('sunset', 'deactivate_redshift', {})
    await hass.async_block_till_done()

    assert hass.states.get('sunset.redshift_active').state == 'False'

    assert len(turn_on_service) == 0


async def test_redshift_go_redshift(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('sunset', 'deactivate_redshift', {'color_temp': 2571})
    await hass.async_block_till_done()
    assert hass.states.get('sunset.redshift_active').state == 'False'

    await hass.services.async_call('sunset', 'activate_redshift', {})
    await hass.async_block_till_done()

    assert hass.states.get('sunset.redshift_active').state == 'True'

    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 6250
    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 6250


async def test_redshift_only_relevant_attrs_in_call(
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
    assert set(turn_on_service[0].data.keys()) == {
        ATTR_ENTITY_ID,
        ATTR_COLOR_TEMP_KELVIN,
        ATTR_BRIGHTNESS
    }


async def test_manual_redshift_not_intervened_by_brightness(
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

    await turn_on_lights(hass, ['light_1'], color_temp=3500)
    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

#    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 3500

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

#    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 3500

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_COLOR_TEMP_KELVIN] == 3500


async def test_global_color_temp(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {}})

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert hass.states.get('sunset.color_temp_kelvin').state == '6250'

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert hass.states.get('sunset.color_temp_kelvin').state == '4375'
