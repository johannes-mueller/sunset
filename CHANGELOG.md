# Changelog

All notable changes to Sunset are documented here. The version in
`custom_components/sunset/manifest.json` and `pyproject.toml` is the single
source of truth for a release.

## 0.2.0 – 2026-11-02

This release replaces the legacy YAML prototype architecture with a
config-entry based integration built on real entities.

### Added

- Real entities: `switch.sunset_redshift_active`,
  `switch.sunset_brightness_active`,
  `sensor.sunset_colour_temperature`, and `sensor.sunset_brightness`, with a
  shared Sunset device.
- Diagnostics download for troubleshooting.
- Entity icons and translated entity names.
- Field descriptions in the configuration and options dialogs.
- Service schemas that reject invalid values and targets.
- A configurable minimum Home Assistant version in `hacs.json`.

### Changed

- Scheduling is event-driven: a timezone- and DST-aware transition chain
  replaces the one-second poll of all lights.
- Automatic updates run about once a minute during the evening transition and
  only when the target actually changes.
- Manual light changes are recognised through service contexts and skipped per
  dimension, and switching a light off and on again clears the override.
- Per-light failures and malformed light attributes are logged and cannot stop
  the rest of the update cycle.
- The colour temperature sensor no longer reports the temperature device class
  because it measures colour temperature, not ambient temperature.
- The minimum supported Home Assistant version is now **2026.4.0**.

### Breaking changes

- The synthetic `sunset.redshift_active`, `sunset.brightness_active`,
  `sunset.color_temp_kelvin`, and `sunset.brightness` states are gone.
  Automations must use the new entities:

  | Old state | New entity |
  | --- | --- |
  | `sunset.redshift_active` | `switch.sunset_redshift_active` |
  | `sunset.brightness_active` | `switch.sunset_brightness_active` |
  | `sunset.color_temp_kelvin` | `sensor.sunset_colour_temperature` |
  | `sunset.brightness` | `sensor.sunset_brightness` |

  Switch states are `on`/`off` instead of `True`/`False`.
- Invalid service data is now rejected instead of being ignored or warned
  about.

The six services keep their names and fields as compatibility aliases for the
new switches and temporary exclusions.

## 0.1.0 – 2026-10-31

- Initial HACS release: installable as a custom repository, config flow with
  YAML import, options flow, and HACS Action/Hassfest workflows.
