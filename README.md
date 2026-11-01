[![pytest](https://github.com/johannes-mueller/sunset/actions/workflows/pytest.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/pytest.yml)
[![HACS Action](https://github.com/johannes-mueller/sunset/actions/workflows/hacs.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/johannes-mueller/sunset/actions/workflows/hassfest.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/hassfest.yml)

# Sunset

Get yourself accustomed to the evening for better sleep.


## Synopsis

During sunset the sunlight turns more and more reddish.  The reddish light will
make our body produce hormones that promote sleep.  That's why in offices there
are usually very hot, i.e. white lights.  At home in the evening a more reddish
light would be more appropriate.  This integration for
[Home Assistant](https://home-assistant.io) takes care of that.


## Features

Sunset gradually shifts the colour temperature of your lights towards a warmer
level during the evening.  It can also lower the brightness at a configured
bed time as a soft reminder to go to sleep.

All settings are configured through the Home Assistant UI and stored in a
config entry.


## Configuration

1. Open **Settings > Devices & services > Add integration**.
2. Search for **Sunset** and add it.
3. Configure the schedule and brightness settings.
4. Use **Configure** on the Sunset integration card to change the settings
   later.

### Options

- **Evening time**: when the colour temperature starts shifting.
- **Night time**: when the night colour temperature is reached.
- **Morning time**: when the colour temperature returns to the daytime level.
- **Day colour temperature**: colour temperature during the day, in Kelvin.
- **Night colour temperature**: colour temperature during the night, in Kelvin.
- **Bed time**: when brightness is lowered.
- **Night brightness**: brightness after bed time.
- **Dim lights at bed time**: disable this to keep brightness unchanged.
- **Lights Sunset should not control**: persistent list of lights that Sunset
  should ignore.

### Migrating from YAML

If your `configuration.yaml` still contains a `sunset:` block, Sunset imports
those settings into a config entry on the first start.  Verify the imported
settings in the UI, then remove the YAML block and restart Home Assistant.

### Colour temperature behaviour

The integration takes over the colour temperature of the lights available in
the system.  Between `morning_time` and `evening_time` the colour temperature
is set to `day_color_temp`.  Once `evening_time` is reached it slowly
transitions to `night_color_temp`, which is reached at `night_time` and
maintained during the night.  At `morning_time` it returns to the daytime
level.

### Manually overriding the colour temperature and brightness

You can manually override the colour temperature or brightness of a light or
group of lights by adjusting it in the usual way, for example from the web
interface.  Sunset will not change that value as long as the light remains
switched on.  Once the light is switched off and on again, Sunset resumes
control.

### Excluding lights

The **Lights Sunset should not control** option is persistent and survives
restarts.

The services `sunset.dont_touch` and `sunset.handle_again` are temporary
alternatives.  They accept a `device_id`, an `area_id`, or an `entity_id`.
`sunset.dont_touch` stops Sunset from manipulating the given lights, while
`sunset.handle_again` hands them back to Sunset.

Temporary exclusions are forgotten when Home Assistant restarts.


## Services

### Activating and deactivating colour temperature handling

Use `sunset.activate_redshift` and `sunset.deactivate_redshift` to enable or
disable colour temperature handling.  `sunset.deactivate_redshift` optionally
takes a `color_temp` parameter in Kelvin to apply to all lights.  If it is not
given, the current colour temperature is left unchanged.

### Activating and deactivating brightness handling

Use `sunset.activate_brightness` and `sunset.deactivate_brightness` to enable
or disable brightness handling.  `sunset.deactivate_brightness` optionally
takes a `brightness` parameter to apply to all lights.


## Planned features

* Shift the colour temperature back in the morning over a defined time.  As of
  now the back shift to the day temperature happens instantaneously.

No ETAs given.


## Status

Sunset is usable, but it is still under active development.


## Installation

### HACS

Sunset is currently available as a HACS custom repository.

1. Make sure [HACS](https://hacs.xyz) is installed.
2. Add this repository as a custom repository of type **Integration**.
3. Install **Sunset** from HACS.
4. Restart Home Assistant.
5. Add **Sunset** from **Settings > Devices & services > Add integration**.

Existing `configuration.yaml` settings are imported automatically on the first
start.  After that, the integration is configured from the UI.

### Manual installation

Copy or symlink the directory `custom_components/sunset` into your
`.homeassistant/custom_components` directory, then restart Home Assistant.


## Removal

Remove the integration from **Settings > Devices & services**, then remove the
custom repository from HACS if you no longer need it.  If you migrated from
YAML, make sure the old `sunset:` block is not left in `configuration.yaml`.


## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, test-driven
development workflow, and the 100% branch coverage requirement.


## Support

As always, bug reports and pull requests are welcome.
