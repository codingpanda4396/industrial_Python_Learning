import snap7
import numpy as np
import time
from threading import Thread, Lock
import random

# 配置Snap7 Server
server = snap7.server.Server()
server.start(tcp_port=1102)  # 在端口1102上启动服务器

# 定义存储区大小和DB编号
DB_SIZE = 1024  # 数据块的大小
DB_NUMBER = 1  # 数据块编号

# 初始化PLC数据存储区 (使用字节数组)
db_data = bytearray(DB_SIZE)
# 创建一个锁对象来保护对db_data的并发访问
db_data_lock = Lock()

# 模拟参数
BASE_SPEED = 3.0  # 基础拉速，单位 m/min
SPEED_FLUCTUATION = 0.1  # 拉速波动幅度，单位 m/min
CUT_SIGNAL_INTERVAL = 30  # 模拟切割信号变化的间隔时间，单位秒

# 标记，用于控制线程
calculating = True

# --- 定义Server的回调函数 ---
def read_callback(_user_data, _sender, _area, _db_number, _start, _size):
    """
    当客户端请求读取数据时，Server会调用此函数。
    返回请求的数据。
    """
    global db_data, db_data_lock
    # 计算请求结束的索引
    end_index = _start + _size
    if end_index > len(db_data):
        end_index = len(db_data)  # 防止越界
        _size = end_index - _start  # 调整有效读取大小
    # 加锁以确保在读取数据时数据不会被修改
    with db_data_lock:
        return db_data[_start:end_index]  # 返回请求的数据切片


    """
    当客户端请求写入数据时，Server会调用此函数。
    将客户端发送的数据写入到我们的数据存储中。
    """
    global db_data, db_data_lock
    # 计算请求结束的索引
    end_index = _start + _size
    if end_index > len(db_data):
        end_index = len(db_data)  # 防止越界
        _size = end_index - _start  # 调整有效写入大小
    # 加锁以确保在写入数据时数据的一致性
    with db_data_lock:
        db_data[_start:end_index] = _data[:_size]  # 将接收到的数据写入指定位置
    return 0  # 返回0表示成功

# --- 向Server注册回调函数 ---
# 设置Server的回调函数，这里主要处理DB区的读写
server.set_read_events_callback(read_callback)

def update_plc_data():
    """模拟更新PLC数据（拉速、切割信号、定尺）"""
    global db_data, db_data_lock
    cut_signal = 0
    cut_counter = 0

    while calculating:
        # 模拟拉速在基础值附近随机波动
        current_speed = BASE_SPEED + random.uniform(-SPEED_FLUCTUATION, SPEED_FLUCTUATION)
        # 模拟切割信号每隔一段时间变化一次
        cut_counter += 1
        if cut_counter >= CUT_SIGNAL_INTERVAL:
            cut_signal = 1 if cut_signal == 0 else 0
            cut_counter = 0

        # 将数据打包到字节数组中
        # 假设拉速（浮点数，4字节）存储在地址0-3，切割信号（1字节）存储在地址4，定尺（整数，4字节）存储在地址5-8
        # 注意：使用锁保护对共享数据 db_data 的写操作
        with db_data_lock:
            snap7.util.set_real(db_data, 0, current_speed)  # 拉速 (m/min)
            snap7.util.set_int(db_data, 4, cut_signal)      # 切割信号 (0 or 1)
            snap7.util.set_dword(db_data, 8, 11770)         # 定尺 (mm)


        time.sleep(0.1)  # 每100ms更新一次数据

def calculate_time_to_12m():
    """通过积分拉速计算达到12米位移所需的时间"""
    global db_data, db_data_lock # 声明使用全局变量
    sampled_speeds = []  # 存储采样到的拉速值
    sampled_times = []   # 存储采样时间点
    cumulative_distance = 0.0  # 累计位移
    delta_t = 0.1  # 采样时间间隔，单位秒 (100ms)
    integration_step = 0  # 积分步数

    print("开始采集拉速数据并进行积分计算...")
    print("采样时间间隔 Δt = {} 秒".format(delta_t))

    while cumulative_distance < 12.0:  # 目标位移12米
        # 直接访问（加锁保护）我们维护的 db_data 字节数组
        with db_data_lock:
            current_speed = snap7.util.get_real(db_data, 0)  # 当前拉速，单位 m/min
        current_speed_m_s = current_speed / 60.0  # 转换为 m/s

        # 记录当前时间和拉速
        current_time = integration_step * delta_t
        sampled_times.append(current_time)
        sampled_speeds.append(current_speed_m_s)  # 使用m/s为单位进行积分

        # 进行数值积分（梯形法则）
        if integration_step > 0:
            # 计算当前时间步的位移增量
            delta_x = 0.5 * (sampled_speeds[-2] + sampled_speeds[-1]) * delta_t#（上底+下底）*h
            cumulative_distance += delta_x

        integration_step += 1
        time.sleep(delta_t)  # 等待下一个采样周期

    # 计算精确时间T (代码保持不变)
    time_before = sampled_times[-2]
    time_after = sampled_times[-1]
    dist_before = cumulative_distance - 0.5 * (sampled_speeds[-2] + sampled_speeds[-1]) * delta_t
    dist_after = cumulative_distance

    exact_time = time_before + (12.0 - dist_before) * (delta_t) / (dist_after - dist_before)

    print("\n=== 计算结果 ===")
    print(f"达到12米位移所需时间 T ≈ {exact_time:.2f} 秒")
    print(f"达到12米位移所需时间 T ≈ {exact_time/60:.2f} 分钟")
    print(f"总共进行了 {integration_step} 次采样")
    print(f"结束时的累计位移: {cumulative_distance:.4f} 米")
    print(f"结束时的实时拉速: {current_speed:.2f} m/min")

# 启动线程模拟PLC数据更新
data_thread = Thread(target=update_plc_data)
data_thread.daemon = True
data_thread.start()

# 等待Server启动并有一些数据
time.sleep(2)

# 开始计算
try:
    calculate_time_to_12m()
except KeyboardInterrupt:
    print("\n用户中断计算。")
finally:
    calculating = False
    server.stop()
    print("Snap7 Server 已停止。")