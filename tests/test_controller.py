"""Unit tests for the SunsetController decision logic.

These tests exercise the controller without any ``hass`` instance. The
controller receives plain ``HA.State`` objects (which do not need a hass
instance to be constructed) and decides what to command — it never
issues service calls itself.
"""

import datetime as dt
from typing import TYPE_CHECKING, Any

import homeassistant.core as HA
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    ColorMode,
)

from custom_components.sunset.calculator import DaytimeCalculator, RedshiftCalculator
from custom_components.sunset.const import (
    CONF_BED_TIME,
    CONF_BRIGHTNESS_ENABLED,
    CONF_DAY_COLOR_TEMP,
    CONF_EVENING_TIME,
    CONF_EXCLUDED_ENTITIES,
    CONF_MORNING_TIME,
    CONF_NIGHT_BRIGHTNESS,
    CONF_NIGHT_COLOR_TEMP,
    CONF_NIGHT_TIME,
    MAX_DAY_BRIGHTNESS,
)
from custom_components.sunset.controller import SunsetController

NOON = dt.datetime(2026, 11, 1, 12, 0)
NIGHT = dt.datetime(2026, 11, 1, 2, 0)

if TYPE_CHECKING:
    from collections.abc import Callable


def light_state(
    entity_id: str = "light.light_1",
    *,
    supported_modes: list[ColorMode] | None = None,
    brightness: int | None = 254,
    color_temp_kelvin: int | None = 2630,
    min_color_temp_kelvin: int = 2000,
    max_color_temp_kelvin: int = 6500,
) -> HA.State:
    """Build a light state like ``tests.common.make_lights`` does."""
    supported = supported_modes or [ColorMode.COLOR_TEMP, ColorMode.XY]
    attrs: dict[str, Any] = {ATTR_SUPPORTED_COLOR_MODES: list(supported)}
    if ColorMode.COLOR_TEMP in supported:
        attrs[ATTR_MIN_COLOR_TEMP_KELVIN] = min_color_temp_kelvin
        attrs[ATTR_MAX_COLOR_TEMP_KELVIN] = max_color_temp_kelvin
        if color_temp_kelvin is not None:
            attrs[ATTR_COLOR_TEMP_KELVIN] = color_temp_kelvin
    if brightness is not None:
        attrs[ATTR_BRIGHTNESS] = brightness
    return HA.State(entity_id, "on", attrs)


def make_controller(
    *,
    night_time: str = "23:00",
    bed_time: str = "00:00",
    morning_time: str = "06:00",
    evening_time: str = "17:00",
    day_color_temp: int = 6000,
    night_color_temp: int = 3000,
    night_brightness: int = 127,
    brightness_enabled: bool = True,
    excluded: list[str] | None = None,
    brightness_clock: Callable[[], dt.datetime] | None = None,
) -> SunsetController:
    """Build a controller with a deterministic noon clock."""
    config = {
        CONF_NIGHT_TIME: night_time,
        CONF_BED_TIME: bed_time,
        CONF_MORNING_TIME: morning_time,
        CONF_EVENING_TIME: evening_time,
        CONF_DAY_COLOR_TEMP: day_color_temp,
        CONF_NIGHT_COLOR_TEMP: night_color_temp,
        CONF_NIGHT_BRIGHTNESS: night_brightness,
        CONF_BRIGHTNESS_ENABLED: brightness_enabled,
        CONF_EXCLUDED_ENTITIES: excluded or [],
    }
    clock = lambda: NOON  # noqa: E731
    redshift_calculator = RedshiftCalculator(
        now=clock,
        evening_time=evening_time,
        night_time=night_time,
        morning_time=morning_time,
        day_color_temp=day_color_temp,
        night_color_temp=night_color_temp,
    )
    brightness_calculator = (
        DaytimeCalculator(
            night_time=bed_time,
            morning_time=morning_time,
            now=brightness_clock or clock,
        )
        if brightness_enabled
        else None
    )
    return SunsetController(
        config=config,
        redshift_calculator=redshift_calculator,
        brightness_calculator=brightness_calculator,
    )


def night_controller() -> SunsetController:
    """A controller whose brightness calculator observes night time."""
    return make_controller(brightness_clock=lambda: NIGHT)


class TestActivationFlags:
    """The redshift and brightness activation flags."""

    def test_initially_active(self):
        controller = make_controller()
        assert controller.redshift_active
        assert controller.brightness_active

    def test_activate_redshift_clears_manual_value_and_reactivates(self):
        controller = make_controller()
        controller.deactivate_redshift(color_temp=4000)
        controller.set_redshift_active(active=False)

        controller.activate_redshift()

        assert controller.redshift_active is True
        assert controller.manual_color_temp is None

    def test_deactivate_redshift_with_value_wants_immediate_apply(self):
        controller = make_controller()
        assert controller.deactivate_redshift(color_temp=4000) is True

    def test_deactivate_redshift_without_value_does_not_apply(self):
        controller = make_controller()
        assert controller.deactivate_redshift(color_temp=None) is False

    def test_deactivate_redshift_keeps_flag_until_explicitly_set(self):
        controller = make_controller()
        controller.deactivate_redshift(color_temp=None)
        assert controller.redshift_active is True

        controller.set_redshift_active(active=False)

        assert controller.redshift_active is False

    def test_deactivate_brightness_with_value_wants_immediate_apply(self):
        controller = make_controller()
        assert controller.deactivate_brightness(brightness=100) is True
        assert controller.manual_brightness == 100

    def test_deactivate_brightness_without_value_does_not_apply(self):
        controller = make_controller()
        assert controller.deactivate_brightness(brightness=None) is False

    def test_activate_brightness(self):
        controller = make_controller()
        controller.set_brightness_active(active=False)

        controller.activate_brightness()

        assert controller.brightness_active is True
        assert controller.manual_brightness is None


class TestTargets:
    """Global targets reported for sensors."""

    def test_target_color_temp_is_day_value_at_noon(self):
        controller = make_controller(day_color_temp=6000)
        assert controller.target_color_temp() == 6000

    def test_manual_color_temp_wins(self):
        controller = make_controller()
        controller.deactivate_redshift(color_temp=4000)
        assert controller.target_color_temp() == 4000

    def test_target_brightness_during_day_is_max(self):
        controller = make_controller()
        assert controller.target_brightness() == MAX_DAY_BRIGHTNESS

    def test_target_brightness_during_night_is_night_brightness(self):
        controller = night_controller()
        assert controller.target_brightness() == 127

    def test_manual_brightness_wins(self):
        controller = make_controller()
        controller.deactivate_brightness(brightness=100)
        assert controller.target_brightness() == 100

    def test_target_brightness_without_brightness_support_is_none(self):
        controller = make_controller(brightness_enabled=False)
        assert controller.target_brightness() is None


class TestColorTempCommands:
    """Colour temperature commanding per light."""

    def test_commands_target_for_color_temp_light(self):
        controller = make_controller(day_color_temp=6000)
        state = light_state(color_temp_kelvin=2630)
        assert controller.compute_commands("light.light_1", state) == {
            ATTR_COLOR_TEMP_KELVIN: 6000
        }

    def test_clamps_to_light_colour_upper_bound(self):
        controller = make_controller(day_color_temp=6000)
        state = light_state(color_temp_kelvin=2630, max_color_temp_kelvin=5500)
        assert controller.compute_commands("light.light_1", state) == {
            ATTR_COLOR_TEMP_KELVIN: 5500
        }

    def test_clamps_to_light_colour_lower_bound(self):
        controller = make_controller(day_color_temp=6000)
        state = light_state(color_temp_kelvin=2630, min_color_temp_kelvin=6100)
        assert controller.compute_commands("light.light_1", state) == {
            ATTR_COLOR_TEMP_KELVIN: 6100
        }

    def test_no_command_for_onoff_light(self):
        controller = make_controller()
        state = light_state(
            supported_modes=[ColorMode.ONOFF],
            color_temp_kelvin=None,
        )
        assert controller.compute_commands("light.light_1", state) == {}

    def test_no_command_when_target_reached(self):
        controller = make_controller(day_color_temp=6000)
        state = light_state(color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", state) == {}

    def test_no_command_when_redshift_inactive(self):
        controller = make_controller(day_color_temp=6000)
        controller.set_redshift_active(active=False)
        state = light_state(color_temp_kelvin=2630)
        assert controller.compute_commands("light.light_1", state) == {}

    def test_external_change_overrides(self):
        controller = make_controller()
        tracked_state = light_state(color_temp_kelvin=2630)
        controller.record_command(
            "light.light_1",
            {ATTR_COLOR_TEMP_KELVIN: 6000},
            tracked_state,
        )
        current = light_state(color_temp_kelvin=5000)
        assert controller.compute_commands("light.light_1", current) == {}

    def test_stable_target_is_not_recommanded(self):
        controller = make_controller()
        state = light_state(color_temp_kelvin=5000)
        controller.record_command(
            "light.light_1",
            {ATTR_COLOR_TEMP_KELVIN: 6000},
            state,
        )
        updated = light_state(color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", updated) == {}


class TestBrightnessCommands:
    """Brightness commanding per light."""

    def test_commands_day_target_for_dimmable_light(self):
        controller = make_controller()
        state = light_state(brightness=180, color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", state) == {
            ATTR_BRIGHTNESS: MAX_DAY_BRIGHTNESS
        }

    def test_no_command_for_onoff_light(self):
        controller = make_controller()
        state = light_state(
            supported_modes=[ColorMode.ONOFF],
            brightness=254,
            color_temp_kelvin=None,
        )
        assert controller.compute_commands("light.light_1", state) == {}

    def test_no_command_when_target_reached(self):
        controller = make_controller()
        state = light_state(brightness=MAX_DAY_BRIGHTNESS, color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", state) == {}

    def test_no_command_when_inactive(self):
        controller = make_controller()
        controller.set_brightness_active(active=False)
        state = light_state(brightness=100, color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", state) == {}

    def test_night_brightness_value(self):
        controller = night_controller()
        state = light_state(brightness=254, color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", state) == {
            ATTR_BRIGHTNESS: 127
        }

    def test_external_brightness_change_overrides(self):
        controller = make_controller()
        tracked_state = light_state(brightness=254, color_temp_kelvin=6000)
        controller.record_command(
            "light.light_1",
            {ATTR_BRIGHTNESS: 127},
            tracked_state,
        )
        current = light_state(brightness=200, color_temp_kelvin=6000)
        assert controller.compute_commands("light.light_1", current) == {}


class TestTrackingLifecycle:
    """Tracking clears when lights go off."""

    def test_command_again_after_off_and_on(self):
        controller = make_controller()
        tracked_state = light_state(color_temp_kelvin=2630)
        controller.record_command(
            "light.light_1",
            {ATTR_COLOR_TEMP_KELVIN: 6000},
            tracked_state,
        )
        controller.light_off("light.light_1")

        fresh_on = light_state(color_temp_kelvin=5000)
        assert controller.compute_commands("light.light_1", fresh_on) == {
            ATTR_COLOR_TEMP_KELVIN: 6000
        }

    def test_forget_unless_on_removes_off_lights(self):
        controller = make_controller()
        controller.record_command(
            "light.on",
            {},
            light_state(entity_id="light.on", color_temp_kelvin=3000),
        )
        controller.record_command(
            "light.off",
            {},
            light_state(entity_id="light.off", color_temp_kelvin=3000),
        )

        controller.forget_unless_on(["light.on"])

        assert controller.compute_commands(
            "light.off", light_state(entity_id="light.off")
        ) == {ATTR_COLOR_TEMP_KELVIN: 6000}


class TestIgnoredLight:
    """dont_touch and excluded entities are never commanded."""

    def test_excluded_from_config(self):
        controller = make_controller(excluded=["light.light_1"])
        state = light_state(color_temp_kelvin=2630)
        assert controller.compute_commands("light.light_1", state) == {}

    def test_dont_touch(self):
        controller = make_controller()
        controller.dont_touch(["light.light_1"])
        state = light_state(color_temp_kelvin=2630)
        assert controller.compute_commands("light.light_1", state) == {}

    def test_handle_again_removes_only_known(self):
        controller = make_controller()
        controller.dont_touch(["light.known", "light.other"])

        controller.handle_again(["light.known"])

        state = light_state(color_temp_kelvin=2630)
        assert controller.compute_commands("light.known", state) == {
            ATTR_COLOR_TEMP_KELVIN: 6000
        }

    def test_handle_again_still_leaves_other_ignored(self):
        controller = make_controller()
        controller.dont_touch(["light.known", "light.other"])

        controller.handle_again(["light.known"])

        state = light_state(color_temp_kelvin=2630)
        assert controller.compute_commands("light.other", state) == {}

    def test_handle_again_reports_unknown(self):
        controller = make_controller()
        assert controller.handle_again(["light.unknown"]) == ["light.unknown"]
