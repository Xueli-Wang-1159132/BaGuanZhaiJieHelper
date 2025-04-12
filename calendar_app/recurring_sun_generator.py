from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY, YEARLY
from astral import LocationInfo
from astral.sun import sun
import pytz
import calendar


class RecurringSunEventGenerator:
    """_summary_
        根据重复规则生成日历信息，可以存储到手机，提前提醒。
        
        
    """
    def __init__(self, start_year, end_year, timezone='Pacific/Auckland'):
        self.start_year = start_year
        self.end_year = end_year
        self.timezone = pytz.timezone(timezone)
        self.location = LocationInfo("Auckland", "NZ", timezone, -36.8485, 174.7633)
        self.events = []

    def _get_sun_times(self, dt):
        days = 1
        next_day = dt +  relativedelta(days=days)
        if next_day.month != dt.month:
            return next_day.replace(day=1) + relativedelta(days=days-1)
        s = sun(self.location.observer, date=dt.date(), tzinfo=self.timezone)
        s2 = sun(self.location.observer, date=next_day.date(), tzinfo=self.timezone)
        return {
            "sunrise": s["sunrise"].strftime('%H:%M'),
            "noon": s["noon"].strftime('%H:%M'),
            "sunset": s["sunset"].strftime('%H:%M'),
            "next_sunrise":s2["sunrise"].strftime('%H:%M')
        }

    def _add_event(self, dt: datetime):
        sun_times = self._get_sun_times(dt)
        e = Event()
        e.name = "太阳时间提醒"
        e.begin = dt
        e.duration = timedelta(hours=24)
        e.description = (
            f"日出: {sun_times['sunrise']}\n"
            f"日中: {sun_times['noon']}\n"
            f"日落: {sun_times['sunset']}\n"
            f"明日日出: {sun_times['next_sunrise']}\n"
        )

        # 添加提前一天的三次提醒（24, 12, 1 小时前）
        for hours_before in [24, 12, 1]:
            alarm = DisplayAlarm(trigger=timedelta(hours=-hours_before))
            e.alarms.append(alarm)

        self.events.append(e)

    def generate_by_monthly_day(self, day=1, months=range(1, 13)):
        for year in range(self.start_year, self.end_year + 1):
            for month in months:
                odt = datetime(year, month, day)
                sun_times = self._get_sun_times(odt)['sunrise']
                hours, minutes = map(int, sun_times.split(':'))
                
                try:
                    dt = datetime(year, month, day, hours, minutes)  # 默认上午 9 点事件
                    dt = self.timezone.localize(dt)
                    self._add_event(dt)
                except ValueError:
                    continue  # 忽略不存在的日期，比如 2月30日

    def generate_by_quarter(self, which='first'):
        month_day_map = {
            'first': (1, 1),  # 每季度第一个月第一天
            'last': (3, 31)   # 每季度最后一个月最后一天（简单处理）
        }
        for year in range(self.start_year, self.end_year + 1):
            for quarter_start_month in [1, 4, 7, 10]:
                month, day = month_day_map.get(which, (1, 1))
                month += quarter_start_month - 1
                try:
                    dt = datetime(year, month, day, 9, 0)
                    dt = self.timezone.localize(dt)
                    self._add_event(dt)
                except ValueError:
                    continue

    def generate_by_weekday_rule(self, month, weekday, which='last'):
        for year in range(self.start_year, self.end_year + 1):
            cal = calendar.monthcalendar(year, month)
            if which == 'last':
                for week in reversed(cal):
                    if week[weekday] != 0:
                        day = week[weekday]
                        break
            elif which == 'first':
                for week in cal:
                    if week[weekday] != 0:
                        day = week[weekday]
                        break
            else:
                raise ValueError("only 'first' or 'last' are supported")

            dt = datetime(year, month, day, 9, 0)
            dt = self.timezone.localize(dt)
            self._add_event(dt)

    def save_to_ics(self, filename):
        cal = Calendar(events=self.events)
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize_iter())
