from collections import deque
import datetime
import threading
import time
import s7util as u
import snap7.util as su
import numpy as np


import threading
import time
import datetime
import logging
from collections import deque
import numpy as np


class DataHandler:
    def __init__(self, max_queue_len=1000, sample_interval=0.5):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # 每个流的拉速队列和瞬时流量队列（存 (timestamp, value)）
        self.pull_speed_queue = [deque(maxlen=max_queue_len) for _ in range(5)]
        self.stream_queue = [deque(maxlen=max_queue_len) for _ in range(5)]
        # 其他 6 个参数（存 (timestamp, dict)）
        self.other_queue = deque(maxlen=max_queue_len)

        self.sample_interval = sample_interval
        self.lock = threading.Lock()

        self.running = False
        self.thread = None

    def start(self):
        """启动采集线程"""
        self.running = True
        self.thread = threading.Thread(target=self._data_acquisition_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """停止采集线程"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _data_acquisition_loop(self):
        """模拟采集数据"""
        while self.running:
            timestamp_now = datetime.datetime.now().timestamp()

            # 模拟 5 个流的拉速和瞬时流量
            current_pull_speeds = np.random.rand(5) * 2.0  # m/min
            stream_values = [{"value": np.random.rand() * 10.0} for _ in range(5)]

            with self.lock:
                for i in range(5):
                    self.pull_speed_queue[i].append((timestamp_now, float(current_pull_speeds[i])))
                    inst_flow = float(sum(v.get('value', 0.0) for v in [stream_values[i]]))
                    self.stream_queue[i].append((timestamp_now, inst_flow))

            # 模拟 6 个参数
            other_data = {
                '结晶器流量': np.random.rand() * 200,
                '结晶器水温差': np.random.rand() * 10,
                '二冷水总管压力': np.random.rand() * 5,
                '结晶器进水温度': np.random.rand() * 50,
                '结晶器水压': np.random.rand() * 2,
                '二冷水总管温度': np.random.rand() * 40,
            }
            with self.lock:
                self.other_queue.append((timestamp_now, dict(other_data)))

            time.sleep(self.sample_interval)

    # ------------------- 关键计算函数 -------------------

    def _calculate_t0(self, cut_signal_ts: float, length: float, pull_speed_queue: deque):
        """计算起始点 t0"""
        total = 28.0 + length * 0.001
        n = len(pull_speed_queue)
        if n < 2:
            return cut_signal_ts, max(0, n - 1)

        times = np.array([t for t, _ in pull_speed_queue], dtype=float)
        speeds = np.array([s for _, s in pull_speed_queue], dtype=float)
        times[-1] = cut_signal_ts  # 对齐到切割信号时间

        dt = times[1:] - times[:-1]
        interval_dis = 0.5 * (speeds[:-1] + speeds[1:]) * dt
        cum = np.concatenate(([0.0], np.cumsum(interval_dis)))
        total_dist = cum[-1]

        suffix = total_dist - cum
        idx_candidates = np.where(suffix >= total)[0]
        if idx_candidates.size:
            idx = int(idx_candidates[0])
            return float(times[idx]), idx

        self.logger.warning("未找到满足条件的t0，使用最早时间点")
        return float(times[0]), 0

    def _calculate_t2(self, t0: float, pull_speed_queue: deque, start_index: int):
        """计算结束点 t2"""
        n = len(pull_speed_queue)
        if n < 2 or start_index >= n:
            return t0, start_index

        times = np.array([t for t, _ in pull_speed_queue], dtype=float)
        speeds = np.array([s for _, s in pull_speed_queue], dtype=float)

        dt = times[1:] - times[:-1]
        interval_dis = 0.5 * (speeds[:-1] + speeds[1:]) * dt
        cum = np.concatenate(([0.0], np.cumsum(interval_dis)))

        diffs = cum - cum[start_index]
        idx_candidates = np.where(diffs >= 12.0)[0]
        if idx_candidates.size:
            idx2 = int(idx_candidates[0])
            return float(times[idx2]), idx2

        self.logger.warning("未达到12m距离，使用最后时间点作为t2")
        return float(times[-1]), n - 1

    def _calculate_data(self, delta_t, index1, index2, stream_index):
        """在 [t0, t2] 区间积分流量 & 6参数均值"""
        with self.lock:
            if not (0 <= index1 < len(self.pull_speed_queue[stream_index])) or not (
                0 <= index2 < len(self.pull_speed_queue[stream_index])
            ):
                return 0.0, [0.0] * 6

            times_pull = [t for t, _ in self.pull_speed_queue[stream_index]]
            t0 = float(times_pull[index1])
            t2 = float(times_pull[index2])
            if t2 < t0:
                t0, t2 = t2, t0

            # 积分流量
            stream_slice = [(ts, val) for ts, val in self.stream_queue[stream_index] if t0 <= ts <= t2]
            if len(stream_slice) == 0 or delta_t <= 0:
                total_stream = 0.0
            else:
                times_stream = np.array([ts - t0 for ts, _ in stream_slice], dtype=float)
                vals_stream = np.array([v for _, v in stream_slice], dtype=float)
                if len(vals_stream) == 1:
                    total_stream = float(vals_stream[0] * (t2 - t0))
                else:
                    total_stream = float(np.trapz(vals_stream, times_stream))

            self.logger.debug(
                f"流{stream_index+1}总流量: {total_stream}（区间[{t0:.2f},{t2:.2f}]秒，样本{len(stream_slice)}个）"
            )

            # 六个参数均值
            other_params = [
                '结晶器流量',
                '结晶器水温差',
                '二冷水总管压力',
                '结晶器进水温度',
                '结晶器水压',
                '二冷水总管温度',
            ]
            other_slice = [d for ts, d in self.other_queue if t0 <= ts <= t2]
            if not other_slice:
                other_res_list = [0.0] * 6
            else:
                other_res_list = []
                for param in other_params:
                    vals = [d.get(param, 0.0) for d in other_slice if isinstance(d, dict)]
                    avg = float(sum(vals) / len(vals)) if vals else 0.0
                    other_res_list.append(avg)

            self.logger.debug(f"六个参数平均值分别为 {other_res_list}")
            return total_stream, other_res_list

    # ------------------- 对外接口 -------------------

    def calculate(self, cut_signal_ts: float, length: float, stream_index: int = 4):
        """
        cut_signal_ts: 切割信号的时间戳
        length: 板坯长度 (mm)
        stream_index: 第几个流 (0-4)
        """
        with self.lock:
            if len(self.pull_speed_queue[stream_index]) < 2:
                self.logger.warning("数据不足，无法计算")
                return 0.0, [0.0] * 6

        t0, idx1 = self._calculate_t0(cut_signal_ts, length, self.pull_speed_queue[stream_index])
        t2, idx2 = self._calculate_t2(t0, self.pull_speed_queue[stream_index], idx1)
        delta_t = t2 - t0

        total_stream, other_res_list = self._calculate_data(delta_t, idx1, idx2, stream_index)

        self.logger.info(
            f"流{stream_index+1} 从 t0={t0:.2f} 到 t2={t2:.2f} "
            f"总流量: {total_stream:.3f}, 参数平均: {other_res_list}"
        )
        return total_stream, other_res_list

if __name__ == "__main__":
    print("系统启动...")
    dh = DataHandler()
    dh.conn()
    print("连接尝试完成（请查看日志确认是否成功）")
    try:
        dh.start_data_acquisition()
        # 主线程保持运行，监听 ctrl-c
        while not dh.stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止...")
    finally:
        dh.stop_data_acquisition()
        print("程序已安全退出")
