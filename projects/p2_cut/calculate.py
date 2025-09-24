from collections import deque
import threading
import time
import s7util as u
import snap7.util as su
import numpy as np

class DataHandler:
    def __init__(self,stream_count=8):
        #流数           
        self.stream_count=stream_count
        #为每个流创建一个拉速队列
        self.pull_speed_queue=[deque(maxlen=2000) for _ in range(self.stream_count)]
        #为每个流存储当前定尺值
        self.current_lengths=[0.0]*self.stream_count
        #为每个流存储上一次的切割信号状态
        self.last_cut_signals = [False]*self.stream_count
        #为每个流创建一个水流量队列 
        self.stream_queue=[deque(maxlen=2000) for _ in range(self.stream_count)]
        #为每个流创建一个其他信息队列
        self.other_queue=deque(maxlen=2000)
        # 线程控制事件
        self.stop_event = threading.Event()
        self.data_thread = None

        self.logger=u.Logger(__name__)
        self.logger.file_on('res.txt')
        
        #用于连接三个PLC
        self.client1=u.S7Client()
        self.client2=u.S7Client()
        self.client3=u.S7Client()
    
    def conn(self):
        """连接三个PLC"""
        self.client1.connect("172.16.1.20",0,1)
        self.client2.connect("192.168.1.215",0,1)
        self.client3.connect("172.16.1.21",0,1)
    
    def start_data_acquisition(self):
        """启动数据采集线程"""
        self.stop_event.clear()#清除停止信号
        self.data_thread = threading.Thread(target=self._data_acquisition_loop, daemon=True)#
        self.data_thread.start()
        print("数据采集线程启动。。")
   
    def stop_data_acquisition(self):
        """停止数据采集线程"""
        self.stop_event.set()
        if self.data_thread:
            self.data_thread.join(timeout=5)
   
    def collect_data(self,current_cut_signals:list,current_pull_speeds:list,current_lengths:list,other_data:dict,stream_data:dict):
        """收集要处理的数据：切割信号、拉速队列、定尺、6个变量、水流量"""
        #8流切割信号
        cut_signal_byte_array = self.client2.read_multi_dbs(
                    [131, 132, 133, 134, 135, 136, 137, 138],
                    [4, 4, 4, 4, 4, 4, 4, 4],
                    [1, 1, 1, 1, 1, 1, 1, 1]
                )
        #8流的拉速
        pull_speed_byte_array = self.client1.read_multi_dbs(
                    [6, 6, 6, 6, 6, 6, 6, 6],
                    [36, 40, 44, 48, 52, 56, 60, 64],
                    [4, 4, 4, 4, 4, 4, 4, 4]
                )
        #8流的定尺
        length_byte_array = self.client1.read_multi_dbs(
                    [6, 6, 6, 6, 6, 6, 6, 6],
                    [72, 76, 80, 84, 88, 92, 96, 100],
                    [4, 4, 4, 4, 4, 4, 4, 4]
                )
        
        result_buffers=self.client3.read_multi_dbs(
            [16,16],
            [232,0],
            [24,160]#40个参数
        )
        
        for bytes in cut_signal_byte_array:
            current_cut_signals.append(su.get_bool(bytes, 0, 0))
        for bytes in pull_speed_byte_array:
            current_pull_speeds.append(su.get_real(bytes, 0))
        for bytes in length_byte_array:
            current_lengths.append(su.get_real(bytes, 0))
        
        print([current_cut_signals])
        #6个变量+水流量
        other_params = [
            '结晶器流量', '结晶器水温差', '二冷水总管压力',
            '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        ]
        #得到{结晶器流量:xxx,......}
        other_data.update({
            name: su.get_real(result_buffers[0], i*4)
            for i, name in enumerate(other_params)
        })

        buffer = result_buffers[1]

        for stream in range(1,9):#8流数据
            stream_values = []
            for segment in range(1,6):#每流五段
                #跳转到当前流起始字节位置+计算之前的段占用的字节数
                offset=(stream-1)*20+(segment-1)*4
                value=su.get_real(buffer,offset)
                stream_values.append({
                    'segment':segment,
                    'value':value
                })
            stream_data[f"流{stream}"]={
                'start':(stream-1)*20,
                'size':20,
                'values':stream_values
            }
        
    def _calculate_t0(self,cut_signal_ts:float,length:float,pull_speed_queue:deque[float]):
        """根据给定切割信号时间、定尺、拉速queue,计算t0的timestamp
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

    def _calculate_t2(self,t0,pull_speed_queue,index):
        """用拉速队列从t0开始计算到12m时的用时"""
        start_index=index
        t=t0
        s=0.0
        t3=0
        for i in range(start_index,len(pull_speed_queue)-1):
            v1=pull_speed_queue[i]
            v2=pull_speed_queue[i+1]
            dt=0.5
            s+=(v1+v2)*dt*0.5
            t+=dt
            if s>12.0:
                t3=t
                index2=i
                break
        return t3,index2
    
    def _calculate_data(self,delta_t,index1,index2,stream_index):
        """计算delta_t内的总水流量
           计算6个参数在delta_t内的平均值
        """

        stream_sum = 0
        for j in range(index1,index2):
            if j < len(self.stream_queue[stream_index]):  # 添加边界检查
                stream_sum += self.stream_queue[stream_index][j]  # 取指定流在j时刻的流量值
        total_stream=stream_sum*(1.0/7200.0)#计算i流总流量 = sum(瞬时流量)/7200
        self.logger.debug(f"流{stream_index+1}总流量: {total_stream}m³")    

        #'结晶器流量', '结晶器水温差', '二冷水总管压力',
        #   '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        other_res_list=[0.0]*6
        for i in range(index1,index2):
            other_data=self.other_queue[i]
            other_res_list[0] += other_data['结晶器流量']
            other_res_list[1] += other_data['结晶器水温差']
            other_res_list[2] += other_data['二冷水总管压力']
            other_res_list[3] += other_data['结晶器进水温度']
            other_res_list[4] += other_data['结晶器水压']
            other_res_list[5] += other_data['二冷水总管温度']
        #求出平均值
        other_res_list= [data/(index2-index1) for data in other_res_list]
        self.logger.debug(f"六个参数平均值分别为{other_res_list}")        

    def _data_acquisition_loop(self):
        """数据采集线程的主循环"""
        while not self.stop_event.is_set():
            try:
                #1. 读取数据并处理
                current_cut_signals = []#当前切割信号
                current_pull_speeds = []#当前拉速
                current_lengths = []#当前定尺
                other_data={}#6个变量
                stream_data={}#各流水流量
                self.collect_data(current_cut_signals,current_pull_speeds,current_lengths
                                  ,other_data,stream_data)
                
                #得到6个参数的瞬时值
                self.other_queue.append(other_data)
                #2.遍历8个流
                for i in range(self.stream_count):
                    #对应流的拉速队列中加入相应的拉速
                    self.pull_speed_queue[i].append(current_pull_speeds[i])
                    #存储对应流的定尺
                    self.current_lengths[i] = current_lengths[i]
                    #dict中的dict中的list
                    stream_values=stream_data[f"流{i+1}"]["values"]
                    #得到每一流的瞬时流量存入对应的流量队列
                    self.stream_queue[i].append(sum( v.get('value')  for v in stream_values))
                    
                    #切割信号出现上升沿
                    if current_cut_signals[i] and not self.last_cut_signals[i]:
                        if len(self.pull_speed_queue)>=800:#拉速采样次数满足后计算
                            cut_signal_time=time.time()#获取当前时间戳
                            #根据切割信号时间、当前定尺、拉速队列、计算t0 (index1指t0时刻队列中对应的索引)
                            t0,index1=self._calculate_t0(cut_signal_time,self.current_lengths[i],self.pull_speed_queue[i])
                            print(f"{i}流计算得到时间戳：{t0}")
                            #根据拉速队列，从t0对应的拉速开始计算t2（index2代表t2时刻队列中对应的索引）
                            t2,index2=self._calculate_t2(t0,self.pull_speed_queue[i],index1)
                            delta_t=t2-t0#拿到了0-12m的时间
                            #计算这段时间内的各流水流量、六个参数的平均值,并存入文件
                            self._calculate_data(delta_t,index1,index2,i)

                    self.last_cut_signals[i]=current_cut_signals[i]
                time.sleep(0.5) 

            except Exception as e:
                print(e)
            

if __name__ == "__main__":
    print("系统启动...")
    dh=DataHandler()
    dh.conn()
    print("连接成功")
    try:
        dh.start_data_acquisition()
        while not dh.stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt as e:
        print("\n接收到中断信号，正在停止...")
    finally:
        dh.stop_data_acquisition()
        print("程序已安全退出")
    
        



           







