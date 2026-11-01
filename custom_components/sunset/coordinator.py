"""HASS glue for the Sunset integration.

The coordinator owns everything that touches ``hass``: the transition
schedule, the light state listener, and applying the controller's
decisions. All decisions live in ``SunsetController``; this module only
translates them into service calls and entity updates.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

import homeassistant.core as HA
import homeassistant.helpers.event as EV
import homeassistant.util.dt as dt_util
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_ON
from homeassistant.helpers import service as service_helper

from .calculator import DaytimeCalculator, RedshiftCalculator
from .const import (
    CONF_BED_TIME,
    CONF_BRIGHTNESS_ENABLED,
    CONF_DAY_COLOR_TEMP,
    CONF_EVENING_TIME,
    CONF_MORNING_TIME,
    CONF_NIGHT_COLOR_TEMP,
    CONF_NIGHT_TIME,
    DOMAIN,
    INTERPOLATION_INTERVAL,
    SERVICES,
    normalize_config,
)
from .controller import SunsetController
from .services import async_register_services

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.config_entries import ConfigEntry

    from .entity import SunsetEntity

_LOGGER = logging.getLogger("sunset")

_MAX_TRACKED_CONTEXTS = 64


def _noop() -> None:
    """Do nothing."""


@dataclass(slots=True)
class SunsetRuntimeData:
    """Runtime data for the Sunset config entry."""

    coordinator: SunsetDataCoordinator


class SunsetDataCoordinator:
    """Scheduling, light tracking, and applying Sunset's decisions."""

    def __init__(self, hass: HA.HomeAssistant, entry: ConfigEntry) -> None:
        """Prepare the coordinator from the config entry without touching hass."""
        config = normalize_config({**entry.data, **entry.options})

        self.hass = hass
        self.entry = entry
        self.controller = SunsetController(
            config=config,
            redshift_calculator=RedshiftCalculator(
                config[CONF_EVENING_TIME],
                config[CONF_NIGHT_TIME],
                config[CONF_MORNING_TIME],
                config[CONF_DAY_COLOR_TEMP],
                config[CONF_NIGHT_COLOR_TEMP],
            ),
            brightness_calculator=(
                DaytimeCalculator(
                    config[CONF_BED_TIME],
                    config[CONF_MORNING_TIME],
                )
                if config[CONF_BRIGHTNESS_ENABLED]
                else None
            ),
        )

        self._evening_time = dt.time.fromisoformat(config[CONF_EVENING_TIME])
        self._night_time = dt.time.fromisoformat(config[CONF_NIGHT_TIME])
        self._morning_time = dt.time.fromisoformat(config[CONF_MORNING_TIME])
        bed_time = config[CONF_BED_TIME]
        self._bed_time = None if bed_time is None else dt.time.fromisoformat(bed_time)

        self._entities: list[SunsetEntity] = []
        self._own_context_ids: deque[str] = deque(maxlen=_MAX_TRACKED_CONTEXTS)
        self._unsub_schedule: EV.CALLBACK_TYPE = _noop
        self._unsub_state_changes: EV.CALLBACK_TYPE = _noop

    async def async_setup(self) -> None:
        """Register services, listeners and schedule, and derive the state."""
        async_register_services(self.hass, self)

        self._unsub_state_changes = EV.async_track_state_change_filtered(
            self.hass,
            EV.TrackStates(all_states=False, entities=set(), domains={"light"}),
            self._light_state_changed,
        ).async_remove
        self.entry.async_on_unload(self._unload)

        await self.async_apply()
        self._schedule_next()

    def _unload(self) -> None:
        self._unsub_state_changes()
        self._unsub_state_changes = _noop
        self._unsub_schedule()
        self._unsub_schedule = _noop
        for service in SERVICES:
            self.hass.services.async_remove(DOMAIN, service)

    def track_entities(self, entities: Iterable[SunsetEntity]) -> None:
        """Remember entity instances so target changes can be pushed to them."""
        self._entities.extend(entities)

    # --- scheduling ------------------------------------------------------

    def _schedule_next(self) -> None:
        self._unsub_schedule()
        now = dt_util.now()
        self._unsub_schedule = EV.async_track_point_in_time(
            self.hass,
            self._scheduled_event,
            self._next_event(now),
        )

    async def _scheduled_event(self, _: dt.datetime | None) -> None:
        await self.async_apply()
        self._schedule_next()

    def _next_event(self, now: dt.datetime) -> dt.datetime:
        candidates = [
            self._next_occurrence(self._evening_time, now),
            self._next_occurrence(self._night_time, now),
            self._next_occurrence(self._morning_time, now),
        ]
        if self._bed_time is not None:
            candidates.append(self._next_occurrence(self._bed_time, now))
        if self._is_interpolating():
            candidates.append(now + INTERPOLATION_INTERVAL)
        return min(candidates)

    def _is_interpolating(self) -> bool:
        return (
            not self.controller.redshift_calculator.is_day()
            and not self.controller.redshift_calculator.is_night()
        )

    @staticmethod
    def _next_occurrence(time: dt.time, now: dt.datetime) -> dt.datetime:
        candidate = dt.datetime.combine(now.date(), time, tzinfo=now.tzinfo)
        if candidate <= now:
            candidate += dt.timedelta(days=1)
        return candidate

    # --- light state tracking --------------------------------------------

    async def _light_state_changed(
        self,
        event: HA.Event[HA.EventStateChangedData],
    ) -> None:
        entity_id = event.data["entity_id"]
        new_state = event.data.get("new_state")

        if new_state is None or new_state.state != STATE_ON:
            self.controller.light_off(entity_id)
            return

        if event.context.id in self._own_context_ids:
            return

        await self.async_apply()

    # --- applying decisions ----------------------------------------------

    async def async_apply(self) -> None:
        """Apply the current decision cycle."""
        self._notify_entities()

        current_states = self._fetch_light_states()
        self.controller.forget_unless_on(current_states)

        await asyncio.gather(
            *(
                self._async_apply_light(entity_id, current_state)
                for entity_id, current_state in current_states.items()
            ),
            return_exceptions=True,
        )

    async def _async_apply_light(
        self,
        entity_id: str,
        current_state: HA.State,
    ) -> None:
        commands = self.controller.compute_commands(entity_id, current_state)
        if not commands:
            return

        self.controller.record_command(entity_id, commands, current_state)

        context = HA.Context()
        self._own_context_ids.append(context.id)

        current_attrs = current_state.attributes
        call_attrs = {
            key: current_attrs[key]
            for key in [ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN]
            if key in current_attrs
        }
        call_attrs[ATTR_ENTITY_ID] = entity_id
        call_attrs.update(commands)

        try:
            await self.hass.services.async_call(
                "light",
                SERVICE_TURN_ON,
                call_attrs,
                blocking=True,
                context=context,
            )
        except HA.HomeAssistantError:
            self.controller.light_off(entity_id)
            _LOGGER.warning("Could not update light %s", entity_id, exc_info=True)

    def _fetch_light_states(self) -> dict[str, HA.State]:
        states: dict[str, HA.State] = {}
        for light in self.hass.states.async_entity_ids("light"):
            state = self.hass.states.get(light)
            if state is not None and state.state == STATE_ON:
                states[light] = state
        return states

    def _notify_entities(self) -> None:
        for entity in self._entities:
            entity.async_write_state_if_changed()

    # --- service handlers -------------------------------------------------

    async def async_activate_redshift(self) -> None:
        """Reactivate automatic redshifting and apply immediately."""
        self.controller.activate_redshift()
        await self.async_apply()

    async def async_deactivate_redshift(self) -> None:
        """Deactivate automatic redshifting."""
        self.controller.deactivate_redshift(color_temp=None)
        self.controller.set_redshift_active(active=False)
        self._notify_entities()

    async def async_activate_brightness(self) -> None:
        """Reactivate automatic brightness handling and apply immediately."""
        self.controller.activate_brightness()
        await self.async_apply()

    async def async_deactivate_brightness(self) -> None:
        """Deactivate automatic brightness handling."""
        self.controller.deactivate_brightness(brightness=None)
        self.controller.set_brightness_active(active=False)
        self._notify_entities()

    async def handle_activate_redshift(self, _: HA.ServiceCall) -> None:
        """Reactivate automatic redshifting and apply immediately."""
        await self.async_activate_redshift()

    async def handle_deactivate_redshift(self, call: HA.ServiceCall) -> None:
        """Deactivate automatic redshifting, optionally at a manual value."""
        if self.controller.deactivate_redshift(call.data.get("color_temp")):
            await self.async_apply()
        self.controller.set_redshift_active(active=False)
        self._notify_entities()

    async def handle_activate_brightness(self, _: HA.ServiceCall) -> None:
        """Reactivate automatic brightness handling and apply immediately."""
        await self.async_activate_brightness()

    async def handle_deactivate_brightness(self, call: HA.ServiceCall) -> None:
        """Deactivate automatic brightness handling, optionally at a manual value."""
        if self.controller.deactivate_brightness(call.data.get("brightness")):
            await self.async_apply()
        self.controller.set_brightness_active(active=False)
        self._notify_entities()

    async def handle_dont_touch(self, call: HA.ServiceCall) -> None:
        """Ignore the given entities from now on."""
        self.controller.dont_touch(await self._target_entity_ids(call))

    async def handle_handle_again(self, call: HA.ServiceCall) -> None:
        """Resume handling the given entities and warn on unknown ones."""
        unknown = self.controller.handle_again(await self._target_entity_ids(call))
        for entity_id in unknown:
            _LOGGER.warning("Unknown entity_id: %s", entity_id)

    async def _target_entity_ids(self, call: HA.ServiceCall) -> list[str]:
        """Resolve entity, device and area targets to light entity ids."""
        extracted = await service_helper.async_extract_entity_ids(call)

        raw_entity_ids = call.data.get(ATTR_ENTITY_ID, [])
        if isinstance(raw_entity_ids, str):
            raw_entity_ids = [raw_entity_ids]

        lights = {
            entity_id for entity_id in extracted if entity_id.startswith("light.")
        }
        return sorted(lights | set(raw_entity_ids))
