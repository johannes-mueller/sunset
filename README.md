[![pytest](https://github.com/johannes-mueller/sunset/actions/workflows/pytest.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/pytest.yml)
[![HACS Action](https://github.com/johannes-mueller/sunset/actions/workflows/hacs.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/johannes-mueller/sunset/actions/workflows/hassfest.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/hassfest.yml)

# Sunset

Get yourself accustomed to the evening for better sleep.

## Features

- Gradually shifts the colour temperature of your lights towards a warmer
  level during the evening.
- Optionally lowers the brightness at a configured bed time as a soft
  reminder to go to sleep.
- Configured entirely through the Home Assistant UI and stored in a config
  entry.
- Keeps manual changes you make to a light until you switch it off and on
  again.
- Persistent and temporary exclusions for lights Sunset should leave alone.
- Switches and sensors expose the current state and targets to dashboards and
  automations.

## How it works

Sunset runs on a daily schedule:

| Window | Colour temperature |
| --- | --- |
| `morning_time` → `evening_time` | `day_color_temp` |
| `evening_time` → `night_time` | Linear transition from `day_color_temp` to `night_color_temp` |
| `night_time` → `morning_time` (across midnight) | `night_color_temp` |

During the evening transition the target is refreshed about once a minute and
only written to a light when the value actually changes. Outside the
transition, lights are updated at the configured transition times and when a
light is switched on or changed.

Brightness works on a separate window: from `bed_time` until `morning_time`
the target is `night_brightness`, otherwise it is the maximum safe brightness
(254). Disable **Dim lights at bed time** to leave brightness untouched.

Lights that do not support colour temperature or dimming are skipped for that
dimension. A light that is off is ignored until it is switched on again.

## Installation

### HACS

Sunset is currently available as a HACS custom repository. Default HACS
inclusion is planned.

1. Make sure [HACS](https://hacs.xyz) is installed.
2. Add `https://github.com/johannes-mueller/sunset` as a custom repository of
   type **Integration**.
3. Install **Sunset** from HACS.
4. Restart Home Assistant.
5. Add **Sunset** from **Settings > Devices & services > Add integration**.

### Manual installation

Copy or symlink `custom_components/sunset` into your `.homeassistant/custom_components`
directory and restart Home Assistant.

## Configuration

1. Open **Settings > Devices & services > Add integration**.
2. Search for **Sunset** and add it.
3. Configure the schedule and brightness settings.
4. Use **Configure** on the Sunset integration card to change settings later.

| Option | Default | Meaning |
| --- | --- | --- |
| Evening time | `17:00` | When the colour temperature starts shifting towards the night value. |
| Night time | `23:00` | When the night colour temperature is reached. |
| Bed time | `00:00` | When brightness is lowered. Leave empty to keep brightness unchanged. |
| Morning time | `06:00` | When the colour temperature returns to the daytime value. |
| Day colour temperature | `6250` K | Colour temperature during the day. |
| Night colour temperature | `2500` K | Colour temperature during the night. |
| Night brightness | `127` | Brightness applied after bed time, from 0 to 255. |
| Dim lights at bed time | on | Disable to leave the brightness of your lights unchanged. |
| Lights Sunset should not control | none | Persistent list of lights that Sunset should ignore. |

Times may cross midnight; for example a bed time of `00:00` and a morning time
of `06:00` dim the lights just after midnight until the morning.

## Entities

Sunset creates one device with four entities:

| Entity | Meaning |
| --- | --- |
| `switch.sunset_redshift_active` | Whether automatic colour temperature handling is active. |
| `switch.sunset_brightness_active` | Whether automatic brightness handling is active. |
| `sensor.sunset_colour_temperature` | The colour temperature Sunset currently targets, in Kelvin. |
| `sensor.sunset_brightness` | The brightness Sunset currently targets, from 0 to 255. Unknown while brightness handling is disabled. |

The switches are the primary controls. Use them in dashboards and automations
to pause Sunset for the evening or to resume it.

## Actions

The six services remain available as compatibility aliases for the switches
and the temporary exclusions. They are not deprecated, but new automations can
use the switches directly.

| Action | Equivalent to |
| --- | --- |
| `sunset.activate_redshift` | Turning `switch.sunset_redshift_active` on. |
| `sunset.deactivate_redshift` | Turning `switch.sunset_redshift_active` off; optionally sets all lights to `color_temp`. |
| `sunset.activate_brightness` | Turning `switch.sunset_brightness_active` on. |
| `sunset.deactivate_brightness` | Turning `switch.sunset_brightness_active` off; optionally sets all lights to `brightness`. |
| `sunset.dont_touch` | Temporarily exclude the targeted lights. |
| `sunset.handle_again` | Hand the targeted lights back to Sunset. |

Targets accept entities, devices, areas, and lists of those, and are resolved
to light entities only. `dont_touch` and `handle_again` also accept `all` and
`none`.

```yaml
actions:
  # Pause colour temperature handling for the evening.
  - action: switch.turn_off
    target:
      entity_id: switch.sunset_redshift_active

  # Deactivate colour temperature handling and set all lights to 2700 K.
  - action: sunset.deactivate_redshift
    data:
      color_temp: 2700

  # Do not touch the lights in an area until further notice.
  - action: sunset.dont_touch
    target:
      area_id: living_room

  # Hand a device's lights back to Sunset.
  - action: sunset.handle_again
    target:
      device_id: 0f5d4e125f42235e2a3646ee4e3a2ee6
```

Invalid data is rejected: colour temperatures outside 2000–6500 K, brightness
values outside 0–255, missing targets, and malformed entity ids are reported
as invalid service calls.

### Triggers and conditions

Sunset provides no triggers and no conditions. Use the entities and actions
above from your own automations.

## Manual overrides

If you change the colour temperature or brightness of a light yourself, Sunset
leaves that value alone while the light stays on. Switching the light off and
on again clears the override and Sunset resumes control. The same applies to
lights that stop reporting the attribute: Sunset skips that dimension instead
of fighting the device.

## Excluding lights

The **Lights Sunset should not control** option is persistent and survives
restarts. The `sunset.dont_touch` action is a temporary alternative; the
exclusion is forgotten when Home Assistant restarts. `sunset.handle_again`
removes either kind.

## Known limitations

- The maximum brightness Sunset commands is **254**, not 255. Some bulbs
  misbehaved when given 255 directly; the likely cause is the Zigbee
  `MoveToLevel` level range, which ends at 254.
- The morning return to the daytime colour temperature is instantaneous.
  Gradual morning transitions are a planned feature.
- During the evening transition the target is refreshed about once a minute,
  so colour changes are gradual rather than continuous.
- When a light rejects an update, the failure is logged with the entity id and
  Sunset tries again on the next cycle.
- Sunset only controls colour temperature and brightness. It does not change
  colour modes, effects, or other light attributes.

## Troubleshooting

- **A light is not changing.** Check that it advertises `color_temp` or
  `brightness` support, that it is not excluded in the integration options or
  by `sunset.dont_touch`, and that you have not changed it manually since it
  was last switched on. Switching it off and on again clears a manual
  override.
- **The brightness sensor is unknown.** Brightness handling is disabled (no
  bed time or **Dim lights at bed time** turned off).
- **A service call fails validation.** Check the allowed ranges and use real
  entity, device, or area ids. Error details appear in the Home Assistant log
  and in the automation trace.
- **A light cannot be updated.** Look for `Could not update light` in the
  Home Assistant log; the message contains the entity id. Verify that the
  light is available and accepts colour temperature and brightness.
- **Nothing happens at all.** Check the two switch entities and reload the
  integration from **Settings > Devices & services**.

## Migrating from YAML

If `configuration.yaml` still contains a `sunset:` block, Sunset imports those
settings into a config entry on the first start. Verify the imported settings
in the UI, then remove the YAML block and restart Home Assistant. Further YAML
configuration is ignored while a UI entry exists.

## Upgrading from 0.1.0

Version 0.2.0 replaces the synthetic `sunset.*` states with real entities.
Automations that referenced the old states must be updated:

| Old state | New entity |
| --- | --- |
| `sunset.redshift_active` | `switch.sunset_redshift_active` |
| `sunset.brightness_active` | `switch.sunset_brightness_active` |
| `sunset.color_temp_kelvin` | `sensor.sunset_colour_temperature` |
| `sunset.brightness` | `sensor.sunset_brightness` |

The switch states are `on`/`off` instead of `True`/`False`. The six services
keep their names and fields.

## Requirements and compatibility

Sunset requires Home Assistant **2026.4.0** or newer. The declared minimum is
reviewed at every minor release and only raised deliberately, with the change
announced in the changelog. HACS will not offer an update on an older Home
Assistant; install the previous Sunset release from the HACS version selector
in that case.

## Removal

Remove the integration from **Settings > Devices & services**, then remove the
custom repository from HACS if you no longer need it. If you migrated from
YAML, make sure the old `sunset:` block is not left in `configuration.yaml`.

## Support

Bug reports and pull requests are welcome at
<https://github.com/johannes-mueller/sunset/issues>. Please include your Home
Assistant version and any relevant log lines.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, the
test-driven development workflow, the 100% branch coverage requirement, and the
release checklist.

## License

Sunset is licensed under the Apache License 2.0. See [LICENSE.txt](LICENSE.txt).
