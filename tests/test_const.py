"""Test configuration normalization helpers."""

import datetime as dt

from custom_components.sunset.const import (
    CONF_BED_TIME,
    CONF_BRIGHTNESS_ENABLED,
    CONF_EXCLUDED_ENTITIES,
    normalize_config,
)


def test_normalize_time_objects_and_excluded_entities():
    config = normalize_config(
        {
            "evening_time": dt.time(17, 0),
            "excluded_entities": "light.kitchen",
        }
    )

    assert config["evening_time"] == "17:00"
    assert config["excluded_entities"] == ["light.kitchen"]


def test_normalize_explicit_brightness_and_empty_exclusions():
    config = normalize_config(
        {
            CONF_BRIGHTNESS_ENABLED: False,
            CONF_BED_TIME: "01:00",
            CONF_EXCLUDED_ENTITIES: [],
        }
    )

    assert config[CONF_BRIGHTNESS_ENABLED] is False
    assert config[CONF_BED_TIME] is None
    assert config[CONF_EXCLUDED_ENTITIES] == []
