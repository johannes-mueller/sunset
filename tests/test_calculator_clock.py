"""Semantics tests for the time calculations with an injected clock.

These tests define the window semantics of the calculators:

- before ``evening_time`` it is day and the target colour temperature is
  the day colour temperature,
- between ``evening_time`` and ``night_time`` the colour temperature
  interpolates linearly from the day to the night colour temperature,
- between ``night_time`` and ``morning_time`` — wrapping midnight — it
  is night,
- from ``morning_time`` on it is day again; the window tests compare
  with strict ``>``/``<`` so exactly at a boundary instant the previous
  window has just ended, except that the mid-window interpolation
  already reaches the window value at its boundary (at exactly
  ``night_time`` the interpolated colour temperature equals the night
  colour temperature, and at exactly ``bed_time`` the night window has
  not yet begun),
- all of this must hold for calendars with DST transitions and with the
  window wrapping midnight.
"""

import datetime as dt
import zoneinfo

from custom_components.sunset.calculator import DaytimeCalculator, RedshiftCalculator

BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


def make_now(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
    second: int = 0,
    tzinfo: dt.tzinfo | None = None,
):
    """Build a fixed clock returning a single instant."""
    time = dt.datetime(year, month, day, hour, minute, second, tzinfo=tzinfo)
    return lambda: time


class TestRedshiftWindows:
    """Colour temperature windows with an injected clock."""

    def test_day_before_evening(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 1, 12, 0),
            evening_time="17:00",
            night_time="23:00",
            morning_time="06:00",
            day_color_temp=6250,
            night_color_temp=2500,
        )
        assert calculator.is_day()
        assert not calculator.is_night()
        assert calculator.color_temp() == 6250

    def test_exactly_at_evening_ends_the_day(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 1, 17, 0),
            day_color_temp=6250,
            night_color_temp=2500,
        )
        assert not calculator.is_day()
        assert not calculator.is_night()
        assert calculator.color_temp() == 6250

    def test_interpolation_midpoint(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 1, 20, 0),
            evening_time="17:00",
            night_time="23:00",
            day_color_temp=6000,
            night_color_temp=3000,
        )
        assert not calculator.is_day()
        assert not calculator.is_night()
        assert calculator.color_temp() == 4500

    def test_interpolation_shortly_after_evening(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 1, 17, 0, 30),
            evening_time="17:00",
            night_time="23:00",
            day_color_temp=6000,
            night_color_temp=3000,
        )
        assert 5900 < calculator.color_temp() < 6000

    def test_exactly_at_night_reached_the_night_value(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 1, 23, 0),
            night_time="23:00",
            morning_time="06:00",
            day_color_temp=6000,
            night_color_temp=3000,
        )
        assert not calculator.is_night()
        assert calculator.color_temp() == 3000

    def test_night_wraps_midnight(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 2, 2, 30),
            night_time="23:00",
            morning_time="06:00",
        )
        assert calculator.is_night()
        assert calculator.color_temp() == 2500

    def test_exactly_at_morning_is_day_again(self):
        calculator = RedshiftCalculator(
            now=make_now(2026, 11, 2, 6, 0),
            night_time="23:00",
            morning_time="06:00",
            day_color_temp=6250,
        )
        assert not calculator.is_night()
        assert calculator.is_day()
        assert calculator.color_temp() == 6250

    def test_clock_is_reconsulted(self):
        clock = {"now": dt.datetime(2026, 11, 1, 12, 0)}
        calculator = RedshiftCalculator(now=lambda: clock["now"])
        assert calculator.color_temp() == 6250
        clock["now"] = dt.datetime(2026, 11, 1, 20, 0)
        assert calculator.color_temp() == 4375


class TestDaytimeCalculatorWindows:
    """Bed-time window of the brightness calculator."""

    def test_bed_at_midnight_wraps(self):
        calculator = DaytimeCalculator(
            night_time="00:00",
            morning_time="06:00",
            now=make_now(2026, 11, 1, 23, 59),
        )
        assert not calculator.is_night()

    def test_night_after_bed_time(self):
        calculator = DaytimeCalculator(
            night_time="00:00",
            morning_time="06:00",
            now=make_now(2026, 11, 2, 0, 1),
        )
        assert calculator.is_night()

    def test_exactly_at_bed_time_is_not_night(self):
        calculator = DaytimeCalculator(
            night_time="00:00",
            morning_time="06:00",
            now=make_now(2026, 11, 2, 0, 0),
        )
        assert not calculator.is_night()

    def test_exactly_at_morning_still_reports_night(self):
        # For a bed window whose ``bed_time`` is earlier than
        # ``morning_time``, exactly at the morning instant the night
        # start has not yet wrapped to the next day, so the strict
        # ``now > night_start`` comparison still reports night at that
        # single instant. This quirk is part of the legacy semantics.
        calculator = DaytimeCalculator(
            night_time="00:00",
            morning_time="06:00",
            now=make_now(2026, 11, 2, 6, 0),
        )
        assert calculator.is_night()

    def test_right_after_morning_is_not_night(self):
        calculator = DaytimeCalculator(
            night_time="00:00",
            morning_time="06:00",
            now=make_now(2026, 11, 2, 6, 0, 1),
        )
        assert not calculator.is_night()

    def test_bed_time_in_the_middle_of_the_night(self):
        calculator = DaytimeCalculator(
            night_time="23:30",
            morning_time="06:00",
            now=make_now(2026, 11, 2, 3, 0),
        )
        assert calculator.is_night()

    def test_not_night_in_the_evening(self):
        calculator = DaytimeCalculator(
            night_time="00:00",
            morning_time="06:00",
            now=make_now(2026, 11, 1, 22, 0),
        )
        assert not calculator.is_night()


class TestDstHandling:
    """Aware clocks and DST transitions."""

    def test_night_wrap_on_dst_spring_change_day(self):
        spring_forward = dt.datetime(2026, 3, 29, 1, 30, tzinfo=BERLIN)
        calculator = RedshiftCalculator(
            now=lambda: spring_forward,
            night_time="23:00",
            morning_time="06:00",
            day_color_temp=6250,
            night_color_temp=2500,
        )
        assert calculator.is_night()
        assert calculator.color_temp() == 2500

    def test_morning_on_dst_fall_back_day(self):
        fall_back = dt.datetime(2025, 10, 26, 6, 0, tzinfo=BERLIN)
        calculator = RedshiftCalculator(
            now=lambda: fall_back,
            night_time="23:00",
            morning_time="06:00",
            day_color_temp=6250,
        )
        assert not calculator.is_night()
        assert calculator.is_day()

    def test_interpolation_span_is_nominal_on_a_dst_change_day(self):
        calculator = RedshiftCalculator(
            now=lambda: dt.datetime(2026, 3, 29, 20, 0, tzinfo=BERLIN),
            evening_time="17:00",
            night_time="23:00",
            day_color_temp=6000,
            night_color_temp=3000,
        )
        assert calculator.color_temp() == 4500


def test_clock_injection_matches_legacy_day_behaviour():
    """The calculators work with any clock injection."""
    calculator = RedshiftCalculator(
        now=lambda: dt.datetime(2026, 11, 1, 13, 37),
        evening_time="17:00",
        night_time="23:00",
        morning_time="06:00",
    )
    assert calculator.color_temp() == 6250
