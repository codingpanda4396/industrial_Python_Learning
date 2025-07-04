# -*- coding:utf-8 -*-

import re
from datetime import datetime, timezone, timedelta

def to_timestamp(dt_str, tz_str):
    #字符串转datetime
    dt=datetime.strptime(dt_str,'%Y-%m-%d %H:%M:%S')
    #时区转换
    tz_str=tz_str.strip('UTC').strip(':00')
    tz=timezone(timedelta(hours=int(tz_str)))
    #根据指定的时区，转换成
    timestamp=dt.replace(tzinfo=tz).timestamp()
    return timestamp



# 测试:
t1 = to_timestamp('2015-6-1 08:10:30', 'UTC+7:00')
assert t1 == 1433121030.0, t1

t2 = to_timestamp('2015-5-31 16:10:30', 'UTC-09:00')
assert t2 == 1433121030.0, t2

print('ok')
