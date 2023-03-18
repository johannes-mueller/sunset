

import datetime as DT


class DaytimeCalculator:

    def __init__(self, night_time: str, morning_time: str):
        self._night_time: DT.time = DT.time.fromisoformat(night_time)
        self._morning_time = DT.time.fromisoformat(morning_time)

    def is_night(self) -> bool:
        return DT.datetime.now() > self._night_start()

    def _night_start(self) -> DT.datetime:
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


class RedshiftCalculator(DaytimeCalculator):

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

    def is_day(self):
        return DT.datetime.now() < self._evening_start()

    def color_temp(self) -> int:
        if self.is_night():
            return self._night_color_temp

        if self.is_day():
            return self._day_color_temp

        return self._interpolated_color_temp()

    def _interpolated_color_temp(self) -> int:
        evening_time_span = (self._night_start() - self._evening_start()).seconds
        time_into_evening = (DT.datetime.now() - self._evening_start()).seconds

        color_range = self._night_color_temp - self._day_color_temp

        color = self._day_color_temp + color_range / evening_time_span * time_into_evening
        return round(color)

    def _evening_start(self):
        return self._time_corrected(self._evening_time)
