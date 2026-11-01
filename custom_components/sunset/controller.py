"""Decision logic for the Sunset integration.

The controller owns all decisions: the global colour temperature and
brightness targets, the per-light tracked state for manual overrides,
and the ignored entities. It is pure decision logic — it neither touches
``hass`` nor issues service calls; the coordinator does that for it.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_SUPPORTED_COLOR_MODES,
    COLOR_MODES_BRIGHTNESS,
    ColorMode,
)

from .const import (
    CONF_EXCLUDED_ENTITIES,
    CONF_NIGHT_BRIGHTNESS,
    MAX_DAY_BRIGHTNESS,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import State

    from .calculator import DaytimeCalculator, RedshiftCalculator


@dataclass(slots=True)
class LightTrack:
    """Explicitly tracked facts about a light while it has been on.

    Sunset records what it last commanded per light. The `HA.State`
    snapshots are replaced by these explicit values so that external
    changes are recognized by comparing facts, not synthetic states.
    """

    brightness: int | None = None
    color_temp_kelvin: int | None = None


class SunsetController:
    """Compute targets and per-light commands as pure decision logic."""

    def __init__(
        self,
        config: dict[str, typing.Any],
        redshift_calculator: RedshiftCalculator,
        brightness_calculator: DaytimeCalculator | None,
    ) -> None:
        """Initialise the controller with config and calculators."""
        self.config = config
        self.redshift_calculator = redshift_calculator
        self.brightness_calculator = brightness_calculator

        self.redshift_active = True
        self.brightness_active = True

        self.manual_color_temp: int | None = None
        self.manual_brightness: int | None = None

        self.ignored: set[str] = set(config[CONF_EXCLUDED_ENTITIES])
        self.tracked: dict[str, LightTrack] = {}

    # --- global targets -------------------------------------------------

    def target_color_temp(self) -> int:
        """Return the target colour temperature in Kelvin."""
        if self.manual_color_temp is not None:
            return self.manual_color_temp
        return round(self.redshift_calculator.color_temp())

    def target_brightness(self) -> int | None:
        """Return the target brightness, or None without brightness support."""
        if self.manual_brightness is not None:
            return self.manual_brightness
        if self.brightness_calculator is None:
            return None
        if self.brightness_calculator.is_night():
            return self.config[CONF_NIGHT_BRIGHTNESS]
        return MAX_DAY_BRIGHTNESS

    # --- activation flags and manual values ------------------------------

    def activate_redshift(self) -> None:
        """Reactivate automatic redshifting."""
        self.manual_color_temp = None
        self.redshift_active = True

    def deactivate_redshift(self, color_temp: int | None = None) -> bool:
        """Store a deactivation with an optional manual colour temperature.

        Returns whether the lights must be updated immediately. The
        ``redshift_active`` flag is deliberately left untouched: the
        historical service ordering applies a manual value from the
        still-activated state before switching the flag off.
        """
        self.manual_color_temp = color_temp
        return color_temp is not None

    def set_redshift_active(self, *, active: bool) -> None:
        """Set the redshift activation flag."""
        self.redshift_active = active

    def activate_brightness(self) -> None:
        """Reactivate automatic brightness handling."""
        self.manual_brightness = None
        self.brightness_active = True

    def deactivate_brightness(self, brightness: int | None = None) -> bool:
        """Store a deactivation with an optional manual brightness.

        Returns whether the lights must be updated immediately. As with
        ``deactivate_redshift``, the flag is set separately afterwards.
        """
        self.manual_brightness = brightness
        return brightness is not None

    def set_brightness_active(self, *, active: bool) -> None:
        """Set the brightness activation flag."""
        self.brightness_active = active

    # --- per-light commanding -------------------------------------------

    def compute_commands(self, entity_id: str, current_state: State) -> dict[str, int]:
        """Return the attributes to be commanded to the light."""
        if entity_id in self.ignored:
            return {}

        return self._color_temp_commands(
            entity_id, current_state
        ) | self._brightness_commands(entity_id, current_state)

    def record_command(
        self,
        entity_id: str,
        commands: dict[str, int],
        current_state: State,
    ) -> None:
        """Record the commanded attributes for a light."""
        tracked = self.tracked.get(entity_id)
        source = tracked or _tracked_factory(current_state)

        self.tracked[entity_id] = LightTrack(
            brightness=commands.get(ATTR_BRIGHTNESS, source.brightness),
            color_temp_kelvin=commands.get(
                ATTR_COLOR_TEMP_KELVIN, source.color_temp_kelvin
            ),
        )

    def light_off(self, entity_id: str) -> None:
        """Forget the tracked state and empty override after a light went off."""
        self.tracked.pop(entity_id, None)

    def forget_unless_on(self, on_entity_ids: Iterable[str]) -> None:
        """Drop the tracking of every light that is no longer on."""
        on = set(on_entity_ids)
        for entity_id in list(self.tracked):
            if entity_id not in on:
                self.light_off(entity_id)

    # --- ignored entities -------------------------------------------------

    def dont_touch(self, entity_ids: Iterable[str]) -> None:
        """Stop touching the given entities."""
        self.ignored.update(entity_ids)

    def handle_again(self, entity_ids: Iterable[str]) -> list[str]:
        """Resume handling the given entities.

        Returns the entity ids that were not ignored before, so the
        caller can log them as unknown.
        """
        entity_ids = list(entity_ids)
        known = [entity_id for entity_id in entity_ids if entity_id in self.ignored]
        for entity_id in known:
            self.ignored.remove(entity_id)
        return sorted(set(entity_ids) - set(known))

    # --- internal helpers -------------------------------------------------

    def _color_temp_commands(
        self,
        entity_id: str,
        current_state: State,
    ) -> dict[str, int]:
        tracked = self.tracked.get(entity_id)
        known_color_temp_kelvin = (
            tracked.color_temp_kelvin if tracked is not None else None
        )
        current_color_temp_kelvin = current_state.attributes.get(ATTR_COLOR_TEMP_KELVIN)

        light_was_on_before = tracked is not None
        somebody_changed_color_temp = _mired_of_kelvin(
            known_color_temp_kelvin
        ) != _mired_of_kelvin(current_color_temp_kelvin)
        light_is_not_color_temp_light = (
            ColorMode.COLOR_TEMP
            not in current_state.attributes.get(ATTR_SUPPORTED_COLOR_MODES, [])
        )

        if light_is_not_color_temp_light:
            return {}

        if somebody_changed_color_temp and light_was_on_before:
            return {}

        color_temp = self._color_temp_in_limits(current_state)

        if not self.redshift_active or _mired_of_kelvin(color_temp) == _mired_of_kelvin(
            current_color_temp_kelvin
        ):
            return {}

        return {ATTR_COLOR_TEMP_KELVIN: color_temp}

    def _color_temp_in_limits(self, current_state: State) -> int:
        min_color_temp_kelvin = current_state.attributes[ATTR_MIN_COLOR_TEMP_KELVIN]
        max_color_temp_kelvin = current_state.attributes[ATTR_MAX_COLOR_TEMP_KELVIN]
        target = self.target_color_temp()
        return min(max_color_temp_kelvin, max(min_color_temp_kelvin, target))

    def _brightness_commands(
        self,
        entity_id: str,
        current_state: State,
    ) -> dict[str, int]:
        tracked = self.tracked.get(entity_id)
        known_brightness = tracked.brightness if tracked is not None else None
        current_brightness = current_state.attributes.get(ATTR_BRIGHTNESS)

        light_was_on_before = tracked is not None
        somebody_changed_brightness = known_brightness != current_brightness
        light_is_not_dimmable = COLOR_MODES_BRIGHTNESS.isdisjoint(
            current_state.attributes.get(ATTR_SUPPORTED_COLOR_MODES, [])
        )

        if light_is_not_dimmable:
            return {}

        if somebody_changed_brightness and light_was_on_before:
            return {}

        if not self.brightness_active:
            return {}

        brightness = self.target_brightness()

        if brightness is None or brightness == current_brightness:
            return {}

        return {ATTR_BRIGHTNESS: brightness}


def _tracked_factory(current_state: State) -> LightTrack:
    """Build the tracked facts for a light known only from its state."""
    return LightTrack(
        brightness=current_state.attributes.get(ATTR_BRIGHTNESS),
        color_temp_kelvin=current_state.attributes.get(ATTR_COLOR_TEMP_KELVIN),
    )


def _mired_of_kelvin(kelvin: int | None) -> int | None:
    if kelvin is None:
        return None
    return int(1e6 / kelvin)
