[![pytest](https://github.com/johannes-mueller/sunset/actions/workflows/pytest.yml/badge.svg)](https://github.com/johannes-mueller/sunset/actions/workflows/pytest.yml)

# Sunset

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

    * `day_color_temp`: the color temperature at daytime in Kelvin
    * `night_color_temp`: the color temperature at nighttime in Kelvin

Besides the color temperature Sunset can also manipulate the brightness of
the lights.  In contrast to the color temperature it does not shift the
brightness continuously but drops the brightness of all lights at a given
time.  This is meant to be a soft reminder that it is time for you to go to
bed.

    * `bed_time`: The time when the brightness should be dropped or 'null' to
    disable brightness manipulation.
    * `night_brightness`: The brightness after bed time (default 127)


### Color temperature translation behavior

The component takes over the color temperature of all the lights available in
the system.  Between `morning_time` and `evening_time` the color temperature
will be set to the level of `day_color_temp`.  Once `evening_time` is reached
the color temperature will slowly transition to `night_color_temp`.  The
`night_color_temp` value will be reached exactly at `night_time` and maintained
during the night.  Once `morning_time` is reached the color temperature will
instantaneously go back to `day_color_temp`.


### Manually overriding the color temperature and the brightness

You can manually override the color temperature and the brightness for a
certain light or group of lights just by adjusting it in a usual way, e.g. the
web interface.  The color temperature of this light will then not be changed as
long as the light remains switched on.  Once the light goes off and on again,
its color temperature and the brightness will be again governed by Sunset.


### Forbidding Sunset to touch a specific light

There are the services `sunset.dont_touch` and `sunset.handle_again`. They both
take a `device_id` an `area_id` or an `entity_id` as parameter.  As you would
guess from the names `sunset.dont_touch` makes Sunset not manipulate a certain
light, whereas `sunset.handle_again` makes Sunset control the light again.

Lights have to be specified as lists of entities, an area or a device.

Be aware that the lights not to be touched are not persistent.  They are
forgotten as soon as the component is restarted.  So it is just meant as a
temporary measure.


### Activating and deactivating

You can use the services `sunset.activate_redshift` and
`sunset.deactivate_redshift` to activate and deactivate the redshift
altogether.  The `sunset.deactivate_redshift` service takes an optional
`color_temp` parameter to apply a certain color temperature to all lights.  If
it is not given the color temperature is not changed on deactivation.

Similarly you can use the services `sunset.activate_brightness` and
`sunset.deactivate_brightness` to deactivate the dimming.

### Planned features

* Shift the color temperature back in the morning over a defined time.  As of now
  the back shift to day temperature happens instantaneously.

* Configure lights that are generally ignored by Sunset.

No ETAs given.


## Status

Hacked it like a couple of months ago and deployed it on my system.  So far it seems to
work fine.


## Installation

For now you need to clone the repo and copy or symlink the directory
`custom_components/sunset` to your `.homeassistant/custom_components`.  When
restarting Sunset should automatically step in.


## Support

As always, bug reports and pull requests welcome.
