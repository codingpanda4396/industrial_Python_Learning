import snap7, csv, threading, warnings, time, ctypes
from utils.statepoint import *



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
    """S7Client的封装，提供了一次读取多个DB块的能力"""
    def connect(self, address, rack, slot, tcp_port = 102, retry: bool = True, retry_times: int = 10, max_stay: int = 300):
        if bool(retry) == False:#不进行重试
            return super().connect(address, rack, slot, tcp_port)
        
        stay = 1#重试间隔   
        while retry_times == 0 or retry_times > 1:
            try:
                return super().connect(address, rack, slot, tcp_port)
            except:
                if retry_times > 1:
                    retry_times -= 1#--重试次数
                time.sleep(stay)
                stay *= 2#指数退避策略
                if stay > max_stay:#限制最大重试间隔
                    stay = max_stay
        
        return super().connect(address, rack, slot, tcp_port)

    def multi_db_read_py(self, db_number: list, start: list, size: list):
        """一次性读取多个DB块的不同区域
        """
        count = len(size)
        buffers = [ctypes.create_string_buffer(i) for i in size]
        params = []
        for i in range(count):
            params.append(TS7DataItem(snap7.type.Areas.DB, snap7.type.WordLen.Byte, 0, db_number[i], start[i], size[i], ctypes.cast(buffers[i], ctypes.c_void_p)))
        
        array_type = TS7DataItem * count
        param_array = array_type(*params)
        result = self.read_multi_vars(param_array)
        if result[0]:
            raise RuntimeError("多组读取失败")
        
        res_rtn = [bytearray(i) for i in buffers]
        return res_rtn

class S7data:
    """负责从CSV文件加载数据点配置、管理PLC连接、组织数据读取、解析数据类型，并通过多线程实现数据的自动更新和变化监听。"""
    def __init__(self, csvfile):
        self.logger = None

        self.S7Client = None
        self.lock = threading.Lock()
        self.thread_run = False
        self.threads = []
        self.nodes = {} 
        self.node_data = {} 
        self.groups = {}  
        self.target_from_name = {}

        with open(csvfile) as f: # 使用上下文管理器打开CSV文件，确保文件正确关闭[6,7](@ref)
            for i in csv.DictReader(f): # 使用csv.DictReader逐行读取CSV文件，每行数据自动转换为字典形式，键为CSV的列头[6,8](@ref)
                if i['name'] in self.nodes: # 检查当前行的节点名称是否已存在于已有的节点字典中
                    raise Exception(f"S7配置文件节点名称重复：{i['name']}") # 如果节点名称重复，抛出异常，提示重复的节点名称
                else:
                    self.nodes[i['name']] = i # （K->行name V->本行数据）
                    self.node_data[i['name']] = bytearray(int(i['size']))#（key->行name V—>按size创建的bytearray）
                    if i['group'] not in self.groups: 
                        self.groups[i['group']] = [] #如果还没有该组，创建新组
                    self.groups[i['group']].append(i['name']) #将当前行name添加进对应的组

    def set_logger(self, logger):
        self.logger = logger

    def set_S7Client(self, s7c: S7Client):
        self.S7Client = s7c

    def get_S7Client(self):
        return self.S7Client
    
    def get_value(self, name):
        """负责将 bytearray原始数据根据配置的 type解析成有意义的Python数据类型"""
        if len(name) > 3 and name[-3] == '[' and name[-1] == ']' and name[-2].isdigit() and 0 <= int(name[-2]) < 8:
            index = int(name[-2])
            name = name[:-3]
            data = (self.node_data[name][0] >> index) & 1
        elif self.nodes[name]['type'] == 'int':
            data = snap7.util.get_int(self.node_data[name], 0)
        elif self.nodes[name]['type'] == 'dint':
            data = snap7.util.get_dint(self.node_data[name], 0)
        elif self.nodes[name]['type'] == 'bool':
            data = snap7.util.get_bool(self.node_data[name], 0, int(self.nodes[name]['offset']))
        elif self.nodes[name]['type'] == 'boollist':
            data = [(self.node_data[name][0] >> i) & 1 for i in range(8)]
        elif self.nodes[name]['type'] == 'real':
            data = snap7.util.get_real(self.node_data[name], 0)
        elif self.nodes[name]['type'] == 'string':
            data = self.node_data[name][2:2+int.from_bytes(self.node_data[name][1:2])].decode('gbk', errors='replace')
        elif self.nodes[name]['type'] == 'wstring':
            data = self.node_data[name][4:].decode(encoding='utf-16be', errors='replace')
        else:
            warnings.warn('暂不支持的类型：' + self.nodes[name]['type'])
            if self.logger:
                self.logger.error('暂不支持的类型：' + self.nodes[name]['type'])
            return None
        
        return data

    def send(self, name):
        """数据更新后自动调用，将其注入到StatePoint"""
        if self.nodes[name]['type'] == 'int':
            data = snap7.util.get_int(self.node_data[name], 0)
        elif self.nodes[name]['type'] == 'dint':
            data = snap7.util.get_dint(self.node_data[name], 0)
        elif self.nodes[name]['type'] == 'bool':
            data = snap7.util.get_bool(self.node_data[name], 0, int(self.nodes[name]['offset']))
        elif self.nodes[name]['type'] == 'boollist':
            data = [(self.node_data[name][0] >> i) & 1 for i in range(8)]
        elif self.nodes[name]['type'] == 'real':
            data = snap7.util.get_real(self.node_data[name], 0)
        elif self.nodes[name]['type'] == 'string':
            data = self.node_data[name][2:2+int.from_bytes(self.node_data[name][1:2])].decode('gbk', errors='replace')
        elif self.nodes[name]['type'] == 'wstring':
            data = self.node_data[name][4:].decode(encoding='utf-16be', errors='replace')
        elif self.nodes[name]['type'] == 'int_list':
            data = []
            for i in range(0, int(self.nodes[name]['size']), 2):
                data.append(snap7.util.get_int(self.node_data[name], i))
        else:
            warnings.warn('暂不支持的类型：' + self.nodes[name]['type'])
            if self.logger:
                self.logger.error('暂不支持的类型：' + self.nodes[name]['type'])
            return None

        if name in self.target_from_name:
            for i in self.target_from_name[name]:
                i.inject(data)
        if self.nodes[name]['type'] == 'boollist' and name + '*' in self.target_from_name:
            for i in range(8):
                for j in self.target_from_name[name+'*'][i]:
                    j.inject(data[i])

    def update(self, name):
        """后台线程函数,读取数据并监控其变化"""
        nodeinfo = self.nodes[name]
        try:
            while True:
                if not self.thread_run:
                    return None
                self.lock.acquire()
                if not self.S7Client.get_connected():
                    warnings.warn('S7Client连接中断')
                    if self.logger:
                        self.logger.error('S7Client连接中断')
                    self.thread_run = False
                    self.lock.release()
                    return None
                tmp = self.S7Client.db_read(int(nodeinfo['db']), int(nodeinfo['start']), int(nodeinfo['size']))
                self.lock.release()
                if self.node_data[name] != tmp:
                    self.node_data[name] = tmp#如果数据发生变化，覆盖旧数据
                    self.send(name)
                time.sleep(float(nodeinfo['frequency']) / 1000)
        except RuntimeError as reason:
            warnings.warn(reason)
            if self.logger:
                self.logger.error(reason)
            self.thread_run = False
            self.lock.release()

    def start_auto_update(self):
        """启动自动更新所有允许读取的PLC节点的线程"""
        if self.thread_run:
            return None
        self.threads = []
        if self.S7Client == None:
            warnings.warn('未初始化S7Client')
            if self.logger:
                self.logger.error('未初始化S7Client')
            return None
        if not self.S7Client.get_connected():
            warnings.warn('S7Client未连接')
            if self.logger:
                self.logger.error('S7Client未连接')
            return None
        for key, value in self.nodes.items():
            if value['read_allow'].upper() != 'FALSE':
                self.threads.append(threading.Thread(target=self.update, args=(value['name'],)))
        self.thread_run = True
        for i in self.threads:
            i.start()

    def update_group(self, group_name):
        nodesname = self.groups[group_name]#获取该组下所有行name
        db_number = []
        start = []
        size = []

        #遍历组内数据点
        for name in nodesname:
            nodeinfo = self.nodes[name]#获取代表行的字典
            #湖区db_number start size三个字段
            db_number.append(int(nodeinfo['db']))
            start.append(int(nodeinfo['start']))
            size.append(int(nodeinfo['size']))

        while True:
            if not self.thread_run:
                return None
            
            tmp = False
            read_valid = True
            with self.lock:
                if not self.S7Client.get_connected():
                    warnings.warn('S7Client连接中断')
                    if self.logger:
                        self.logger.error('S7Client连接中断')
                    self.thread_run = False
                    return None

                try:
                    tmp = self.S7Client.multi_db_read_py(db_number, start, size)
                except RuntimeError as reason:
                    warnings.warn(reason)
                    read_valid = False
                    if self.logger:
                        self.logger.error(reason)
                    self.thread_run = False

            if read_valid and tmp:
                for i in range(len(tmp)):
                    if self.node_data[nodesname[i]] != tmp[i]:
                        self.node_data[nodesname[i]] = tmp[i]
                        self.send(nodesname[i])

    def auto_update_group(self):
        """使用多线程自动更新所有设备组的数据"""
        if self.thread_run:
            return None
        self.threads = []
        if self.S7Client == None:
            warnings.warn('未初始化S7Client')
            if self.logger:
                self.logger.error('未初始化S7Client')
            return None
        if not self.S7Client.get_connected():
            warnings.warn('S7Client未连接')
            if self.logger:
                self.logger.error('S7Client未连接')
            return None
        
        for group in self.groups.keys():
            self.threads.append(threading.Thread(target=self.update_group, args=(group,)))

        self.thread_run = True
        for i in self.threads:
            i.start()

    def end_auto_update(self):
        self.thread_run = False
        for i in self.threads:
            i.join()

    def make_point(self, name, point_type = Statepoint):
        index = -1  
        solvedname = name
        if len(name) > 3 and name[-3] == '[' and name[-1] == ']' and name[-2].isdigit() and 0 <= int(name[-2]) < 8:
            index = int(name[-2])
            name = name[:-3]
            solvedname = name + '*'
        if name not in self.nodes:
            raise ValueError("创建了未配置的点")

        if solvedname not in self.target_from_name:
            if index == -1:
                self.target_from_name[solvedname] = []
            else:
                self.target_from_name[solvedname] = [[],[],[],[],[],[],[],[]]
                
        res = point_type()
        if index == -1:
            self.target_from_name[solvedname].append(res)
        else:
            self.target_from_name[solvedname][index].append(res)
        self.send(name)
        return res
