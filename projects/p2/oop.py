import threading
import snap7
from collections import deque
from time import perf_counter
import random
import time
from threading import Thread

class PLCClinet:
    """管理plc连接、数据读写"""
    def __init__(self, ip_address='127.0.0.1', rack=0, slot=1, db_number=1):
        self.ip_address = ip_address
        self.rack = rack
        self.slot = slot
        self.db_number = db_number
        self.plc = snap7.client.Client()
        self.lock = threading.Lock()
    def connect(self)->bool:
        try:
            self.plc.connect(self.ip_address, self.rack, self.slot)
            if self.plc.get_connected():
                print("连接成功")
                return True
            else:
                print("PLC连接失败")
                return False
        except Exception as e:
            print(f"连接异常:{e}")
            return False
    def disconnect(self):
        try:
           if self.plc:
               self.plc.disconnect()
               self.plc.destroy()
               print("plc连接安全断开。。") 
        except Exception as e:
            print(f"PLC断开异常:{e}")
    def read_data(self,start,size):
        with self.lock:
            try:
                data = self.plc.db_read(self.db_number,start,size)
                return data
            except Exception as e:
                print(f"读取PLC数据失败: {e}")
                return None
    def write_data(self,start,data)-> bool:
        with self.lock:
            try:
                self.plc.db_write(self.db_number,start,data)
                return True
            except Exception as e:
                print(f"写PLC数据失败:{e}")
                return False
            
class DataProcessor:    
    """处理PLC数据"""
    @staticmethod
    def parse_plc_data(data):
        if data is None or len(data)<10:#判空
            return None
        try:
            v = snap7.util.get_real(data, 0)  # 拉速 (m/min)
            cut = snap7.util.get_bool(data, 4, 0)  # 切割信号
            Lcut = snap7.util.get_dword(data, 6) / 1000.0  # 定尺长度 (mm -> m)
            return {'velocity': v, 'cut_signal': cut, 'cut_length': Lcut}#工具类转换之后返回一个字典
        except Exception as e:
            print(f"解析PLC数据异常: {e}")
            return None


class TimeCalculator:
    """计算进入时刻、切割时刻、12m处时刻"""
    def __init__(self, Lcaster=28.0):
        self.data_history = deque(maxlen=2000)
        self.Lcaster = Lcaster
        self.prev_cut_signal = False#之前的信号

    def detect_cut_and_calculate(self, current_ts, current_data):
        """
        检测切割信号上升沿，若检测到则计算相关时间点
        """
        # 1.获取信号
        current_cut_signal=current_data['cut_signal']
        results={}#结果集合 
        #2.检测上升沿
        if not self.prev_cut_signal and current_cut_signal:
            t2=current_ts
            print(f"检测到切割信号上升沿，时刻 t2={t2:.2f}s")
            
            Sneed=self.Lcaster+current_data['cut_length']

            enter_ts=self._calculate_enter_ts(Sneed)

            if enter_ts is not None:
                results['t1']=enter_ts
                print(f"计算得到进入时刻 t0={enter_ts:.2f}s")

                t3=self._calculate_12m_ts(enter_ts)

                if t3 is not None:
                    results['t3']=t3
                    print(f"计算得到12m处时刻 t3={t3:.2f}s")
            else:
                print("历史数据不足，无法回溯计算进入时刻")
        self.prev_cut_signal=current_cut_signal#更新信号状态
        #信息加入队列
        self.data_history.append((current_ts,current_data['velocity'], current_cut_signal, current_data['cut_length']))
        return results
        
            
    def _calculate_enter_ts(self, Sneed):
        """通过回溯历史数据积分计算进入时刻"""
        S=0.0#累计距离
        enter_ts=None
        for i in range(len(self.data_history)-1,0,-1):
            ts1,v1,_,_ =self.data_history[i-1]
            ts2,v2,_,_ =self.data_history[i]
            dt=ts2-ts1
            ds=dt*0.5*(v1+v2)
            S+=ds
            if S>=Sneed:
                extra=S-Sneed
                frac=(ds-extra)/ds if ds>0 else 0#最后一段需要的距离/最后一段走的总距离
                enter_ts=ts1+frac*dt
                break#跳出循环
        return enter_ts


    def _calculate_12m_ts(self, enter_ts):
        """正常积分计算开始到12m处的时间
        """
        S12=0.0
        t3=None
        start_index=None

        for i,(ts,_,_,_) in enumerate(self.data_history):
            if ts>enter_ts:
                start_index=i
                break
        if start_index is not None:
            for i in range(start_index,len(self.data_history)-1):
                ts1,v1,_,_ = self.data_history[i]
                ts2,v2,_,_ = self.data_history[i+1]
                dt=ts2-ts1
                ds=dt*0.5*(v1+v2)
                S12+=ds
                if S12>=12.0:
                    extra=S12-12.0
                    frac=(ds-extra)/ds if ds>0 else 0
                    t3 = ts1+frac*dt#计算出精确时间
                    break   
            return t3



class DataSimulator:
    def __init__(self, plc_client):
        self.plc_client = plc_client
        self.simulating = False
        self.thread = None

    def start_simulation(self):
        """启动模拟线程"""
        self.simulating = True
        self.thread = Thread(target=self._simulate_worker, daemon=True)
        self.thread.start()
        print("数据模拟器已启动")

    def stop_simulation(self):
        """停止模拟"""
        self.simulating = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("数据模拟器已停止")

    def _simulate_worker(self):
        """模拟工作线程"""
        cut_signal = False
        cut_counter = 0
        data_to_write = bytearray(10)

        while self.simulating:
            # 模拟拉速 (m/min) 波动
            pull_speed = 3.0 + random.uniform(-0.5, 0.5)
            cut_counter += 1 
            # 约每3秒翻转一次切割信号
            if cut_counter > 30:
                cut_signal = not cut_signal
                cut_counter = 0

            # 组装数据并写入
            snap7.util.set_real(data_to_write, 0, pull_speed)
            snap7.util.set_bool(data_to_write, 4, 0, cut_signal)
            snap7.util.set_dword(data_to_write, 6, 11770)  # 定尺 11770mm

            if self.plc_client.write_data(0, data_to_write):
                print(f"模拟数据写入成功: 拉速={pull_speed:.2f}, 切割信号={cut_signal}")
            else:
                print("模拟数据写入失败")

            time.sleep(0.1)  # 模拟数据更新周期


class ProductionMonitor:
    """协调PLC通信、数据处理、数据模拟"""
    def __init__(self,ip_address='127.0.0.1'):
        self.plc_client=PLCClinet(ip_address)
        self.data_processor=DataProcessor()
        self.time_calculator=TimeCalculator(Lcaster=28.0)
        self.data_simulator=DataSimulator(self.plc_client)
        self.monitoring = False

    def start(self):    
        """启动监控系统"""
        if not self.plc_client.connect():
            return False

        self.monitoring=True
        self.data_simulator.start_simulation()

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("用户中断监控")
        finally:
            self.stop()
    def stop(self):
        """停止监控并清理资源"""
        self.monitoring = False
        self.data_simulator.stop_simulation()
        self.plc_client.disconnect()
        print("监控系统已安全退出")
    def _main_loop(self):       
        """主循环"""
        while self.monitoring:
            data=self.plc_client.read_data(0,10)
            if data is None:
                time.sleep(0.1)
                continue
            parsed_data=self.data_processor.parse_plc_data(data)
            if parsed_data is None:
                time.sleep(0.05)
                continue
            current_ts=perf_counter()

            results=self.time_calculator.detect_cut_and_calculate(current_ts,parsed_data)
            if 't3' in results and 't1' in results:
                t1 = results['t1']
                t3 = results['t3']
                print("\n*** 计算结果 ***")
                print(f"进入时刻 t0: {t1:.2f} s")
                print(f"12m 处时刻 t3: {t3:.2f} s")
                print(f"0-12m用时{t3-t1}")
                break
            time.sleep(0.05)  # 控制主循环周期

if __name__ == "__main__":
    monitor = ProductionMonitor(ip_address='127.0.0.1')
    monitor.start()

        
