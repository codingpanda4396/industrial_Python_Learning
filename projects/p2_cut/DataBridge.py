from collections import deque
import datetime
import time
from utils.StatePoint import BufferPoint,Statepoint
from utils.Calculator import Calculator
from utils.s7util import Logger
import numpy as np

class DataBridge:
    def __init__(self, pull_speed_buffer,length_buffer,cutting_sig_buffer,water_discharge_buffer):
        """获取数据点，并把数据点列表转换为单个数据点"""
        #拉速point list
        self.pull_speed_buffer=pull_speed_buffer
        #流量point list
        self.water_discharge_buffer=water_discharge_buffer
        #切割信号point list
        self.cutting_sig_buffer=cutting_sig_buffer
        #定尺
        self.length_buffer=length_buffer
        
        

    def generate_each_flow(self)-> list:
        """生成8个单独持有本流数据的对象
        """
        flow_list=[]
        for i in range(8):
            pull_speed=self.pull_speed_buffer[i]
            cutting_sig=self.cutting_sig_buffer[i]
            length=self.length_buffer[i]
            water_discharge_list=self.water_discharge_buffer[i]
            flow_list.append(SingleFlowData(i+1,pull_speed,length,cutting_sig,water_discharge_list))
        return flow_list


class SingleFlowData:
    """代表一个流的相关数据
    配套相关量的计算，计算方法直接返回结果
    """
    def __init__(self,flow_no:int,pull_speed:BufferPoint,length:Statepoint,cutting_sig:Statepoint,water_discharge_list:list[BufferPoint]):
        self.pull_speed=pull_speed
        self.length=length
        self.cutting_sig=cutting_sig
        self.water_discharge=water_discharge_list

        self.flow_no=flow_no#流号
        #初始化日志系统
        self.logger=Logger(__name__)
        self.logger.screen_on()
        self.logger.file_on("DataBridge.log")
        #设置切割信号数据点的激活动作
        self.cutting_sig.set_excite_action(self.cutting_action)

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
        
        vt_func=self.calc.make_v_t_func(pull_speed)









