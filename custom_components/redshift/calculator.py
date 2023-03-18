

import datetime as DT


class _AbstractCalculator:

    def __init__(self, night_time: str, morning_time: str):
        self._night_time: DT.time = DT.time.fromisoformat(night_time)
        self._morning_time = DT.time.fromisoformat(morning_time)

    def _night(self) -> DT.datetime:
        return self._time_corrected(self._night_time)

    def _morning(self) -> DT.datetime:
        return self._today_time(self._morning_time)

    def _today_time(self, time: DT.time) -> DT.datetime:
        today = DT.datetime.today()
        return DT.datetime.combine(today, time)

    def _time_corrected(self, time: DT.time) -> DT.datetime:
        today_time = self._today_time(time)
        morning = self._morning()
        if today_time > morning and DT.datetime.now() < morning:
            return today_time - DT.timedelta(days=1)
        if today_time < morning and DT.datetime.now() > morning:
            return today_time + DT.timedelta(days=1)
        return today_time


class RedshiftCalculator(_AbstractCalculator):

    def __init__(
            self,
            evening_time: str = "17:00",
            night_time: str = "23:00",
            morning_time: str = "07:00",
            day_color_temp: int = 6250,
            night_color_temp: int = 2500
    ):
        self._day_color_temp: int = day_color_temp
        self._night_color_temp: int = night_color_temp

        self._evening_time: DT.time = DT.time.fromisoformat(evening_time)
        super().__init__(night_time, morning_time)

    def color_temp(self) -> int:
        now = DT.datetime.now()

        night = self._night()

        if now > night:
            return self._night_color_temp

        evening = self._evening()

        if now < evening:
            return self._day_color_temp

        evening_time_span = (night - evening).seconds
        elapsed_seconds = (now - evening).seconds

        color_range = self._night_color_temp - self._day_color_temp

        color = self._day_color_temp + color_range / evening_time_span * elapsed_seconds
        return round(color)

    def _evening(self):
        return self._time_corrected(self._evening_time)


class BrightnessCalculator(_AbstractCalculator):

    def is_night(self) -> bool:
        now = DT.datetime.now()

        night = self._night()

        return now > night
