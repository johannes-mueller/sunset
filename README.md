[![pytest](https://github.com/johannes-mueller/redshift/actions/workflows/pytest.yml/badge.svg)](https://github.com/johannes-mueller/redshift/actions/workflows/pytest.yml)

# Redshift

Get yourself accustomed to the evening for better sleep.


## Synopsis

During sunset the sunlight turns more and more reddish.  The reddish light will
make our body produce hormones that promote sleep.  That's why in offices there
are usually very hot, i.e. white lights.  At home in the evening a more reddish
light would be more appropriate.  This extension for
[Homeassistant](https://home-assistant.io) takes care of that.


## Features

You can configure three times in your `configuration.yaml`.

* `evening_time`: the time when the redshift will start
* `night_time`: the time when the redshift has reached the final color
  temperature.
* `morning_time`: the time when the color temperature will get back to the
  day time level.

* `day_color_temp`: the color temperature at daytime
* `night_color_temp`: the color temperature at nighttime


### Color temperature translation behavior

The component take over the color temperature of all the lights available in
the system.  Between `morning_time` and `evening_time` the color temperature
will be set to the level of `day_color_temp`.  Once `evening_time` is reached
the color temperature will slowly transition to `night_color_temp`.  The
`night_color_temp` value will be reached exactly at `night_time` and maintained
during the night.  Once `morning_time` is reached the color temperature will
instantaneously go back to `day_color_temp`.


### Manually overriding the color temperature

You can manually override the color temperature for a certain light or group of
lights just by adjusting it in a usual way, e.g. the web interface.  The color
temperature of this light will then not be changed as long as the light remains
switched on.  Once the light goes off and on again, its color temperature will
be again governed by the redshift.


## Planned features

* Light dimming: automatically dim all the lights by a certain amount at a
  certain evening time to signal "now its time for bed".



## Installation

For now you need to clone the repo and copy or symlink the directory
`custom_components/redshift` to your `.homeassistant/custom_components`.  When
restarting the redshift should automatically step in.


## Support

As always, bug reports and pull requests welcome.
