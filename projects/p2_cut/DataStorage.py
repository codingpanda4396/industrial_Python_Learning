from collections import deque


class DataStorage:
    def __init__(self, stream_count=8, maxlen=2000, logger=None):
        self.stream_count = stream_count #流数
        #拉速队列
        self.pull_speed_queue = [deque(maxlen=maxlen) for _ in range(stream_count)]
        #流量队列
        self.stream_queue = [deque(maxlen=maxlen) for _ in range(stream_count)]
        #其他量队列
        self.other_queue = deque(maxlen=maxlen)
        #记录当前定尺
        self.current_lengths = [0.0] * stream_count
        #记录先前的切割信号
        self.last_cut_signals = [False] * stream_count
        #日志
        self.logger = logger 

    def push_pull_speeds(self, speeds_list):
        """将拉速list存入队列"""
        for i, item in enumerate(speeds_list):
            self.pull_speed_queue[i].append(item)

    def push_streams(self, stream_data):
        """将水流量数据结构解析并存入队列"""
        for i in range(self.stream_count):
            #stream_data->{"流1": {"values": [{"segment": 1, "value": (117.123, 172123213121.12)}]}}
            self.stream_queue[i].append(stream_data[f"流{i+1}"]['values'])
            #加入队列的是->[{"segment": 1, "value": (117.123, 172123213121.12)}]

    def push_other(self, other):
        """其他计算量存入队列"""
        self.other_queue.append(other)