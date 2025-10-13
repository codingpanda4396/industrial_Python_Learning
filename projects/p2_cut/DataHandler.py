import datetime
import threading
import time
import traceback
from utils import s7util as su
import utils.Calculator as Calculator,DataBridge as DataBridge,PlcConnector,Persistence

class DataHandler:
    def __init__(self, logger=None, db_path='data_results.db'):
        #初始化日志系统
        self.logger = su.Logger(__name__)
        self.logger.screen_on()
        self.logger.file_on()

        self.plc = PlcConnector.PlcConnector()
        #连接并启动自动数据更新
        self.plc.connect()
        data:tuple=self.plc.generate_points()
        self.bridge= DataBridge.DataBridge(*data)
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info('数据采集线程停止')

    def _process_once(self):
        self.bridge.data_storage()

    def _loop(self):
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
    dh=DataHandler()
    try:
        dh.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt as e:
        dh.stop()

    

