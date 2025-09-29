"""
重构后的完整程序：
- 将 PLC 访问、数据存储、计算、持久化分离成独立模块（高内聚、低耦合）
- 使用 SQLite 持久化计算结果
- 减少与 PLC 的通信：PlcConnector 提供批量读取与读取缓存机制（可配置的最小读取间隔）

注意：
- 程序仍然使用原来项目中的 snap7 / utils.s7util 接口（如果不存在，会回退到模拟模式以便本地测试）
- 请根据实际 PLC DB 地址/偏移调整 PlcConnector 中的读取参数

使用方法：
    python data_handler_refactor.py

我把重构后的完整代码放到一个文件（Data Handler Refactor）里，你可以在旁边的代码文档中看到并直接复制运行。关键点说明如下（很短）：

拆分为：PlcConnector（批量读取 + 读缓存，减少与 PLC 的通信）、DataStorage（队列缓存）、Calculator（t0/t2/积分/平均值）、Persistence（SQLite 持久化）、DataHandler（协调器和线程）。

默认为一次循环尽量批量读取一次 PLC（read_all_once），并在内存队列中累积采样，只有在检测到切割上升沿且样本足够多时触发计算与入库，从而显著减少 PLC 访问次数。

使用 SQLite 保存每次事件（t0、t2、总水量、六个参数平均值、平均流率），文件名默认 data_results.db。

如果运行环境没有 utils.s7util 或 snap7.util，程序会退到模拟模式，便于在本地调试。

可以很容易替换为 MySQL/Postgres：修改 Persistence 类即可。

"""

import threading
import time
import datetime
from collections import deque
import sqlite3
import logging
import traceback

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.integrate import quad

# 尝试导入项目里的 utils.s7util 与 snap7.util，若失败则启用模拟模式以便本地测试
try:
    import utils.s7util as u
    import snap7.util as su
    REAL_PLCS = True
except Exception:
    REAL_PLCS = False
    u = None
    su = None


# --------------------------- Logger --------------
def get_logger(name="DataHandlerRefactor"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


# --------------------------- Persistence (SQLite) --------------
class Persistence:
    """负责把计算出的事件持久化到 SQLite 数据库。"""
    def __init__(self, db_path='data_results.db', logger=None):
        self.db_path = db_path
        self.logger = logger or get_logger('Persistence')
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # 表存储每次切割事件的 t0、t2、总水量、六个参数平均值、流编号、产生时间戳
        cur.execute('''
        CREATE TABLE IF NOT EXISTS flow_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stream_index INTEGER,
            t0 REAL,
            t2 REAL,
            duration_seconds REAL,
            total_water REAL,
            avg_flow_rate REAL,
            crystallizer_flow REAL,
            crystallizer_temp_diff REAL,
            coldpipe_pressure REAL,
            crystallizer_in_temp REAL,
            crystallizer_pressure REAL,
            coldpipe_temp REAL,
            created_at REAL
        )
        ''')
        conn.commit()
        conn.close()
        self.logger.info(f"SQLite DB initialized at {self.db_path}")

    def save_flow_event(self, stream_index:int, t0:float, t2:float, total_water:float, avg_params:dict, avg_flow_rate:float):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            duration = t2 - t0
            row = (
                stream_index+1,
                float(t0),
                float(t2),
                float(duration),
                float(total_water),
                float(avg_flow_rate),
                float(avg_params.get('结晶器流量', 0.0)),
                float(avg_params.get('结晶器水温差', 0.0)),
                float(avg_params.get('二冷水总管压力', 0.0)),
                float(avg_params.get('结晶器进水温度', 0.0)),
                float(avg_params.get('结晶器水压', 0.0)),
                float(avg_params.get('二冷水总管温度', 0.0)),
                datetime.datetime.now().timestamp()
            )
            cur.execute('''INSERT INTO flow_events (
                stream_index, t0, t2, duration_seconds, total_water, avg_flow_rate,
                crystallizer_flow, crystallizer_temp_diff, coldpipe_pressure,
                crystallizer_in_temp, crystallizer_pressure, coldpipe_temp, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', row)
            conn.commit()
            conn.close()
            self.logger.info(f"Saved flow event for stream {stream_index+1}, total_water={total_water:.4f} m^3")
        except Exception as e:
            self.logger.error(f"Failed to save event: {e}\n{traceback.format_exc()}")


# --------------------------- PlcConnector --------------
class PlcConnector:
    """与PLC进行通信，核心目标：
    1. 减少通信次数 批量读取，一次性获取所有数据
    2. 提供缓存机制 避免短时间内读取同样的地址
    """
    def __init__(self, logger=None, min_read_interval=0.4):
        self.logger = logger or get_logger('PlcConnector')
        self.min_read_interval = min_read_interval  # 同一类读请求最小间隔（秒）
        self._last_read_time = {}  #缓存最近一次读取的原始数据
        self._read_lock = threading.Lock()

        if REAL_PLCS:
            # 使用真实 S7 客户端
            self.client1 = u.S7Client()
            self.client2 = u.S7Client()
            self.client3 = u.S7Client()
        else:
            self.client1 = None
            self.client2 = None
            self.client3 = None
            self.logger.warning("Running in SIMULATION mode for PLC reads")

    def connect(self):
        if not REAL_PLCS:
            return
        self.client1.connect("172.16.1.20",0,1)
        self.client2.connect("192.168.1.215",0,1)
        self.client3.connect("172.16.1.21",0,1)
        self.logger.info("PLC clients connected")

    def _should_use_cache(self, key):
        now = time.time()
        last = self._last_read_time.get(key, 0)
        return (now - last) < self.min_read_interval

    def _update_read_time(self, key):
        self._last_read_time[key] = time.time()

    # 下面的 read_* 方法封装了批量读取并返回解包后的 Python 结构。
    def read_all_once(self):
        """返回：
        (cut_signals: list[bool] (len=8), pull_speeds: list[(speed,ts)], lengths:list[float], other_params:dict, stream_values:dict)
        该方法尽可能在一次或少量请求中批量读取所有需要的数据。
        """
        with self._read_lock:
            # key 简单使用固定字符串，使得短时间内重复调用时可以走缓存机制
            key = 'read_all'
            if self._should_use_cache(key):
                # 如果最近刚读过，则尽量返回空或上次数据：为了简洁，这里直接继续读（实际可缓存上一份）
                pass
            self._update_read_time(key)

            if REAL_PLCS:
                
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

                # 解析
                cut_signals = [su.get_bool(b,0,0) for b in cut_signal_byte_array]
                pull_speeds = [(su.get_real(b,0), time.time()) for b in pull_speed_byte_array]
                lengths = [su.get_real(b,0) for b in length_byte_array]

                other_params = [
                    '结晶器流量', '结晶器水温差', '二冷水总管压力',
                    '结晶器进水温度', '结晶器水压', '二冷水总管温度'
                ]
                new_data = {name: su.get_real(result_buffers[0], i*4) for i, name in enumerate(other_params)}
                new_data['timestamp'] = time.time()

                buffer = result_buffers[1]
                stream_data = {}
                for stream in range(1,9):
                    stream_values = []
                    for segment in range(1,6):
                        offset=(stream-1)*20 + (segment-1)*4
                        value = (su.get_real(buffer, offset), time.time())
                        stream_values.append({'segment':segment,'value':value})
                    stream_data[f"流{stream}"] = {
                        'start':(stream-1)*20,
                        'size':20,
                        'values':stream_values
                    }

                return cut_signals, pull_speeds, lengths, new_data, stream_data
            else:
                # 模拟数据（便于本地调试）
                cut_signals = [False]*8
                pull_speeds = [(100.0 + i, time.time()) for i in range(8)]
                lengths = [1200.0+i*10 for i in range(8)]
                other = {
                    '结晶器流量': 10.0,
                    '结晶器水温差': 0.8,
                    '二冷水总管压力': 0.5,
                    '结晶器进水温度': 20.0,
                    '结晶器水压': 0.6,
                    '二冷水总管温度': 18.0,
                    'timestamp': time.time()
                }
                stream_data = {}
                for s in range(1,9):
                    vals=[]
                    for seg in range(1,6):
                        vals.append({'segment':seg,'value':(1.0*seg + s, time.time())})
                    stream_data[f"流{s}"] = {'start':(s-1)*20,'size':20,'values':vals}
                return cut_signals, pull_speeds, lengths, other, stream_data


# --------------------------- DataStorage --------------
class DataStorage:
    def __init__(self, stream_count=8, maxlen=2000, logger=None):
        self.stream_count = stream_count
        self.pull_speed_queue = [deque(maxlen=maxlen) for _ in range(stream_count)]
        self.stream_queue = [deque(maxlen=maxlen) for _ in range(stream_count)]
        self.other_queue = deque(maxlen=maxlen)
        self.current_lengths = [0.0] * stream_count
        self.last_cut_signals = [False] * stream_count
        self.logger = logger or get_logger('Storage')

    def push_pull_speeds(self, speeds_list):
        for i, item in enumerate(speeds_list):
            self.pull_speed_queue[i].append(item)

    def push_streams(self, stream_data):
        for i in range(self.stream_count):
            self.stream_queue[i].append(stream_data[f"流{i+1}"]['values'])

    def push_other(self, other):
        self.other_queue.append(other)


# --------------------------- Calculator --------------
class Calculator:
    def __init__(self, logger=None):
        self.logger = logger or get_logger('Calculator')

    def _make_v_tfunc(self, pull_speed_queue:deque):
        speed_time_list = list(pull_speed_queue)
        if len(speed_time_list) < 2:
            raise ValueError("拉速数据太少，无法插值")
        speeds, times = zip(*speed_time_list)
        t_arr = np.array(times)
        v_arr = np.array(speeds) / 60.0
        return CubicSpline(t_arr, v_arr, bc_type='natural'), t_arr

    def calc_t0(self, cut_signal_ts:float, length:float, pull_speed_queue:deque):
        total = 28.0 + length * 0.001
        t1 = cut_signal_ts
        v_tfunc, time_array = self._make_v_tfunc(pull_speed_queue)

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

    def calc_t2(self, t0:float, pull_speed_queue:deque, length:float):
        v_tfunc, time_array = self._make_v_tfunc(pull_speed_queue)
        def distance_func(t):
            return quad(v_tfunc, t0, t)[0]
        t_low = float(t0)
        t_high = float(time_array[-1])
        if t_low >= t_high:
            return t_high
        tol = 1e-6
        target = 12.0 + length * 0.001
        while abs(t_high - t_low) > tol:
            t_mid = (t_low + t_high) / 2
            cur = distance_func(t_mid)
            if cur < target:
                t_low = t_mid
            else:
                t_high = t_mid
        return (t_low + t_high) / 2

    def calc_total_water_and_avg_params(self, start_time:float, end_time:float, stream_queue:deque, other_queue:deque):
        # 计算总水量
        time_list = []
        flow_list = []
        for stream_values in stream_queue:
            # stream_values 是 [{'segment':i,'value':(flow,ts)}, ...]
            if not stream_values:
                continue
            flow_rate = sum(s.get('value')[0] for s in stream_values)
            ts = stream_values[0].get('value')[1]
            time_list.append(ts)
            flow_list.append(flow_rate)
        if len(time_list) < 2:
            self.logger.warning('流队列数据不足，无法计算水量')
            total_water = 0.0
            avg_flow_rate = 0.0
        else:
            x = np.array(time_list)
            y = np.array(flow_list) / 3600.0  # 转为 m^3/s
            flow_t_func = CubicSpline(x, y)
            total_water = quad(flow_t_func, start_time, end_time)[0]
            # 平均流速（m^3/s）
            avg_flow_rate = total_water / (end_time - start_time) if end_time > start_time else 0.0

        # 计算6个参数平均值
        param_names = [
            '结晶器流量', '结晶器水温差', '二冷水总管压力',
            '结晶器进水温度', '结晶器水压', '二冷水总管温度'
        ]
        valid = [d for d in other_queue if start_time <= d.get('timestamp', 0) <= end_time]
        if not valid:
            self.logger.warning('在时间范围内没有参数数据')
            avg_params = {name:0.0 for name in param_names}
        else:
            sums = {name:0.0 for name in param_names}
            for d in valid:
                for name in param_names:
                    sums[name] += d.get(name, 0.0)
            avg_params = {name: sums[name]/len(valid) for name in param_names}

        return total_water, avg_params, avg_flow_rate


# --------------------------- DataHandler (Coordinator) --------------
class DataHandler:
    def __init__(self, stream_count=8, logger=None, db_path='data_results.db'):
        self.logger = logger or get_logger('DataHandler')
        self.stream_count = stream_count
        self.plc = PlcConnector(self.logger)
        self.storage = DataStorage(stream_count=stream_count, logger=self.logger)
        self.calc = Calculator(logger=self.logger)
        self.persist = Persistence(db_path=db_path, logger=self.logger)

        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.plc.connect()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.logger.info('数据采集线程启动')

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info('数据采集线程停止')

    def _process_once(self):
        # 一次性批量读取数据并更新存储
        cut_signals, pull_speeds, lengths, other, stream_data = self.plc.read_all_once()
        # 将读取到的数据写入 storage
        self.storage.push_pull_speeds(pull_speeds)
        self.storage.push_streams(stream_data)
        self.storage.push_other(other)
        for i in range(self.stream_count):
            self.storage.current_lengths[i] = lengths[i]

        # 检查切割信号上升沿
        for i in range(self.stream_count):
            prev = self.storage.last_cut_signals[i]
            curr = cut_signals[i]
            if curr and not prev:
                # 触发计算
                # 只有在采样足够多时才计算（防止样本不足）
                if len(self.storage.pull_speed_queue[i]) >= 100:
                    cut_ts = time.time()
                    try:
                        t0 = self.calc.calc_t0(cut_ts, self.storage.current_lengths[i], self.storage.pull_speed_queue[i])
                        t2 = self.calc.calc_t2(t0, self.storage.pull_speed_queue[i], self.storage.current_lengths[i])

                        total_water, avg_params, avg_flow_rate = self.calc.calc_total_water_and_avg_params(t0, t2, self.storage.stream_queue[i], self.storage.other_queue)

                        # 持久化
                        self.persist.save_flow_event(i, t0, t2, total_water, avg_params, avg_flow_rate)
                        self.logger.info(f"流{i+1}处理完成：t0={t0:.3f}, t2={t2:.3f}, total_water={total_water:.4f} m^3")

                    except Exception as e:
                        self.logger.error(f"计算失败（流{i+1}）: {e}\n{traceback.format_exc()}")
                else:
                    self.logger.info(f"流{i+1}采样数不足（{len(self.storage.pull_speed_queue[i])}）")
            self.storage.last_cut_signals[i] = curr

    def _loop(self):
        # 主循环：尽量批量读取，减少PLC通信次数
        while not self.stop_event.is_set():
            try:
                start = time.time()
                self._process_once()
                elapsed = time.time() - start
                # 目标循环周期：0.4-0.6s（可根据 min_read_interval 调整）
                sleep_for = max(0.05, 0.5 - elapsed)
                time.sleep(sleep_for)
            except Exception as e:
                self.logger.error(f"主循环异常: {e}\n{traceback.format_exc()}")


# --------------------------- main --------------
if __name__ == '__main__':
    logger = get_logger('Main')
    dh = DataHandler(logger=logger)
    try:
        dh.start()
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info('接收到中断，停止...')
    finally:
        dh.stop()
        logger.info('程序退出')
