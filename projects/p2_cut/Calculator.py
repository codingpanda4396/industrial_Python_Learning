from collections import deque
from scipy.interpolate import CubicSpline
import numpy as np
from utils import s7util as su
from scipy.integrate import quad

class Calculator:
    def __init__(self):
        self.logger =su.Logger(__name__)
        self.logger.screen_on()
        self.logger.file_on()
    def _make_v_t_func(self,pull_speed_queue:deque):
        speed_time_list=list(pull_speed_queue)
        if len(speed_time_list)<4:
            raise ValueError("数据过少无法插值")
        speeds, times = zip(*speed_time_list)
        t_arr = np.array(times)
        v_arr = np.array(speeds) / 60.0
        return CubicSpline(t_arr, v_arr, bc_type='natural'), t_arr   
    def calc_t0(self, cut_signal_ts:float, length:float, pull_speed_queue:deque):
        total = 28.0 + length * 0.001
        t1 = cut_signal_ts
        #得到vt函数和时间数组
        v_tfunc, time_array = self._make_v_t_func(pull_speed_queue)

        def cal_len(t0):
            return quad(v_tfunc, t0, t1)[0]

        t_low = float(time_array[0])
        t_high = float(t1)
        if t_low >= t_high:
            return t_low

        # 二分查找
        tol = 1e-6
        while abs(t_high - t_low) > tol:
            t_mid = (t_low + t_high) / 2
            cur_len = cal_len(t_mid)
            if cur_len > total:
                t_low = t_mid
            else:
                t_high = t_mid
        t0 = (t_low + t_high) / 2
        return t0 
        
    def calc_t2(self, t0:float, pull_speed_queue:deque, length:float):
        v_tfunc, time_array = self._make_v_tfunc(pull_speed_queue)
        def distance_func(t):
            return quad(v_tfunc, t0, t)[0]
        t_low = float(t0)
        t_high = float(time_array[-1])
        if t_low >= t_high:
            return t_high
        tol = 1e-6
        target = 12.0 + length * 0.001
        while abs(t_high - t_low) > tol:
            t_mid = (t_low + t_high) / 2
            cur = distance_func(t_mid)
            if cur < target:
                t_low = t_mid
            else:
                t_high = t_mid
        return (t_low + t_high) / 2

    def calc_total_water_and_avg_params(self, start_time:float, end_time:float, stream_queue:deque, other_queue:deque):
        # 计算总水量
        time_list = []
        flow_list = []
        for stream_values in stream_queue:
            # stream_values 是 [{'segment':i,'value':(flow,ts)}, ...]
            if not stream_values:
                continue
            flow_rate = sum(s.get('value')[0] for s in stream_values)
            ts = stream_values[0].get('value')[1]
            time_list.append(ts)
            flow_list.append(flow_rate)
        if len(time_list) < 2:
            self.logger.warning('流队列数据不足，无法计算水量')
            total_water = 0.0
            avg_flow_rate = 0.0
        else:
            x = np.array(time_list)
            y = np.array(flow_list) / 3600.0  # 转为 m^3/s
            flow_t_func = CubicSpline(x, y)
            total_water = quad(flow_t_func, start_time, end_time)[0]
            # 平均流速（m^3/s）
            avg_flow_rate = total_water / (end_time - start_time) if end_time > start_time else 0.0

        # 计算6个参数平均值
        param_names = [
            '结晶器流量', '结晶器水温差', '二冷水总管压力',
            '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        ]
        valid = [d for d in other_queue if start_time <= d.get('timestamp', 0) <= end_time]
        if not valid:
            self.logger.warning('在时间范围内没有参数数据')
            avg_params = {name:0.0 for name in param_names}
        else:
            sums = {name:0.0 for name in param_names}
            for d in valid:
                for name in param_names:
                    sums[name] += d.get(name, 0.0)
            avg_params = {name: sums[name]/len(valid) for name in param_names}

        return total_water, avg_params, avg_flow_rate