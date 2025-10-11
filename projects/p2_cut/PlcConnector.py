import time
from utils import s7util as su
from snap7 import util as u
import threading
from utils import s7data as sd
from utils.StatePoint import BufferPoint

class PlcConnector:
    """与PLC进行通信，核心目标：
     减少通信次数 批量读取，一次性获取所有数据
    """
    def __init__(self):
        #初始化日志系统
        self.logger=su.Logger(__name__)
        self.logger.file_on()
        self.logger.screen_on()
        #初始化客户端
        self.client1=su.S7Client()
        self.client2=su.S7Client()
        self.client3=su.S7Client()
        #根据csv配置加载数据点
        self.s7_20=sd.S7data("conf/s7@172.16.1.20.csv")
        self.s7_215=sd.S7data("conf/s7@192.168.1.215.csv")
        self.s7_21=sd.S7data("conf/s7@172.16.1.21.csv")
        #工具类中放入客户端
        self.s7_20.set_S7Client(self.client1)
        self.s7_215.set_S7Client(self.client2)
        self.s7_21.set_S7Client(self.client3)

        
        self._read_lock=threading.Lock()

    def connect(self):
        """连接PLC"""
        self.client1.connect("172.16.1.20",0,1)
        self.client2.connect("192.168.1.215",0,1)
        self.client3.connect("172.16.1.21",0,1)
        self.logger.info("PLC clients connected")

    def start_data_acquisition(self):
        """开始数据自动获取"""
        pull_speed_buffer=[self.s7_20.make_point(f"{i}流结晶器拉速",BufferPoint) for i in range(1,9)]
        length_points=[self.s7_20.make_point(f"{i}流定尺") for i in range(1,9)]
        cutting_sig_points = [self.s7_215.make_point(f"L{i}切割信号[0]") for i in range(1, 9)]
        water_discharge_buffer = [[self.s7_21.make_point(f"5#水流量-{i}流-{j}段",BufferPoint)for j in range(1,6)] for i in range(1,9)]
        overall_temperature=self.s7_21.make_point(f"5#二冷水总管温度",BufferPoint)
        pressure=self.s7_21.make_point(f"5#二冷水总管压力",BufferPoint)
        billet_temperature=self.s7_20.make_point("中间包连续测温温度",BufferPoint)
        water_temperature_diff=self.s7_21.make_point("5#结晶器水温差",BufferPoint)
        
        self.s7_20.auto_update_group()
        self.s7_215.auto_update_group()
        self.s7_21.auto_update_group()
        #返回数据tuple
        return pull_speed_buffer,length_points,cutting_sig_points,water_discharge_buffer,overall_temperature,pressure,billet_temperature,water_temperature_diff