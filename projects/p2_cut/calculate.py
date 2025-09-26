from collections import deque
import datetime
import threading
import time
import s7util as u
import snap7.util as su
import numpy as np
from  scipy.interpolate import CubicSpline
from  scipy.integrate import quad
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
        self.logger.file_on('res.log')
        self.logger.screen_on()
        
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
        self.data_thread = threading.Thread(target=self._data_acquisition_loop, daemon=True)
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
            current_pull_speeds.append((su.get_real(bytes, 0),datetime.datetime.now().timestamp()))#得到拉速、对应时间戳
        for bytes in length_byte_array:
            current_lengths.append(su.get_real(bytes, 0))
        
        #6个变量+水流量
        other_params = [
            '结晶器流量', '结晶器水温差', '二冷水总管压力',
            '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        ]
        #得到{结晶器流量:xxx,......}
        new_data = {name: su.get_real(result_buffers[0], i*4) for i, name in enumerate(other_params)}
        new_data["timestamp"] = datetime.datetime.now().timestamp()
        other_data.update(new_data)

        buffer = result_buffers[1]

        for stream in range(1,9):#8流数据
            stream_values = []
            for segment in range(1,6):#每流五段
                #跳转到当前流起始字节位置+计算之前的段占用的字节数
                offset=(stream-1)*20+(segment-1)*4
                value=(su.get_real(buffer,offset),datetime.datetime.now().timestamp())
                stream_values.append({
                    'segment':segment,
                    'value':value
                })
            stream_data[f"流{stream}"]={
                'start':(stream-1)*20,
                'size':20,
                'values':stream_values
            }
        
    def _calculate_t0(self,cut_signal_ts:float,length:float,pull_speed_queue:deque[(float,float)]):
        """根据给定切割信号时间、定尺、拉速queue,计算t0的timestamp
        """
        # total=28.0+length*0.001#钢坯走过的距离
        # time_interval=0.5
        # S=0.0
        # t=cut_signal_ts
        # t0=0
        # index=0
        # for i in range(len(pull_speed_queue)-1,0,-1):#倒序遍历队列
        #     v1=pull_speed_queue[i-1]
        #     v2=pull_speed_queue[i]
        #     dt=time_interval
        #     ds=dt*0.5*(v1+v2)
        #     S+=ds
        #     t-=dt#切割时间减去一个个time_interval，得到
        #     if S>total:
        #         t0=t
        #         index=i
        #         break
        # return t0,index
        total = 28.0+length*0.001#t0-t1钢坯走过的长度
        t1=cut_signal_ts
        #1.得到v-t函数(拉速-时间戳)
        speed_time_list=list(pull_speed_queue)
        speed_tuple,time_tuple=zip(*speed_time_list)
        time_array=np.array(time_tuple)
        speed_array=np.array(speed_tuple)/60.0
        #三次样条插值得到v-t函数
        v_tfunc=CubicSpline(time_array,speed_array,bc_type='natural')
        #2.根据v-t函数积分，t0到t1速度对时间的积分=28+定尺,从而求出t0
        """计算t0到t1的距离"""
        def cal_len(t0):
            return quad(v_tfunc,t0,t1)[0]
        
        t_low=time_array[0]#最早可能的时间
        t_high = cut_signal_ts#最晚可能的时间
        tolerance=1e-6#精度控制

        while abs(t_high-t_low)>tolerance:
            t_mid=(t_low+t_high)/2
            cur_len=cal_len(t_mid)

            if cur_len>total:
                t_low=t_mid 
            else:
                t_high=t_mid
        t0=(t_low+t_high)/2
        
        return t0

    def _calculate_t2(self,t0,pull_speed_queue,):
        """用拉速队列从t0开始计算到12m时的用时"""
        # start_index=index
        # t=t0
        # s=0.0
        # t3=0
        # for i in range(start_index,len(pull_speed_queue)-1):
        #     v1=pull_speed_queue[i]
        #     v2=pull_speed_queue[i+1]
        #     dt=0.5
        #     s+=(v1+v2)*dt*0.5
        #     t+=dt
        #     if s>12.0:
        #         t3=t
        #         index2=i
        #         break
        # return t3,index2

        speed_time_list=list(pull_speed_queue)
        
        speeds,timestamps=zip(*speed_time_list)#得到(v1,v2,v3...) (t1,t2,t3,...)
        time_array = np.array(timestamps)
        speed_array = np.array(speeds) / 60.0  # 转换为米/秒

        v_tfunc=CubicSpline(time_array, speed_array, bc_type='natural')
        # 定义积分函数：从t0到t的距离
        def distance_func(t):
            return quad(v_tfunc, t0, t)[0]
        
        t_low = t0
        t_high = time_array[-1]  # 队列中最后的时间点
        tolerance = 1e-6  # 精度控制
        
        # 二分查找
        while abs(t_high - t_low) > tolerance:
            t_mid = (t_low + t_high) / 2
            current_distance = distance_func(t_mid)
            
            if current_distance < 12.0:
                t_low = t_mid
            else:
                t_high = t_mid
        
        t2 = (t_low + t_high) / 2
        
        
        
        return t2
        
        
    
    def _calculate_data(self, start_time, end_time, stream_index):
        """计算t0-t2的总水流量
           计算6个参数在时间段内的平均值
        """

        # stream_sum = 0
        # for j in range(index1,index2):
        #     if j < len(self.stream_queue[stream_index]):  # 添加边界检查
        #         stream_sum += self.stream_queue[stream_index][j]  # 取指定流在j时刻的流量值
        # total_stream=stream_sum*(1.0/7200.0)#计算i流总流量 = sum(瞬时流量)/7200
        # self.logger.debug(f"流{stream_index+1}总流量: {total_stream}立方米")    

        # #'结晶器流量', '结晶器水温差', '二冷水总管压力',
        # #   '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        # other_res_list=[0.0]*6
        # for i in range(index1,index2):
        #     other_data=self.other_queue[i]
        #     other_res_list[0] += other_data['结晶器流量']
        #     other_res_list[1] += other_data['结晶器水温差']
        #     other_res_list[2] += other_data['二冷水总管压力']
        #     other_res_list[3] += other_data['结晶器进水温度']
        #     other_res_list[4] += other_data['结晶器水压']
        #     other_res_list[5] += other_data['二冷水总管温度']
        # #求出平均值
        # other_res_list= [data/(index2-index1) for data in other_res_list]
        # self.logger.debug(f"六个参数平均值分别为{other_res_list}")  


        total_water=0.0
        #要计算总水量：
        #1. 首先要获得总流量-时间函数
        #2. 对总流量-时间函数在t0-t2上积分

        #该流的流量统计队列,队列中的元素是一个个（stream_values = [{'segment':1,'value':(流量,ts)},{'segment':1,'value':(流量,ts)}...]）
        #代表了ts时刻的5段流量list
        
        queue=self.stream_queue[stream_index]
        time_list=[]
        flow_list=[]
        for stream_values in queue:
            flow_rate = sum(  stream_values[i].get('value')[0] for i in range(5) )
            flow_list.append(flow_rate)
            time_list.append(stream_values[0].get('value')[1])
        x=np.array(time_list)
        y=np.array(flow_list)
        flow_t_func=CubicSpline(x,y)#得到总流量-时间函数
        total_water=quad(flow_t_func,start_time,end_time)[0]
        
        self.logger.debug(f"流{stream_index+1}总流量: {total_water:.4f}立方米")
        param_names = [
        '结晶器流量', '结晶器水温差', '二冷水总管压力',
        '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        ]      
        valid_data=[]
        for data in self.other_queue:
            data_time=data.get('timestamp',None)
            if data_time and start_time <= data_time <= end_time:
                valid_data.append(data)
        if not valid_data:
            self.logger.warning(f"流{stream_index+1}在时间范围内没有有效的参数数据")
            return
        
        param_sums = {name: 0.0 for name in param_names}
        for data in valid_data:
            for name in param_names:
                param_sums[name] += data.get(name,0.0)
        
        param_avgs = {name: total/len(valid_data) for name, total in param_sums.items()}

        avg_str = ", ".join([f"{name}:{value:.2f}" for name, value in param_avgs.items()])  
        self.logger.debug(f"流{stream_index+1}六个参数平均值: {avg_str}")




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
                    #拿到该流的5段流量list（dict中的dict中的list）
                    stream_values=stream_data[f"流{i+1}"]["values"]#stream_values = [{'segment':1,'value':(流量,ts)},{'segment':1,'value':(流量,ts)}...]
                    #得到每一流的瞬时流量存入对应的(流量,timestamp)队列
                    self.stream_queue[i].append(stream_values)
                    #切割信号出现上升沿
                    if current_cut_signals[i] and not self.last_cut_signals[i]:
                        if len(self.pull_speed_queue[i])>=1500:#拉速采样次数满足后计算
                            cut_signal_time=datetime.datetime.now().timestamp()#获取当前时间戳
                            #根据切割信号时间、当前定尺、拉速队列、计算t0 
                            t0=self._calculate_t0(cut_signal_time,self.current_lengths[i],self.pull_speed_queue[i])
                            self.logger.info(f"钢坯行走用时：{(cut_signal_time-t0)/60.0}min")
                            print(f"{i}流计算得到时间戳：{t0}")
                            #根据拉速队列，从t0对应的拉速开始计算t2
                            t2=self._calculate_t2(t0,self.pull_speed_queue[i])
                            
                            #计算这段时间内的各流水流量、六个参数的平均值,并存入文件
                            self._calculate_data(t0,t2, i)
                        else:
                            self.logger.info(f"{i+1}流采样数不够。。。")
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
    
        



           







