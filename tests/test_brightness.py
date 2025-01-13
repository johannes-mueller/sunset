
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ON
)

from homeassistant.components.light import (
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    COLOR_MODE_BRIGHTNESS
)



from custom_components.sunset import async_setup


from .common import (
    async_fire_time_changed_now_time,
    turn_on_lights,
    some_day_time,
    some_evening_time,
    some_night_time,
)

from .const import DOMAIN


async def test_service_active_no_change(
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

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 254


async def test_service_active_no_change_two_lights(
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


async def test_day_to_night(
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

    turn_on_service.pop()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127


async def test_day_to_night_alternative_night_brightness(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {'night_brightness': 192}})
    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    turn_on_service.pop()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 192


async def test_day_to_night_no_bed_time(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {'bed_time': 'null'}})
    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    turn_on_service.pop()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 254


async def test_day_to_night_changed_brightness_no_bed_time(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {'bed_time': 'null'}})
    attrs = {
        ATTR_SUPPORTED_COLOR_MODES: [COLOR_MODE_BRIGHTNESS],
        ATTR_BRIGHTNESS: 192
    }
    hass.states.async_set('light.light_1', STATE_ON, attrs)

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_night_to_day(
        hass,
        lights,
        turn_on_service,
        start_at_night
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1'])

    start_at_night.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    turn_on_service.pop()

    start_at_night.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 254


async def test_day_to_night_sunset_inactive(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})
    hass.states.async_set('sunset.redshift_active', False)

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0
    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127


async def test_brightness_deactivate_with_brightness(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('sunset', 'deactivate_brightness', {'brightness': 192})
    await hass.async_block_till_done()

    assert hass.states.get('sunset.brightness_active').state == 'False'

    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 192
    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 192

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_brightness_deactivate_no_brightness(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('sunset', 'deactivate_brightness', {})
    await hass.async_block_till_done()

    assert hass.states.get('sunset.brightness_active').state == 'False'

    assert len(turn_on_service) == 0


async def test_day_to_night_brightness_inactive_active(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})
    hass.states.async_set('sunset.brightness_active', False)

    await turn_on_lights(hass, ['light_1'])

    start_at_noon.move_to(some_day_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    turn_on_service.pop()

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 254

    hass.states.async_set('sunset.brightness_active', True)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127


async def test_override_brightness_do_not_touch_night(
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

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127

    await turn_on_lights(hass, ['light_1'], brightness=192)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_override_brightness_do_not_touch_evening(
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
    assert call.data[ATTR_BRIGHTNESS] == 254

    await turn_on_lights(hass, ['light_1'], brightness=192)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1
    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 192


async def test_override_color_temp_do_touch(
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
    assert call.data[ATTR_BRIGHTNESS] == 254

    await turn_on_lights(hass, ['light_1'], color_temp=4000)

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 1

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127


async def test_override_while_active_then_reactivate(
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

    call = turn_on_service.pop()
    assert call.data[ATTR_BRIGHTNESS] == 127

    await turn_on_lights(hass, ['light_1'], brightness=192)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('sunset.brightness_active', False)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0

    hass.states.async_set('sunset.brightness_active', True)

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_brightness_bwlight(
        hass,
        bw_light,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['bwlight_1'])

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 0


async def test_brightness_dimlight(
        hass,
        dim_light,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['dimlight_1'])

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)

    await hass.async_block_till_done()

    assert len(turn_on_service) == 1


async def test_brightness_go_brightness(
        hass,
        lights,
        turn_on_service,
        start_at_noon
):
    assert await async_setup(hass, {DOMAIN: {}})

    await turn_on_lights(hass, ['light_1', 'light_2'])
    await hass.services.async_call('sunset', 'deactivate_brightness', {'brightness': 192})
    await hass.async_block_till_done()
    assert hass.states.get('sunset.brightness_active').state == 'False'

    await hass.services.async_call('sunset', 'activate_brightness', {})
    await hass.async_block_till_done()

    assert hass.states.get('sunset.brightness_active').state == 'True'

    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 254
    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 254


async def test_manual_brightness_not_intervened_by_redshift(
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

    await turn_on_lights(hass, ['light_1'], brightness=128)
    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 128

    start_at_noon.move_to(some_evening_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 128

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert turn_on_service.pop().data[ATTR_BRIGHTNESS] == 128


async def test_global_brightness(hass, start_at_noon):
    assert await async_setup(hass, {DOMAIN: {}})

    start_at_noon.tick(600)
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert hass.states.get('sunset.brightness').state == '254'

    start_at_noon.move_to(some_night_time())
    async_fire_time_changed_now_time(hass)
    await hass.async_block_till_done()

    assert hass.states.get('sunset.brightness').state == '127'
