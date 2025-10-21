from utils.statepoint import Statepoint
from pylogix import PLC
from pylogix.lgx_response import Response
from threading import Thread
import time

class CIPData:
    __sentinel = object()

    def __init__(self, ip = ''):
        self.tags2name = {
            "GB_PEISHUI": [f"5#水流量-{i}流-{j}段" for i in range(1, 9) for j in range(1, 6)],
            "GB_PEISHUI[58]": ['5#结晶器流量', '5#结晶器水温差', '5#二冷水总管压力', '5#结晶器进水温度', '5#结晶器水压', '5#二冷水总管温度']
        }#PLC标签 : 有意义的名称

        self.name2value = {j: 0 for i in self.tags2name.vwalues() for j in i}#缓存所有名称的当前值

        self.name2point = {}

        self.plc_ip = ip
        self.thread_update = None
        self.thread_run = False

    def deliver_value(self, name, value):
        if self.get_value(name) == value:
            return None
        
        self.name2value[name] = value

        if name in self.name2point:
            for point in self.name2point[name]:
                point.inject(value)

    def process_response(self, response: Response, name: str | list[str]):
        if response.Status == "Success":
            if isinstance(name, list):
                _ = [self.deliver_value(name[i], response.Value[i]) for i in range(len(name))]
            else:
                self.deliver_value(name, response.Value)
        else:
            print("Error:", response.Status)

    def update_forever(self, sleep_second = 0.5):
        ip = self.plc_ip
        if ip == '':
            raise ValueError("PLC IPAddress is not defined.")

        retry_count = 3
        with PLC(ip) as plc:
            while retry_count > 0 and self.thread_run:
                try:
                    for tag, name in self.tags2name.items():
                        if isinstance(name, list):
                            ret = plc.Read(tag, len(name))
                        else:
                            ret = plc.Read(tag)
                        self.process_response(ret, name)
                    retry_count = 3
                except:
                    retry_count -= 1
                finally:
                    time.sleep(sleep_second)
        self.thread_run = False
        if retry_count <= 0:
            print("An abnormal connection with the PLC occurred.")

    def start_update(self):
        """启动后台线程持续读取PLC数据并更新本地缓存"""
        if self.thread_update or self.thread_run:
            raise ChildProcessError("This thread cannot be started now.")
        
        self.thread_update = Thread(target=self.update_forever)
        self.thread_run = True
        self.thread_update.start()

    def stop_update(self):
        self.thread_run = False
        if self.thread_update == None:
            return None
        
        self.thread_update.join()
        self.thread_update = None

    def restart_update(self):
        self.stop_update()
        self.start_update()

    def get_value(self, name: str, default: any = __sentinel):
        if name not in self.name2value:
            if default is self.__sentinel:
                raise NameError(f"Name {name} is not defined.")
            else:
                return default
        
        return self.name2value[name]

    def make_point(self, name: str, point_t = Statepoint):
        point = point_t(self.get_value(name))

        if name not in self.name2point:
            self.name2point[name] = set()

        self.name2point[name].add(point)

        return point