from collections import deque
import datetime
import queue
import time
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
            pass
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
        
        # 在时间范围 [t0, t2] 内均匀取 5 个时间点


        t0=self.calc.calc_t0(cutting_time,length,pull_speed,v_t_func)
        t2=self.calc.calc_t2(t0,pull_speed,length,v_t_func)
       
        sampled_times = np.linspace(t0, t2, 5)
        # 对每个时间点调用拟合函数 v_t_func，计算对应的拉速
        sampled_speeds = [v_t_func(t) for t in sampled_times]
        # 打印采样结果（时间和对应的拉速）
        self.logger.debug(f"拉速拟合采样: times={sampled_times}, speeds={sampled_speeds}")

        avg_pull_speed=(length+12.0)/(t2-t0)
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











