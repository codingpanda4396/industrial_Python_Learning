import threading
import time
import traceback
from utils import s7util as su
import Calculator,DataStorage,PlcConnector,Persistence

class DataHandler:
    def __init__(self, stream_count=8, logger=None, db_path='data_results.db'):
        #初始化日志系统
        self.logger = su.Logger(__name__)
        self.logger.screen_on()
        self.logger.file_on()

        self.stream_count = stream_count#流数
        self.plc = PlcConnector.PlcConnector()
        self.storage = DataStorage.DataStorage(stream_count=stream_count, logger=self.logger)
        self.calc = Calculator.Calculator()
        self.persist = Persistence.Persistence()

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
                if len(self.storage.pull_speed_queue[i]) >= 1500:
                    cut_ts = time.time()
                    try:
                        t0 = self.calc.calc_t0(cut_ts, self.storage.current_lengths[i], self.storage.pull_speed_queue[i])
                        t2 = self.calc.calc_t2(t0, self.storage.pull_speed_queue[i], self.storage.current_lengths[i])

                        total_water, avg_params, avg_flow_rate = self.calc.calc_total_water_and_avg_params(t0, t2, self.storage.stream_queue[i], self.storage.other_queue)

                        # 持久化
                        #avg_params:
                        # {
                        #     '结晶器流量': 123.45,       # float类型，来自result_buffers的0偏移位置
                        #     '结晶器水温差': 5.67,       # float类型，来自result_buffers的4字节偏移 
                        #     '二冷水总管压力': 1.23,     # float类型，来自result_buffers的8字节偏移
                        #     '结晶器进水温度': 45.6,      # float类型，来自result_buffers的12字节偏移
                        #     '结晶器水压': 3.21,         # float类型，来自result_buffers的16字节偏移
                        #     '二冷水总管温度': 32.1,      # float类型，来自result_buffers的20字节偏移
                        #     'timestamp': 1630000000.123 # float类型，记录数据采集时间
                        # }
                        self.persist.save_flow_event(i, cut_ts,t0, t2,avg_params['二冷水总管温度'],avg_params['二冷水总管压力']
                                                     , total_water,0,0,0,avg_params['结晶器水温差'])


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

if __name__ ==  "__main__":
    dh=DataHandler(8)
    dh.start()
