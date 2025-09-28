from utils.statepoint import Statepoint
from models.data_sender import Sender
import numpy as np
from scipy import interpolate, integrate
from collections import deque
from models.cip_data import CIPData
from utils.s7data import S7data
import datetime, logging, time, threading, queue

class BufferPoint(Statepoint):
    def __init__(self, initvalue = None, initstate = False, maxlen: int | None = 3000):
        super().__init__(deque(maxlen = maxlen), initstate)

    def inject(self, data):
        self.data.append((data, datetime.datetime.now().timestamp()))

    def get_buffer(self):
        res = self.data.copy()
        last = res[-1][0]
        res.append((last, datetime.datetime.now().timestamp() + 0.001))
        return res

class billet_data_gatherer:
    """钢坯数据采集者"""
    def __init__(self, dspeed_point: BufferPoint, cutting_sig_point: Statepoint, sizing_point: Statepoint, flow_rate_point_list: list[BufferPoint],
                 logger: logging.Logger, strand_no: int, result_queue: queue.Queue):
        self.dspeed_point = dspeed_point
        self.cutting_sig_point = cutting_sig_point
        self.sizing_point = sizing_point
        self.flow_rate_point_list = flow_rate_point_list
        self.logger = logger
        self.strand_no = strand_no
        self.result_queue = result_queue

        self.MOLD_TO_CUTTER_DISTANCE = 28
        self.CRITICAL_ZONE_LENGTH = 12

        self.cutting_sig_point.set_excite_action(self.cutting_action)
        
    def cutting_action(self):
        cutting_time = datetime.datetime.now().timestamp()
        sizing = self.sizing_point.data / 1000 #mm转换为m

        self.logger.debug(f"{self.strand_no}流开始切割")

        time.sleep(30)#确保数据采集完整
        dspeed_buffer: deque = self.dspeed_point.get_buffer()
        flow_rate_buffer_list: list[deque] = [self.flow_rate_point_list[i].get_buffer() for i in range(5)]

        if len(dspeed_buffer) < 10:
            self.logger.debug(f"{self.strand_no}流已统计数据量不足，无法计算")
            return

        data_tuple, time_tuple = zip(*dspeed_buffer)

        x = np.array(time_tuple) #时间数组
        y = np.array(data_tuple) / 60 #拉速转换为m/s
        vt_func = interpolate.interp1d(x, y, kind='cubic')#三次样条插值
        entry_time = self._binary_search_start(vt_func, cutting_time, sizing + self.MOLD_TO_CUTTER_DISTANCE)#头部进入结晶器

        if entry_time == None:
            self.logger.debug(f"{self.strand_no}流已统计数据量不足，无法计算")
            return
        
        exit_time = self._binary_search_end(vt_func, entry_time, sizing + self.CRITICAL_ZONE_LENGTH)#尾部离开结晶器
        dspeed_avg = (sizing + self.CRITICAL_ZONE_LENGTH) / (exit_time - entry_time) * 60

        self.create_data(cutting_time, entry_time, exit_time, self.flow_rate_total(flow_rate_buffer_list, entry_time, exit_time), dspeed_avg)
        
    def _binary_search_start(self, func, upper_limit, target):
        """二分查找计算钢坯进入关键区域时间
        func：速度-时间插值函数
        upper_limit：切割时间戳（搜索范围上限）

        """
        left = func.x.min()
        right = func.x.max()

        if self._get_distance(func, left, upper_limit) < target:
            return

        while abs(right - left) > 0.01:
            mid = (left + right) / 2
            if self._get_distance(func, mid, upper_limit) >= target:
                left = mid
            else:
                right = mid
        
        return (left + right) / 2
    
    def _binary_search_end(self, func, lower_limit, target):
        left = func.x.min()
        right = func.x.max()

        while abs(right - left) > 0.01:
            mid = (left + right) / 2
            if self._get_distance(func, lower_limit, mid) >= target:
                right = mid
            else:
                left = mid
        
        return (left + right) / 2

    def _get_distance(self, vt_func, lower, upper):
        """通过积分计算移动距离"""
        return integrate.quad(vt_func, lower, upper)[0]
    
                                #五段流量队列
    def flow_rate_total(self, deque_list: list[deque], start_time, end_time):
        res = []
        for dequei in deque_list:
            data_tuple, time_tuple = zip(*dequei)
            x = np.array(time_tuple)
            y = np.array(data_tuple) / 3600
            if len(x) < 4:
                avg = np.mean(y)
                vt_func = lambda xx: avg
            else:
                vt_func = interpolate.interp1d(x, y, kind='cubic')
            total = integrate.quad(vt_func, start_time, end_time)[0]
            res.append(total)

        return sum(res)
    
    def create_data(self, cutting_time, entry_time, exit_time, water_total, dspeed_avg):
        self.logger.debug(f"{self.strand_no}流钢坯计算结果：")
        self.logger.debug(f'\t切割时间：{datetime.datetime.fromtimestamp(cutting_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t进入时间：{datetime.datetime.fromtimestamp(entry_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t离开时间：{datetime.datetime.fromtimestamp(exit_time).strftime("%Y-%m-%d %H:%M:%S")}')
        self.logger.debug(f'\t水量总计：{water_total}')
        self.logger.debug(f'\t平均拉速：{dspeed_avg}')
        self.result_queue.put((self.strand_no, float(cutting_time), float(entry_time), float(exit_time), float(water_total), float(dspeed_avg)))

class SteelFit:
    """拟合模块"""
    def __init__(self, s7_data_20: S7data, s7_data_215: S7data, cip_data: CIPData, sender: Sender, logger: logging.Logger):
        self.water_temperature_buffer: BufferPoint = cip_data.make_point("5#二冷水总管温度", BufferPoint)
        self.water_pressure_buffer: BufferPoint = cip_data.make_point("5#二冷水总管压力", BufferPoint)
        self.steel_temperature_buffer: BufferPoint = s7_data_20.make_point("中间包连续测温温度", BufferPoint)
        self.water_temperature_difference_buffer: BufferPoint = cip_data.make_point("5#结晶器水温差", BufferPoint)

        self.dspeed_buffer = [s7_data_20.make_point(f"{i}流结晶器拉速", BufferPoint) for i in range(1, 9)]
        self.cutting_sig_point = [s7_data_215.make_point(f"L{i}切割信号[0]") for i in range(1, 9)]
        self.sizing_point = [s7_data_20.make_point(f"{i}流定尺") for i in range(1, 9)]
        self.flow_rate_point_list = [[cip_data.make_point(f"5#水流量-{i}流-{j}段", BufferPoint) for j in range(1, 6)] for i in range(1, 9)]

        self.sender = sender
        self.logger = logger
        self.task_queue = queue.Queue()

        self.billet_data_gatherer_list = [
            billet_data_gatherer(
                self.dspeed_buffer[i],
                self.cutting_sig_point[i],
                self.sizing_point[i],
                self.flow_rate_point_list[i],
                logger,
                i + 1,
                self.task_queue
            )
            for i in range(8)
        ]
        
        self.thread_run = True
        self.thread = threading.Thread(target=self.loop_process)
        self.thread.start()

    def loop_process(self):
        while self.thread_run:
            try:
                task_tuple = self.task_queue.get(True, 1)
                tmp_dict = {}
                tmp_dict["strand_no"] = task_tuple[0]
                tmp_dict["cutting_time"] = datetime.datetime.fromtimestamp(task_tuple[1])
                tmp_dict["entry_time"] = datetime.datetime.fromtimestamp(task_tuple[2])
                tmp_dict["exit_time"] = datetime.datetime.fromtimestamp(task_tuple[3])
                
                cal_res = self.cal_data(task_tuple[2], task_tuple[3])
                tmp_dict["water_temperature"] = cal_res[0]
                tmp_dict["water_pressure"] = cal_res[1]
                tmp_dict["water_volume"] = task_tuple[4]
                tmp_dict["water_pressure_sd"] = cal_res[2]
                tmp_dict["steel_temperature"] = cal_res[3]
                tmp_dict["drawing_speed"] = task_tuple[5]
                tmp_dict["water_temperature_difference"] = cal_res[4]

                self.sender.upload_billet(tmp_dict)
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error(f"铸机数据计算过程中出现意外:{e}")

    def cal_data(self, entry_time, exit_time):
        wt = self.interval_avg(self.water_temperature_buffer.get_buffer(), entry_time, exit_time)
        wp = self.interval_avg(self.water_pressure_buffer.get_buffer(), entry_time, exit_time)
        wps = self.interval_sd(self.water_pressure_buffer.get_buffer(), entry_time, exit_time)
        st = self.interval_avg(self.steel_temperature_buffer.get_buffer(), entry_time, exit_time)
        wtd = self.interval_avg(self.water_temperature_difference_buffer.get_buffer(), entry_time, exit_time)

        return (float(wt), float(wp), float(wps), float(st), float(wtd))

    def interval_avg(self, buffer, left, right):
        data_tuple, time_tuple = zip(*buffer)
        x = np.array(time_tuple)
        y = np.array(data_tuple)
        func = interpolate.interp1d(x, y, kind = "cubic")
        inte = integrate.quad(func, left, right)[0]

        return inte / (right - left)

    def interval_sd(self, buffer, left, right):
        data_tuple, time_tuple = zip(*buffer)
        x = np.array(time_tuple)
        y = np.array(data_tuple)
        func = interpolate.interp1d(x, y, kind = "cubic")
        inte = integrate.quad(func, left, right)[0]
        avg = inte / (right - left)

        func2 = lambda x: (func(x) - avg) ** 2
        inte2 = integrate.quad(func2, left, right)[0]
        avg2 = inte2 / (right - left)

        return avg2 ** 0.5


if __name__ == "__main__":
    from utils.s7data import S7Client, S7data
    from utils.logger import Logger

    # 配置S7连接
    s7_1 = S7Client()
    s7_1.connect("172.16.1.20", 0, 0)
    data_1 = S7data("conf/s7@172.16.1.20.csv")
    data_1.set_S7Client(s7_1)
    data_1.auto_update_group()
    
    s7_2 = S7Client()
    s7_2.connect("172.16.1.21", 0, 0)
    data_2 = S7data("conf/s7@172.16.1.21.csv")
    data_2.set_S7Client(s7_2)
    data_2.auto_update_group()

    s7_3 = S7Client()
    s7_3.connect("192.168.1.215", 0, 0)
    data_3 = S7data("conf/s7@192.168.1.215.csv")
    data_3.set_S7Client(s7_3)
    data_3.auto_update_group()

    # 配置CIP连接
    cip_data = CIPData("192.168.3.100")
    cip_data.start_update()
    
    # 配置日志模块
    logger = Logger('test')
    logger.screen_on()

    class C:
        def upload_billet(self, arg_dict: dict):
            pass

    # 钢坯拟合模块
    steel_fit = SteelFit(data_1, data_3, cip_data, C(), logger)
