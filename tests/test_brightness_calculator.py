import pytest

import freezegun as FG

from custom_components.redshift.calculator import BrightnessCalculator


def test_setup_brightness_calculator():
    BrightnessCalculator(
        night_time="23:00",
        morning_time="06:00"
    )


@pytest.mark.parametrize('now_time, expected', [
    ("12:00", False),
    ("23:30", True),
    ("02:00", True),
    ("07:00", False)
])
def test_is_night_23_06(now_time, expected):
    calculator = BrightnessCalculator(
        night_time="23:00",
        morning_time="06:00"
    )

    with FG.freeze_time("2021-11-07 %s:00" % now_time):
        assert calculator.is_night() == expected


@pytest.mark.parametrize('now_time, expected', [
    ("12:00", False),
    ("23:30", False),
    ("00:30", False),
    ("02:00", True),
    ("07:00", False)
])
def test_is_night_01_06(now_time, expected):
    calculator = BrightnessCalculator(
        night_time="01:00",
        morning_time="06:00"
    )

    with FG.freeze_time("2021-11-07 %s:00" % now_time):
        assert calculator.is_night() == expected
