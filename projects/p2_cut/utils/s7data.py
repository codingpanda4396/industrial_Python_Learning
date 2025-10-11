import snap7, csv, threading, warnings, time, ctypes
from utils.StatePoint import *

class TS7DataItem(ctypes.Structure):
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
    def multi_db_read_py(self, db_number: list, start: list, size: list):
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
        with open(csvfile) as f:
            for i in csv.DictReader(f):
                if i['name'] in self.nodes:
                    raise Exception(f"S7配置文件节点名称重复：{i['name']}")
                else:
                    self.nodes[i['name']] = i
                    self.node_data[i['name']] = bytearray(int(i['size']))
                    if i['group'] not in self.groups:
                        self.groups[i['group']] = []
                    self.groups[i['group']].append(i['name'])

    def set_logger(self, logger):
        self.logger = logger

    def set_S7Client(self, s7c: S7Client):
        self.S7Client = s7c

    def get_S7Client(self):
        return self.S7Client
    
    def get_value(self, name):
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
                    self.node_data[name] = tmp
                    self.send(name)
                time.sleep(float(nodeinfo['frequency']) / 1000)
        except RuntimeError as reason:
            warnings.warn(reason)
            if self.logger:
                self.logger.error(reason)
            self.thread_run = False
            self.lock.release()

    def start_auto_update(self):
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
        nodesname = self.groups[group_name]
        db_number = []
        start = []
        size = []

        for name in nodesname:
            nodeinfo = self.nodes[name]
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
