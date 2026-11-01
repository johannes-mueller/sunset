"""HASS glue for the Sunset integration.

The coordinator owns everything that touches ``hass``: schedulers and
state fetching/appearing, applying the controller's decisions, and
writing the legacy synthetic states the behaviour tests rely on. All
decisions live in ``SunsetController``.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import homeassistant.core as HA
import homeassistant.helpers.event as EV
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.helpers import entity_registry

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
    SERVICES,
    normalize_config,
)
from .controller import SunsetController
from .services import async_register_services

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger("sunset")


@dataclass(slots=True)
class SunsetRuntimeData:
    """Runtime data for the Sunset config entry."""

    coordinator: SunsetDataCoordinator


class SunsetDataCoordinator:
    """Scheduling, state fetching, and applying Sunset's decisions."""

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

    def register(self) -> None:
        """Register services, initial states and the sampler, and unload hooks."""
        async_register_services(self.hass, self)

        self.controller.set_redshift_active(active=True)
        self.controller.set_brightness_active(active=True)
        self.hass.states.async_set(f"{DOMAIN}.redshift_active", str(True))
        self.hass.states.async_set(f"{DOMAIN}.brightness_active", str(True))
        self._write_sensor_states()

        timer_unsub = EV.async_track_time_interval(
            self.hass,
            self._timer_event,
            dt.timedelta(seconds=1),
            cancel_on_shutdown=True,
        )

        def unload() -> None:
            timer_unsub()
            for service in SERVICES:
                self.hass.services.async_remove(DOMAIN, service)
            for state in (
                "redshift_active",
                "brightness_active",
                "color_temp_kelvin",
                "brightness",
            ):
                self.hass.states.async_remove(f"{DOMAIN}.{state}")

        self.entry.async_on_unload(unload)

    # --- scheduling ------------------------------------------------------

    async def _timer_event(self, _: dt.datetime | None) -> None:
        await self.async_apply()

    async def async_apply(self) -> None:
        """Apply the current decision cycle."""
        self._write_sensor_states()

        current_states = self._fetch_light_states()
        self.controller.forget_unless_on(current_states)

        for entity_id, current_state in current_states.items():
            await self._maybe_apply(entity_id, current_state)

    # --- service handlers -------------------------------------------------

    async def handle_activate_redshift(self, _: HA.ServiceCall) -> None:
        """Reactivate automatic redshifting and apply immediately."""
        self.controller.activate_redshift()
        self.hass.states.async_set(f"{DOMAIN}.redshift_active", str(True))
        await self.async_apply()

    async def handle_deactivate_redshift(self, call: HA.ServiceCall) -> None:
        """Deactivate automatic redshifting."""
        if self.controller.deactivate_redshift(call.data.get("color_temp")):
            await self.async_apply()
        self.controller.set_redshift_active(active=False)
        self.hass.states.async_set(f"{DOMAIN}.redshift_active", str(False))

    async def handle_activate_brightness(self, _: HA.ServiceCall) -> None:
        """Reactivate automatic brightness handling and apply immediately."""
        self.controller.activate_brightness()
        self.hass.states.async_set(f"{DOMAIN}.brightness_active", str(True))
        await self.async_apply()

    async def handle_deactivate_brightness(self, call: HA.ServiceCall) -> None:
        """Deactivate automatic brightness handling."""
        if self.controller.deactivate_brightness(call.data.get("brightness")):
            await self.async_apply()
        self.controller.set_brightness_active(active=False)
        self.hass.states.async_set(f"{DOMAIN}.brightness_active", str(False))

    @HA.callback
    def handle_dont_touch(self, event: HA.ServiceCall) -> None:
        """Ignore the given entities from now on."""
        self.controller.dont_touch(self.entity_ids_from_event(event))

    @HA.callback
    def handle_handle_again(self, event: HA.ServiceCall) -> None:
        """Resume handling the given entities and warn on unknown ones."""
        unknown = self.controller.handle_again(self.entity_ids_from_event(event))
        for entity_id in unknown:
            _LOGGER.warning("Unknown entity_id: %s", entity_id)

    # --- helpers ----------------------------------------------------------

    def entity_ids_from_event(
        self,
        event: HA.ServiceCall,
    ) -> Generator[str]:
        """Expand entity, device and area ids of a service call."""
        entity_reg = entity_registry.async_get(self.hass)

        device_id = event.data.get(ATTR_DEVICE_ID)
        if device_id is not None:
            for entity_entry in entity_registry.async_entries_for_device(
                entity_reg,
                device_id,
            ):
                yield entity_entry.entity_id

        area_id = event.data.get(ATTR_AREA_ID)
        if area_id is not None:
            for entity_entry in entity_registry.async_entries_for_area(
                entity_reg,
                area_id,
            ):
                yield entity_entry.entity_id

        entity_ids = event.data.get(ATTR_ENTITY_ID, [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        yield from entity_ids

    def _fetch_light_states(self) -> dict[str, HA.State]:
        states: dict[str, HA.State] = {}
        for light in self.hass.states.async_entity_ids("light"):
            state = self.hass.states.get(light)
            if state is not None and state.state == STATE_ON:
                states[light] = state
        return states

    async def _maybe_apply(self, entity_id: str, current_state: HA.State) -> None:
        commands = self.controller.compute_commands(entity_id, current_state)
        if not commands:
            return

        self.controller.record_command(entity_id, commands, current_state)

        current_attrs = current_state.attributes
        call_attrs = {
            key: current_attrs[key]
            for key in [ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN]
            if key in current_attrs
        }
        call_attrs[ATTR_ENTITY_ID] = entity_id
        call_attrs.update(commands)
        await self.hass.services.async_call("light", SERVICE_TURN_ON, call_attrs)

    def _write_sensor_states(self) -> None:
        self.hass.states.async_set(
            f"{DOMAIN}.color_temp_kelvin", str(self.controller.target_color_temp())
        )
        brightness = self.controller.target_brightness()
        self.hass.states.async_set(
            f"{DOMAIN}.brightness",
            STATE_UNKNOWN if brightness is None else str(brightness),
        )
