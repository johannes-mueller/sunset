"""Config and options flows for the Sunset integration."""

from __future__ import annotations

from typing import Any

import probatio
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BED_TIME,
    CONF_BRIGHTNESS_ENABLED,
    CONF_DAY_COLOR_TEMP,
    CONF_EVENING_TIME,
    CONF_EXCLUDED_ENTITIES,
    CONF_MORNING_TIME,
    CONF_NIGHT_BRIGHTNESS,
    CONF_NIGHT_COLOR_TEMP,
    CONF_NIGHT_TIME,
    DEFAULT_OPTIONS,
    DOMAIN,
    normalize_config,
)

_COLOR_TEMP_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=2000,
        max=6500,
        step=100,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="K",
    )
)

_BRIGHTNESS_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=255,
        step=1,
        mode=selector.NumberSelectorMode.BOX,
    )
)


def _schema(current: dict[str, Any]) -> probatio.Schema:
    """Build the settings schema."""
    return probatio.Schema(
        {
            probatio.Optional(
                CONF_EVENING_TIME,
                default=current[CONF_EVENING_TIME],
            ): selector.TimeSelector(),
            probatio.Optional(
                CONF_NIGHT_TIME,
                default=current[CONF_NIGHT_TIME],
            ): selector.TimeSelector(),
            probatio.Optional(
                CONF_BED_TIME,
                default=current[CONF_BED_TIME] or DEFAULT_OPTIONS[CONF_BED_TIME],
            ): selector.TimeSelector(),
            probatio.Optional(
                CONF_MORNING_TIME,
                default=current[CONF_MORNING_TIME],
            ): selector.TimeSelector(),
            probatio.Optional(
                CONF_DAY_COLOR_TEMP,
                default=current[CONF_DAY_COLOR_TEMP],
            ): _COLOR_TEMP_SELECTOR,
            probatio.Optional(
                CONF_NIGHT_COLOR_TEMP,
                default=current[CONF_NIGHT_COLOR_TEMP],
            ): _COLOR_TEMP_SELECTOR,
            probatio.Optional(
                CONF_NIGHT_BRIGHTNESS,
                default=current[CONF_NIGHT_BRIGHTNESS],
            ): _BRIGHTNESS_SELECTOR,
            probatio.Optional(
                CONF_BRIGHTNESS_ENABLED,
                default=current[CONF_BRIGHTNESS_ENABLED],
            ): selector.BooleanSelector(),
            probatio.Optional(
                CONF_EXCLUDED_ENTITIES,
                default=current[CONF_EXCLUDED_ENTITIES],
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
        }
    )


class SunsetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Sunset config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup flow."""
        if user_input is not None:
            return self.async_create_entry(
                title="Sunset",
                data=normalize_config(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(DEFAULT_OPTIONS),
        )

    async def async_step_import(
        self, import_config: dict[str, Any]
    ) -> ConfigFlowResult:
        """Import an existing YAML configuration."""
        try:
            data = normalize_config(import_config)
        except TypeError, ValueError:
            return self.async_abort(reason="invalid_config")

        return self.async_create_entry(title="Sunset", data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SunsetOptionsFlow:
        """Return the options flow."""
        del config_entry
        return SunsetOptionsFlow()


class SunsetOptionsFlow(OptionsFlowWithReload):
    """Handle Sunset options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options form."""
        current = {
            **DEFAULT_OPTIONS,
            **self.config_entry.data,
            **self.config_entry.options,
        }
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=normalize_config({**current, **user_input}),
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current),
        )
