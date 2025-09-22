from collections import deque
import threading
import time
import s7util as u
import snap7.util as su
import numpy as np
from utils import statepoint as sp

def calculate_t2(t0,pull_speed_queue,index):
    start_index=index
    t=t0
    for i in range(start_index,len(pull_speed_queue)-1):
        v1=pull_speed_queue[i]
        v2=pull_speed_queue[i+1]
        dt=0.5
        s=(v1+v2)*dt*0.5
        t+=dt
        if s>12.0:
            t3=t
            break
    return t3

def calculate_t0(cut_signal_ts:float,length:float,pull_speed_queue:deque[float]):
    """根据给定切割信号时间、定尺、拉速list,计算t0的timestamp
    """
    total=28.0+length#钢坯走过的距离
    time_interval=0.5
    S=0.0
    t=cut_signal_ts
    t0=0
    index=0
    for i in range(len(pull_speed_queue)-1,0,-1):#倒序遍历队列
        v1=pull_speed_queue[i-1]
        v2=pull_speed_queue[i]
        dt=time_interval
        ds=dt*0.5*(v1+v2)
        S+=ds
        t-=dt#切割时间减去一个个time_interval，得到
        if S>total:
            t0=t
            index=i
            break
    return t0,index
class DataHandler:
    def __init__(self,stream_count=8):
        self.stream_count=stream_count
        #为每个流创建一个拉速队列
        self.pull_speed_queue=[deque(maxlen=2000) for _ in range(self.stream_count)]
        #为每个流存储当前定尺值
        self.current_lengths=[0.0]*self.stream_count
        #为每个流存储上一次的切割信号状态
        self.last_cut_signals = [False]*self.stream_count
        # 线程控制事件
        self.stop_event = threading.Event()
        self.data_thread = None

        #连接三个PLC
        self.client1=u.S7Client()
        self.client2=u.S7Client()
        self.client3=u.S7Client()
    
    def conn(self):
        self.client1.connect("172.16.1.20",0,1)
        self.client2.connect("192.168.1.215",0,1)
        self.client3.connect("172.16.1.21",0,1)
    
    def start_data_acquisition(self):
        """启动数据采集线程"""
        self.stop_event.clear()
        self.data_thread = threading.Thread(target=self._data_acquisition_loop, daemon=True)
        self.data_thread.start()
   
    def stop_data_acquisition(self):
        """停止数据采集线程"""
        self.stop_event.set()
        if self.data_thread:
            self.data_thread.join(timeout=5)
   
    def _data_acquisition_loop(self):
        """数据采集线程的主循环"""
        while not self.stop_event.is_set():
            try:
                # 1. 从PLC读取所有流的数据
                cut_signal_byte_array = self.client2.read_multi_dbs(
                    [131, 132, 133, 134, 135, 136, 137, 138],
                    [4, 4, 4, 4, 4, 4, 4, 4],
                    [1, 1, 1, 1, 1, 1, 1, 1]
                )
                pull_speed_byte_array = self.client1.read_multi_dbs(
                    [6, 6, 6, 6, 6, 6, 6, 6],
                    [36, 40, 44, 48, 52, 56, 60, 64],
                    [4, 4, 4, 4, 4, 4, 4, 4]
                )
                length_byte_array = self.client1.read_multi_dbs(
                    [6, 6, 6, 6, 6, 6, 6, 6],
                    [72, 76, 80, 84, 88, 92, 96, 100],
                    [4, 4, 4, 4, 4, 4, 4, 4]
                )

                # 2. 处理数据：将字节数组转换为实际值
                current_cut_signals = []#当前切割信号
                current_pull_speeds = []#当前拉速
                current_lengths = []#当前长度

                for bytes in cut_signal_byte_array:
                    current_cut_signals.append(su.get_bool(bytes, 0, 0))
                for bytes in pull_speed_byte_array:
                    current_pull_speeds.append(su.get_real(bytes, 0))
                for bytes in length_byte_array:
                    current_lengths.append(su.get_real(bytes, 0))
                #3.遍历8个流
                for i in range(self.stream_count):
                    #对应流的拉速队列中加入相应的拉速
                    self.pull_speed_queue[i].append(current_pull_speeds[i])
                    #存储对应流的定尺
                    self.current_lengths[i] = current_lengths

                    #切割信号出现上升沿
                    if current_cut_signals[i] and not self.last_cut_signals[i]:
                        if len(self.pull_speed_queue)>=800:#总共采样1000余次
                            cut_signal_time=time.time()
                            #根据切割信号时间、当前定尺、拉速队列、计算t0
                            t0,index=calculate_t0(cut_signal_time,self.current_lengths[i],self.pull_speed_queue[i])
                            print(f"{i}流计算得到时间戳：{t0}")
                            t2=calculate_t2(t0,self.pull_speed_queue[i],index)
                            delta_t=t2-t0

                    self.last_cut_signals[i]=current_cut_signals[i]
                time.sleep(0.5) 

            except Exception as e:
                print(e)
            




        



           







