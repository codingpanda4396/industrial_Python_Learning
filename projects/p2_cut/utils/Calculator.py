from collections import deque
from scipy import interpolate
from scipy import integrate
from scipy.interpolate import CubicSpline
import numpy as np
from utils import s7util as su
from scipy.integrate import quad

class Calculator:
    def __init__(self):
        self.logger =su.Logger(__name__)
        self.logger.screen_on() 
        self.logger.file_on()

    def make_v_t_func(self, pull_speed_queue: deque):
    # 1. 数据预处理：过滤无效点
        speed_time_list = [
            (v, t) for v, t in pull_speed_queue 
            if v > 0  # 拉速必须为正
        ]
        if len(speed_time_list) < 4:
            raise ValueError("有效数据不足（需≥4个正拉速点）")
        
        # 2. 提取数据并转换单位（m/min -> m/s）
        speeds, times = zip(*speed_time_list)
        t_arr = np.array(times)
        v_arr = np.array(speeds) / 60.0
        
        # 3. 创建插值函数（自然边界条件）
        cs = CubicSpline(t_arr, v_arr, bc_type='natural')
        
        # 4. 包装为返回标量的安全函数
        def v_t_func(t):
            t_min, t_max = t_arr.min(), t_arr.max()
            if t < t_min or t > t_max:
                return 0.0  # 超出范围返回0（或抛异常）
            return float(cs(t))
        
        return v_t_func
    
    def calc_t0(self, cut_signal_ts:float, length:float, pull_speed_queue:deque,v_tfunc):
        total = 28.0 + length
        t1 = cut_signal_ts
        #得到时间数组
        _,time_array=zip(*pull_speed_queue)

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
        
    def calc_t2(self, t0:float, pull_speed_queue:deque, length:float,v_tfunc):
        _,time_array=zip(*pull_speed_queue)
        def distance_func(t):
            return quad(v_tfunc, t0, t)[0]
        t_low = float(t0)
        t_high = float(time_array[-1])
        if t_low >= t_high:
            return t_high
        tol = 1e-6
        target = 12.0 + length
        while abs(t_high - t_low) > tol:
            t_mid = (t_low + t_high) / 2
            cur = distance_func(t_mid)
            if cur < target:
                t_low = t_mid
            else:
                t_high = t_mid
        return (t_low + t_high) / 2

    def calc_total_flow(self,t0,t2,flow_buffer_list:list[deque]):
        res=[]
        for dequei in flow_buffer_list:
            data_tuple,time_tuple = zip(*dequei)
            x=np.array(time_tuple)
            y=np.array(data_tuple)/3600 #m³/s
            
            vt_func= CubicSpline(x,y)
            total=quad(vt_func,t0,t2)[0]
            res.append(total)
        return sum(res)

    def calc_other_data(self,entry_time,exit_time,ot,p,bt,wtd):

        wt = self.interval_avg(self.ot.get_buffer(), entry_time, exit_time)
        wp = self.interval_avg(self.p.get_buffer(), entry_time, exit_time)
        wps = self.interval_sd(self.p.get_buffer(), entry_time, exit_time)
        st = self.interval_avg(self.bt.get_buffer(), entry_time, exit_time)
        wtd = self.interval_avg(self.wtd.get_buffer(), entry_time, exit_time)

        return wt,wp,wps,st,wtd
    
    def interval_avg(self, buffer, left, right):
        data_tuple, time_tuple = zip(*buffer)
        x = np.array(time_tuple)
        y = np.array(data_tuple)
        func = interpolate.interp1d(x, y, kind = "cubic")
        inte = integrate.quad(func, left, right)[0]

        return inte / (right - left)
    
    def interval_sd(self, buffer, left, right):
        data_tuple, time_tuple = zip(*buffer)
        x = np.array(time_tuple)
        y = np.array(data_tuple)
        func = interpolate.interp1d(x, y, kind = "cubic")
        inte = integrate.quad(func, left, right)[0]
        avg = inte / (right - left)

        func2 = lambda x: (func(x) - avg) ** 2
        inte2 = integrate.quad(func2, left, right)[0]
        avg2 = inte2 / (right - left)

        return avg2 ** 0.5
    def _binary_search_start(self, func, upper_limit, target):
        """二分查找计算钢坯进入关键区域时间
        func：速度-时间插值函数
        upper_limit：切割时间戳（搜索范围上限）

        """
        left = func.x.min()
        right = func.x.max()

        if self._get_distance(func, left, upper_limit) < target:
            return

        while abs(right - left) > 0.01:
            mid = (left + right) / 2
            if self._get_distance(func, mid, upper_limit) >= target:
                left = mid
            else:
                right = mid
        
        return (left + right) / 2
    
    def _binary_search_end(self, func, lower_limit, target):
        left = func.x.min()
        right = func.x.max()

        while abs(right - left) > 0.01:
            mid = (left + right) / 2
            if self._get_distance(func, lower_limit, mid) >= target:
                right = mid
            else:
                left = mid
        
        return (left + right) / 2

    def _get_distance(self, vt_func, lower, upper):
        """通过积分计算移动距离"""
        return integrate.quad(vt_func, lower, upper)[0]