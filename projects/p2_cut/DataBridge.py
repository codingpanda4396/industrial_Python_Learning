from collections import deque
import datetime
import logging
import queue
import time

from scipy import integrate, interpolate
from utils.StatePoint import BufferPoint,Statepoint
from utils.Calculator import Calculator
from utils.s7util import Logger
import numpy as np
import Persistence 

class DataBridge:
    def __init__(self, pull_speed_buffer,length_buffer,cutting_sig_buffer,water_discharge_buffer,overall_temperature,pressure,billet_temperature,water_temperature_diff):
        """获取数据点，并把数据点列表转换为单个数据点"""
        #拉速point list
        self.pull_speed_buffer=pull_speed_buffer
        #流量point list
        self.water_discharge_buffer=water_discharge_buffer
        #切割信号point list
        self.cutting_sig_buffer=cutting_sig_buffer
        #定尺
        self.length_buffer=length_buffer
        #总管温度
        self.ot=overall_temperature
        #总管压力
        self.p=pressure
        #钢温
        self.bt=billet_temperature
        #结晶器水温差
        self.wtd=water_temperature_diff

        self.logger=Logger(__name__)
        self.logger.screen_on()
        #任务队列
        self.task_queue=queue.Queue()
        self.flow_list=self._generate_each_flow()
        
        self.calc=Calculator()
        self.persistence=Persistence.Persistence()

    def _generate_each_flow(self)-> list:
        """生成8个单独持有本流数据的对象
        """
        flow_list=[]
        for i in range(8):
            pull_speed=self.pull_speed_buffer[i]
            cutting_sig=self.cutting_sig_buffer[i]
            length=self.length_buffer[i]
            water_discharge_list=self.water_discharge_buffer[i]
            flow_list.append(SingleFlowData(i+1,pull_speed,length,cutting_sig,water_discharge_list,self.task_queue))
        return flow_list
    
    def data_storage(self):
        try:

            task_tuple=self.task_queue.get(True,1)
            flow_no=task_tuple[0]
            cutting_time=task_tuple[1]
            t0=task_tuple[2]
            t2=task_tuple[3]
            total_flow=task_tuple[4]
            avg_pull_speed=task_tuple[5]

            other_data_tuple=self.calc.calc_other_data(t0,t2,self.ot,self.p,self.bt,self.wtd)
            water_temperature = other_data_tuple[0]
            water_pressure=other_data_tuple[1]
            water_pressure_sd=other_data_tuple[2]
            stell_temp=other_data_tuple[3]
            water_temperature_diff=other_data_tuple[4]

            
            self.persistence.save_flow_event(flow_no,cutting_time,t0,t2,water_temperature,water_pressure,total_flow,water_pressure_sd,stell_temp,avg_pull_speed,water_temperature_diff)
        except Exception as e:
            self.logger.debug(e.with_traceback())
class SingleFlowData:
    """代表一个流的相关数据
    """
    def __init__(self,flow_no:int,pull_speed:BufferPoint,length:Statepoint,cutting_sig:Statepoint,water_discharge_list:list[BufferPoint],task_queue:queue.Queue):
        self.pull_speed=pull_speed
        self.length=length
        self.cutting_sig=cutting_sig
        self.water_discharge=water_discharge_list
        self.task_queue:queue.Queue=task_queue

        self.flow_no=flow_no#流号
        #初始化日志系统
        self.logger=Logger(__name__)
        self.logger.screen_on()
        self.logger.file_on("DataBridge.log")
        #设置切割信号数据点的激活动作
        self.cutting_sig.set_excite_action(self.cutting_action)
        #计算工具类
        self.calc=Calculator()

    def cutting_action(self):
        cutting_time=datetime.datetime.now().timestamp()
        length=self.length.data/1000 #得到定尺（mm->m）

        self.logger.debug(f"{self.flow_no}流开始切割")
        time.sleep(30)
        pull_speed:deque=self.pull_speed.get_buffer()#获得(拉速，时间)队列
        flow_buffer_list:list[deque]=[self.water_discharge[i].get_buffer() for i in range(5)]
        if len(pull_speed)<10:
            self.logger.debug(f"{self.flow_no}流已统计数据量不足，无法计算")
            return
        
        v_t_func=self.calc.make_v_t_func(pull_speed)


        t0=self.calc.calc_t0(cutting_time,length,pull_speed,v_t_func)
        
        if t0 == None:
            self.logger.debug(f"{self.flow_no}流已统计数据量不足，无法计算")
            return

        t2=self.calc.calc_t2(t0,pull_speed,length,v_t_func)

        avg_pull_speed=(length+12.0)/(t2-t0) *60
        total_flow=self.calc.calc_total_flow(t0,t2,flow_buffer_list)
        self.create_data(cutting_time,t0,t2,total_flow,avg_pull_speed)
    
    def create_data(self,cutting_time, entry_time, exit_time, water_total, dspeed_avg):
        self.logger.debug(f"{self.flow_no}流钢坯计算结果：")
        self.logger.debug(f'\t切割时间：{datetime.datetime.fromtimestamp(cutting_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t进入时间：{datetime.datetime.fromtimestamp(entry_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t离开时间：{datetime.datetime.fromtimestamp(exit_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t水量总计：{water_total}')
        self.logger.debug(f'\t平均拉速：{dspeed_avg}')
        self.task_queue.put((self.flow_no,float(cutting_time), float(entry_time), float(exit_time), float(water_total), float(dspeed_avg)))



class billet_data_gatherer:
    """钢坯数据采集者"""
    def __init__(self, dspeed_point: BufferPoint, cutting_sig_point: Statepoint, sizing_point: Statepoint, flow_rate_point_list: list[BufferPoint],
                 logger: logging.Logger, strand_no: int, result_queue: queue.Queue):
        self.dspeed_point = dspeed_point
        self.cutting_sig_point = cutting_sig_point
        self.sizing_point = sizing_point
        self.flow_rate_point_list = flow_rate_point_list
        self.logger = logger
        self.strand_no = strand_no
        self.result_queue = result_queue

        self.MOLD_TO_CUTTER_DISTANCE = 28
        self.CRITICAL_ZONE_LENGTH = 12

        self.cutting_sig_point.set_excite_action(self.cutting_action)
        self.logger.debug("状态点active动作设置完毕")
        
    def cutting_action(self):
        cutting_time = datetime.datetime.now().timestamp()
        sizing = self.sizing_point.data / 1000 #mm转换为m

        self.logger.debug(f"{self.strand_no}流开始切割")

        time.sleep(30)#确保数据采集完整
        dspeed_buffer: deque = self.dspeed_point.get_buffer()#获得拉速队列
        flow_rate_buffer_list: list[deque] = [self.flow_rate_point_list[i].get_buffer() for i in range(5)]

        if len(dspeed_buffer) < 10:
            self.logger.debug(f"{self.strand_no}流已统计数据量不足，无法计算")
            self.logger.debug(f"队列：{len(dspeed_buffer)}")
            return

        data_tuple, time_tuple = zip(*dspeed_buffer)

        x = np.array(time_tuple) #时间数组
        y = np.array(data_tuple) / 60 #拉速转换为m/s
        vt_func = interpolate.interp1d(x, y, kind='cubic')#三次样条插值
        entry_time = self._binary_search_start(vt_func, cutting_time, sizing + self.MOLD_TO_CUTTER_DISTANCE)#头部进入结晶器

        if entry_time == None:
            self.logger.debug(f"{self.strand_no}流已统计数据量不足，无法计算")
            return
        
        exit_time = self._binary_search_end(vt_func, entry_time, sizing + self.CRITICAL_ZONE_LENGTH)#尾部离开关键区域
        dspeed_avg = (sizing + self.CRITICAL_ZONE_LENGTH) / (exit_time - entry_time) * 60

        self.create_data(cutting_time, entry_time, exit_time, self.flow_rate_total(flow_rate_buffer_list, entry_time, exit_time), dspeed_avg)
        
    def _binary_search_start(self, func, upper_limit, target):
        """二分查找计算钢坯进入关键区域时间
        func：速度-时间插值函数
        upper_limit：切割时间戳（搜索范围上限）

        """
        left = func.x.min()
        right = func.x.max()
        
        if self._get_distance(func, left, upper_limit) < target:
            self.logger.debug(f"left:{left} distance:{self._get_distance(func,left,upper_limit)}")
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
    
                                #五段流量队列
    def flow_rate_total(self, deque_list: list[deque], start_time, end_time):
        res = []
        for dequei in deque_list:
            data_tuple, time_tuple = zip(*dequei)
            x = np.array(time_tuple)
            y = np.array(data_tuple) / 3600
            if len(x) < 4:
                avg = np.mean(y)
                vt_func = lambda xx: avg
            else:
                vt_func = interpolate.interp1d(x, y, kind='cubic')
            total = integrate.quad(vt_func, start_time, end_time)[0]
            res.append(total)

        return sum(res)
    
    def create_data(self, cutting_time, entry_time, exit_time, water_total, dspeed_avg):
        self.logger.debug(f"{self.strand_no}流钢坯计算结果：")
        self.logger.debug(f'\t切割时间：{datetime.datetime.fromtimestamp(cutting_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t进入时间：{datetime.datetime.fromtimestamp(entry_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t离开时间：{datetime.datetime.fromtimestamp(exit_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t水量总计：{water_total}')
        self.logger.debug(f'\t平均拉速：{dspeed_avg}')
        self.result_queue.put((self.strand_no, float(cutting_time), float(entry_time), float(exit_time), float(water_total), float(dspeed_avg)))








