"""Test the Sunset config and options flows."""

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunset.const import DEFAULT_OPTIONS, DOMAIN


async def test_user_flow(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=DEFAULT_OPTIONS,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data == DEFAULT_OPTIONS


async def test_user_flow_single_instance(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_import_flow(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={"night_brightness": 100},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data["night_brightness"] == 100


async def test_import_flow_invalid_config(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={"evening_time": "not-a-time"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_config"


async def test_import_flow_single_instance(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**DEFAULT_OPTIONS, "night_brightness": 100},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["night_brightness"] == 100
