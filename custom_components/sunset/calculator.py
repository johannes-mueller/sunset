"""Time and colour-temperature calculations for Sunset.

The calculators are pure time maths against a single injected clock so
that they can be tested deterministically and are independent of the
Home Assistant event loop.

Window semantics (all boundaries are exclusive):

- from ``morning_time`` until ``evening_time`` it is day and the target
  colour temperature is the day colour temperature,
- from ``evening_time`` until ``night_time`` the target interpolates
  linearly from the day to the night colour temperature,
- from ``night_time`` until ``morning_time`` — wrapping midnight when
  ``night_time`` is later than ``morning_time`` — it is night,
- exactly at ``night_time``/``bed_time``/``morning_time`` the check
  compares with ``>``, so the previous window has just ended at that
  instant.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from homeassistant.util import dt as dt_util

Clock = Callable[[], dt.datetime]


class DaytimeCalculator:
    """Calculate whether a given moment is during the configured night.

    The night window starts at ``night_time`` and ends at
    ``morning_time``, wrapping midnight if ``night_time`` is later than
    ``morning_time``. The clock is injected; by default it is Home
    Assistant's timezone-aware ``dt_util.now()``.
    """

    def __init__(
        self,
        night_time: str,
        morning_time: str,
        now: Clock | None = None,
    ) -> None:
        """Initialise the calculator with night and morning times."""
        self._now: Clock = now if now is not None else dt_util.now
        self._night_time: dt.time = dt.time.fromisoformat(night_time)
        self._morning_time = dt.time.fromisoformat(morning_time)

    def is_night(self) -> bool:
        """Return whether the current time is within the night window."""
        return self._now() > self._night_start()

    def _night_start(self) -> dt.datetime:
        return self._time_corrected(self._night_time)

    def _morning(self) -> dt.datetime:
        return self._today_time(self._morning_time)

    def _today_time(self, time: dt.time) -> dt.datetime:
        now = self._now()
        naive_today_time = dt.datetime.combine(now.date(), time)
        if now.tzinfo is None:
            return naive_today_time
        return naive_today_time.replace(tzinfo=now.tzinfo)

    def _time_corrected(self, time: dt.time) -> dt.datetime:
        today_time = self._today_time(time)
        morning = self._morning()
        now = self._now()
        if today_time > morning and now < morning:
            return today_time - dt.timedelta(days=1)
        if today_time < morning and now > morning:
            return today_time + dt.timedelta(days=1)
        return today_time


class RedshiftCalculator(DaytimeCalculator):
    """Calculate the target colour temperature for a moment in time."""

    def __init__(  # noqa: PLR0913, PLR0917 (positional legacy signature kept for backwards compatibility)
        self,
        evening_time: str = "17:00",
        night_time: str = "23:00",
        morning_time: str = "07:00",
        day_color_temp: int = 6250,
        night_color_temp: int = 2500,
        now: Clock | None = None,
    ) -> None:
        """Initialise the calculator with the configured time window."""
        self._day_color_temp: int = day_color_temp
        self._night_color_temp: int = night_color_temp

        self._evening_time: dt.time = dt.time.fromisoformat(evening_time)
        super().__init__(night_time, morning_time, now)

    def is_day(self) -> bool:
        """Return whether the current time is before the evening window."""
        return self._now() < self._evening_start()

    def color_temp(self) -> int:
        """Return the target colour temperature in Kelvin."""
        if self.is_night():
            return self._night_color_temp

        if self.is_day():
            return self._day_color_temp

        return self._interpolated_color_temp()

    def _interpolated_color_temp(self) -> int:
        evening_time_span = (
            self._night_start() - self._evening_start()
        ).total_seconds()
        time_into_evening = (self._now() - self._evening_start()).total_seconds()

        color_range = self._night_color_temp - self._day_color_temp

        color = (
            self._day_color_temp + color_range / evening_time_span * time_into_evening
        )
        return round(color)

    def _evening_start(self) -> dt.datetime:
        return self._time_corrected(self._evening_time)
