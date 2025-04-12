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
        self.location = LocationInfo("Auckland", "NZ", timezone, -36.8440526109716, 174.7675260738167)
        self.events = []

    def _get_sun_times(self, dt):
        """返回包含时间差的双格式数据"""
        days = 1
        next_day = dt + relativedelta(days=days)
        
        # 月末处理逻辑
        if next_day.month != dt.month:
            next_day = next_day.replace(day=1) + relativedelta(days=days-1)
        
        # 获取太阳时间数据
        s = sun(self.location.observer, date=dt.date(), tzinfo=self.timezone)
        s2 = sun(self.location.observer, date=next_day.date(), tzinfo=self.timezone)
        
        def format_diff(start, end):
            """时间差格式化函数"""
            try:
                delta = end - start
                if delta.total_seconds() < 0:
                    raise ValueError("次日日出时间早于当日")
                    
                total_seconds = delta.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                
                return {
                    "str": f"{hours:02d}:{minutes:02d}",
                    "hours": hours,
                    "minutes": minutes,
                    "total_minutes": hours * 60 + minutes
                }
            except TypeError:
                return {
                    "str": "N/A",
                    "hours": 0,
                    "minutes": 0,
                    "total_minutes": 0
                }
        
        def format_time(t):
            return {
                "str": t.strftime('%H:%M'),
                "hour": t.hour,
                "minute": t.minute,
                "total_minutes": t.hour * 60 + t.minute,
                "date_time": t
            }
        
        sunrise_time = s["sunrise"]
        next_sunrise_time = s2["sunrise"]
        
        return {
            "sunrise": format_time(sunrise_time),
            "noon": format_time(s["noon"]),
            "sunset": format_time(s["sunset"]),
            "next_sunrise": format_time(next_sunrise_time),
            "sunrise_diff": format_diff(sunrise_time, next_sunrise_time)
        }
    
    def _add_event(self, dt: datetime):
        sun_times = self._get_sun_times(dt)
        e = Event()
        e.name = "太阳时间提醒"
        e.begin = sun_times['sunrise']['date_time']
        e.end = sun_times['next_sunrise']['date_time']
        e.description = (
            f"日出: {sun_times['sunrise']['str']}\n"
            f"日中: {sun_times['noon']['str']}\n"
            f"日落: {sun_times['sunset']['str']}\n"
            f"明日日出: {sun_times['next_sunrise']['str']}\n"
            f"总时长: {sun_times['sunrise_diff']['str']}\n"
            f"注：由于不同经纬度以及海拔会导致时间有略微差异\n"
            f"本次时间使用的是Auckland Britomart Train Station（36°84'40.4\"S 174°76'74.0\"E）的时间\n"
            f"后续版本会增加地理位置信息以及海拔高度来提供更加准确的时间\n"
        )

        # 添加提前一天的三次提醒（24, 12, 1 小时前）
        for hours_before in [24, 12, 1]:
            alarm = DisplayAlarm(trigger=timedelta(hours=-hours_before))
            e.alarms.append(alarm)

        self.events.append(e)

    def generate_by_monthly_day(self, day=1, months=range(1, 13)):
        """_summary_
        根据每月的几月几号创建事件

        Args:
            day (int, optional): 日期. Defaults to 1.
            months (_type_, optional): 月份. Defaults to range(1, 13).
        """
        for year in range(self.start_year, self.end_year + 1):
            for month in months:                
                try:
                    odt = self.timezone.localize(datetime(year, month, day))
                    sun_times = self._get_sun_times(odt)
                    sunrise = sun_times['sunrise']
                    dt = datetime(
                        year, month, day,
                        sunrise['hour'],
                        sunrise['minute']
                    ).astimezone(self.timezone)
                    self._add_event(dt)
                except ValueError:
                    continue  # 忽略不存在的日期，比如 2月30日

    def generate_by_quarter(self, which='first'):
        """根据季度生成日历

        Args:
            which (str, optional): 每个季度的哪一天. Defaults to 'first'.
        """
        month_day_map = {
            'first': (1, 1),  # 每季度第一个月第一天
            'last': (3, 31)   # 每季度最后一个月最后一天
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
        """根据周来生成

        Args:
            month (_type_): 月
            weekday (_type_): 星期几
            which (str, optional): 哪个星期. Defaults to 'last'.

        Raises:
            ValueError: 目前只支持第一个或最后一个
        """
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
