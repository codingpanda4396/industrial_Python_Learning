import time
from utils import s7util as su
from snap7 import util as u
import threading

class PlcConnector:
    """与PLC进行通信，核心目标：
    1. 减少通信次数 批量读取，一次性获取所有数据
    2. 提供缓存机制 避免短时间内读取同样的地址
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
        #TODO 缓存机制
        # self.cache_ttl =cache_ttl
        # self._cache= {}
        # self.read_map=read_map
        #LOCK
        self._read_lock=threading.Lock()

    def connect(self):
        """连接PLC"""
        self.client1.connect("172.16.1.20",0,1)
        self.client2.connect("192.168.1.215",0,1)
        self.client3.connect("172.16.1.21",0,1)
        self.logger.info("PLC clients connected")

    def read_all_once(self):
        """返回：
        (cut_signals: list[bool] (len=8), pull_speeds: list[(speed,ts)], lengths:list[float], other_params:dict, stream_values:dict)
        该方法尽可能在一次或少量请求中批量读取所有需要的数据。
        """
        with self._read_lock:
            #TODO 将plc的读取次数尽可能的压缩
            cut_signal_byte_array = self.client2.read_multi_dbs(
                    [131, 132, 133, 134, 135, 136, 137, 138],
                    [4, 4, 4, 4, 4, 4, 4, 4],
                    [1, 1, 1, 1, 1, 1, 1, 1]
                )

            pull_speed_byte_array = self.client1.read_multi_dbs(
                [6]*8,
                [36,40,44,48,52,56,60,64],
                [4]*8
            )

            length_byte_array = self.client1.read_multi_dbs(
                [6]*8,
                [72,76,80,84,88,92,96,100],
                [4]*8
            )

            result_buffers=self.client3.read_multi_dbs(
                [16,16],
                [232,0],
                [24,160]
            )
            #解析得到切割信号、拉速、定尺
            cut_signals = [u.get_bool(b,0,0) for b in cut_signal_byte_array]
            pull_speeds = [(u.get_real(b,0), time.time()) for b in pull_speed_byte_array]
            lengths = [u.get_real(b,0) for b in length_byte_array]

            other_params = [
                    '结晶器流量', '结晶器水温差', '二冷水总管压力',
                    '结晶器进水温度', '结晶器水压', '二冷水总管温度'
                ]
            other_data = {name: u.get_real(result_buffers[0], i*4) for i, name in enumerate(other_params)}
            other_data['timestamp'] = time.time()

            buffer = result_buffers[1]
            stream_data = {}
            for stream in range(1,9):
                stream_values = []
                for segment in range(1,6):
                    offset=(stream-1)*20 + (segment-1)*4
                    value = (u.get_real(buffer, offset), time.time())
                    stream_values.append({'segment':segment,'value':value})
                stream_data[f"流{stream}"] = {
                    'values':stream_values
                }
            return cut_signals, pull_speeds, lengths, other_data, stream_data


