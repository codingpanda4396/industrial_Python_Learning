import ctypes
import time
import snap7

class TS7DataItem(ctypes.Structure):
    """结构体 描述数据项的区域、类型、起始地址、数据长度等属性"""
    _fields_ = [
        ('Area', ctypes.c_int),
        ('WordLen', ctypes.c_int),
        ('Result', ctypes.c_int),
        ('DBNumber', ctypes.c_int),
        ('Start', ctypes.c_int),
        ('Amount', ctypes.c_int),
        ('pdata', ctypes.c_void_p)
    ]


class S7Client(snap7.client.Client):
    def connect(self,address,rack,slot,tcp_port=102,retry:bool=True,retry_times:int=10,max_wait:int=300):
        """
        尝试连接到西门子S7 PLC，支持重试机制。
        
        参数:
            address: PLC的IP地址
            rack: 机架号
            slot: 槽号
            tcp_port: TCP端口，默认102
            retry: 是否启用重试，默认True
            retry_times: 最大重试次数，0或负数为无限重试，默认10
            max_wait: 最大等待间隔（秒），默认300
            
        异常:
            在非重试模式或重试用尽后，会抛出原始异常
        """
        if not retry:
            return super().connect(address,rack,slot,tcp_port)

        attempt=1        
        wait_time=1#重试间隔
        while retry_times<=0 or attempt<=retry_times:
            try:
                return super().connect(address,rack,slot,tcp_port)
            except Exception as e:
                if retry_times>0 and attempt>=retry_times:
                    raise#超出重试次数->连接失败  
                time.sleep(wait_time)
                
                wait_time = min(wait_time*2,max_wait)
                attempt+=1
    
    def read_multi_dbs(self, db_number: list, start: list, size: list):
        """从多个DB块的不同地址区域读取数据
        params:
        db_number->要读取的DB块编号list
        start->每个DB块中读取的起始字节地址
        size->指定从每个起始地址开始要读取的数据长度（字节数）
        """
        count=len(db_number)
        #为每一个读取请求创建独立缓冲区
        buffers=[ctypes.create_string_buffer(i) for i in size]

        params=[]
        for i in range(count):
            #为每次请求创建一个 TS7DataItem结构体
            params.append(TS7DataItem(
                snap7.type.Areas.DB,
                snap7.type.WordLen.Byte,
                0,
                db_number[i],
                start[i],
                size[i],
                ctypes.cast(buffers[i],ctypes.c_void_p)
            ))
        array_type=TS7DataItem*count
        param_array=array_type(*params)
        result = self.read_multi_vars(param_array)
        if result[0]:
            raise RuntimeError("多组读取失败")
        #将缓冲区中的数据转换为bytearray,此时buffers中已经包含读取到的数据
        res_rtn = [bytearray(i) for i in buffers]
        return res_rtn

class PLCReader:
    def __init__(self):
        pass
    


import logging
from logging.handlers import RotatingFileHandler

class Logger(logging.Logger):
    def __init__(self, name):
        super().__init__(name)

        self.setLevel(level=logging.DEBUG)
        self.format_default = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        self.console = None
        self.handler = None

    def screen_on(self, level=logging.DEBUG, format=None):
        if self.console:
            return None
        
        if format == None:
            #支持自定义格式
            formatter = logging.Formatter(self.format_default)
        else:
            formatter = logging.Formatter(format)

        self.console = logging.StreamHandler()
        self.console.setLevel(level)#支持自定义级别
        self.console.setFormatter(formatter)        
        self.addHandler(self.console)

    def file_on(self, path='log.txt', level=logging.DEBUG, format=None):
        if self.handler:
            return None
        
        if format == None:
            formatter = logging.Formatter(self.format_default)
        else:
            formatter = logging.Formatter(format)

        self.handler = logging.FileHandler(path)
        self.handler.setLevel(level)
        self.handler.setFormatter(formatter)
        self.addHandler(self.handler)

    def file_on_with_rotation(self, path='log.txt', level=logging.DEBUG, format=None, maxBytes=8*1024*1024, backupCount=3):
        if self.handler:
            return None
        
        if format == None:
            formatter = logging.Formatter(self.format_default)
        else:
            formatter = logging.Formatter(format)

        self.handler = RotatingFileHandler(
            path, 
            maxBytes=maxBytes,
            backupCount=backupCount
        )
        self.handler.setLevel(level)
        self.handler.setFormatter(formatter)
        self.addHandler(self.handler)