from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY, YEARLY
from astral import LocationInfo
from astral.sun import sun
import pytz
import calendar
from skyfield import api
from skyfield import almanac
import ssl
import certifi
import os

class RecurringSunEventGenerator:
    """_summary_
        根据重复规则生成日历信息，可以存储到手机，提前提醒。
        
        
    """
    def __init__(self, start_year, end_year, timezone='Pacific/Auckland'):
        self.start_year = start_year
        self.end_year = end_year
        self.timezone = pytz.timezone(timezone)
        self.lat = -36.8485  # Auckland latitude
        self.lon = 174.7633  # Auckland longitude
        self.events = []
        
        # Load skyfield essentials
        self.ts = api.load.timescale()
        file_path = os.path.join(os.path.dirname(__file__), 'de421.bsp')
        self.eph = api.load(file_path)
        #self.eph = api.load('de421.bsp')
        self.location = api.Topos(latitude_degrees=self.lat, longitude_degrees=self.lon)

    def _get_sun_times(self, dt):
        """返回包含时间差的双格式数据"""
        days = 1
        next_day = dt + relativedelta(days=days)
        
        # 月末处理逻辑
        if next_day.month != dt.month:
            next_day = next_day.replace(day=1) + relativedelta(days=days-1)
        
        # 获取太阳时间数据 - 使用 skyfield 替代 astral
        current_day_times = self._calculate_sun_times(dt)
        next_day_times = self._calculate_sun_times(next_day)
        
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
        
        sunrise_time = current_day_times["sunrise"]
        next_sunrise_time = next_day_times["sunrise"]
        
        return {
            "sunrise": format_time(sunrise_time),
            "noon": format_time(current_day_times["noon"]),
            "sunset": format_time(current_day_times["sunset"]),
            "next_sunrise": format_time(next_sunrise_time),
            "sunrise_diff": format_diff(sunrise_time, next_sunrise_time)
        }

        
    def _calculate_sun_times(self, dt):
        """使用skyfield计算日出、正午和日落时间"""
        # 转换为UTC日期，午夜开始
        midnight = datetime(dt.year, dt.month, dt.day, tzinfo=pytz.UTC)
        t0 = self.ts.from_datetime(midnight)
        t1 = self.ts.from_datetime(midnight + timedelta(days=1))
        
        # 寻找日出日落事件
        earth = self.eph['earth']
        sun = self.eph['sun']
        
        f = almanac.sunrise_sunset(self.eph, self.location)
        times, events = almanac.find_discrete(t0, t1, f)
        
        # 初始化结果
        result = {"sunrise": None, "sunset": None, "noon": None}
        
        # 解析日出日落时间
        for time, is_sunrise in zip(times, events):
            # 将Skyfield时间转换为datetime对象
            dt_local = time.astimezone(self.timezone)
            
            if is_sunrise:
                result["sunrise"] = dt_local
            else:
                result["sunset"] = dt_local
        
        # 计算太阳正午时间（最高点）
        t0_time = t0.utc_datetime()
        t1_time = t1.utc_datetime()
        
        # 以15分钟为间隔搜索太阳高度
        highest_altitude = -90
        noon_time = None
        
        current_time = t0_time
        while current_time < t1_time:
            t = self.ts.from_datetime(current_time)
            
            # 计算太阳高度
            astrometric = (earth + self.location).at(t).observe(sun)
            apparent = astrometric.apparent()
            alt, az, distance = apparent.altaz()
            
            if alt.degrees > highest_altitude:
                highest_altitude = alt.degrees
                noon_time = current_time
            
            current_time += timedelta(minutes=15)
        
        # 精确化搜索，1分钟为间隔在最高点附近搜索
        if noon_time:
            refined_start = noon_time - timedelta(minutes=30)
            refined_end = noon_time + timedelta(minutes=30)
            
            current_time = refined_start
            while current_time < refined_end:
                t = self.ts.from_datetime(current_time)
                
                astrometric = (earth + self.location).at(t).observe(sun)
                apparent = astrometric.apparent()
                alt, az, distance = apparent.altaz()
                
                if alt.degrees > highest_altitude:
                    highest_altitude = alt.degrees
                    noon_time = current_time
                
                current_time += timedelta(minutes=1)
            
            # 转换为本地时间
            if noon_time:
                t_noon = self.ts.from_datetime(noon_time)
                # 调用datetime()将Time对象转换为标准datetime对象
                result["noon"] = t_noon.astimezone(self.timezone)
        
        return result
            
    def _add_event(self, dt: datetime):
        sun_times = self._get_sun_times(dt)
        e = Event()
        e.name = "太阳时间提醒"
        e.begin = dt
        e.end = sun_times['next_sunrise']['date_time']
        e.description = (
            f"日出: {sun_times['sunrise']['str']}\n"
            f"日中: {sun_times['noon']['str']}\n"
            f"日落: {sun_times['sunset']['str']}\n"
            f"明日日出: {sun_times['next_sunrise']['str']}\n"
            f"总时长: {sun_times['sunrise_diff']['str']}\n"
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
