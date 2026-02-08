

import freezegun as FG
import pytest

from custom_components.sunset.calculator import RedshiftCalculator


def test_setup_redshift_calculator_default():
    RedshiftCalculator()


def test_setup_redshift_calculator():
    RedshiftCalculator(
        evening_time="17:00",
        night_time="23:00",
        morning_time="07:00",
        day_color_temp=5000,
        night_color_temp=2000,
    )


@pytest.mark.parametrize("day_color_temp", [6000, 6250])
def test_redshift_value_daytime(day_color_temp):
    calculator = RedshiftCalculator(
        evening_time="17:00",
        night_time="23:00",
        morning_time="07:00",
        day_color_temp=day_color_temp,
        night_color_temp=2000,
    )
    with FG.freeze_time("2020-12-13 14:00:00"):
        assert calculator.color_temp() == day_color_temp


@pytest.mark.parametrize("night_color_temp", [2000, 2500])
def test_redshift_value_nighttime(night_color_temp):
    calculator = RedshiftCalculator(
        evening_time="17:00",
        night_time="23:00",
        morning_time="07:00",
        day_color_temp=6000,
        night_color_temp=night_color_temp,
    )
    with FG.freeze_time("2020-12-13 23:30:00"):
        assert calculator.color_temp() == night_color_temp


def test_redshift_value_nighttime_after_midnight():
    calculator = RedshiftCalculator(
        evening_time="17:00",
        night_time="23:00",
        morning_time="07:00",
        day_color_temp=6250,
        night_color_temp=2500,
    )
    with FG.freeze_time("2020-12-13 01:30:00"):
        assert calculator.color_temp() == 2500


def test_redshift_value_nighttime_change_after_midnight():
    calculator = RedshiftCalculator(
        evening_time="17:00",
        night_time="01:00",
        morning_time="07:00",
        day_color_temp=6000,
        night_color_temp=2500,
    )
    with FG.freeze_time("2020-12-13 01:30:00"):
        assert calculator.color_temp() == 2500


@pytest.mark.parametrize(("time", "expected"), [
    ("20:00", 4500),
    ("19:00", 5000),
    ("21:00", 4000),
    ("17:00", 6000),
    ("23:00", 3000),
])
def test_redshift_value_evening_time(time, expected):
    calculator = RedshiftCalculator(
        evening_time="17:00",
        night_time="23:00",
        morning_time="07:00",
        day_color_temp=6000,
        night_color_temp=3000,
    )
    with FG.freeze_time(f"2020-12-13 {time}:00"):
        assert calculator.color_temp() == expected


@pytest.mark.parametrize(("evening", "night", "now"), [
    ("23:00", "01:00", "00:00"),
    ("21:00", "01:00", "23:00"),
    ("23:00", "03:00", "01:00"),
])
def test_redshift_value_evening_time_after_midnight(evening, night, now):
    calculator = RedshiftCalculator(
        evening_time=evening,
        night_time=night,
        morning_time="07:00",
        day_color_temp=6000,
        night_color_temp=2500,
    )
    with FG.freeze_time(f"2020-12-13 {now}:00"):
        assert calculator.color_temp() == 4250
