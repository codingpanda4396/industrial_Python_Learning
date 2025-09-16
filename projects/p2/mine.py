from collections import deque
import random
from time import perf_counter, sleep
import snap7
import snap7.util
from threading import Thread, Lock

calculating = True

def conn():
    plc = snap7.client.Client()
    global calculating
    ip_address = '127.0.0.1'  # 本地回环地址
    rack = 0
    slot = 1

    try:
        print("正在连接PLC...")
        plc.connect(ip_address, rack, slot)
        lock = Lock()

        if plc.get_connected():
            print("成功连接到PLC Server")

            # 启动模拟线程（写入DB）
            Thread(target=simulate, args=(lock, plc), daemon=True).start()

            # 等待并计算
            cut_ts, enter_ts, t3 = calculation(plc, lock)

            if cut_ts is not None and enter_ts is not None and t3 is not None:
                print(f"切割时刻: {cut_ts:.2f} s")
                print(f"进入时刻: {enter_ts:.2f} s")
                print(f"12m 处时刻: {t3:.2f} s")
                print(f"钢坯在生产线上行走时间: {cut_ts - enter_ts:.2f} s")
            else:
                print("未能计算出进入时刻或12m时刻（可能历史数据不足或单位不匹配）。")
        else:
            print("PLC连接失败")
    except Exception as e:
        print("主线程异常：", e)
    finally:
        # 结束标志，停止模拟线程
        calculating = False
        try:
            plc.disconnect()
            plc.destroy()
        except Exception:
            pass
        print("连接已断开")


# 模拟切割信号、拉速、定尺
def simulate(lock: Lock, plc: snap7.client.Client):
    cut_signal = False
    cut_counter = 0
    data_to_write = bytearray(10)

    while calculating:
        # 模拟拉速 (m/min)
        pull_speed = 3.0 + random.uniform(-0.5, 0.5)
        cut_counter += 1
        if cut_counter > 30:  # ~3s 翻转一次
            cut_signal = not cut_signal
            cut_counter = 0

        # 这里写入一个定尺示例：11770 （假设是 mm）
        with lock:
            snap7.util.set_real(data_to_write, 0, pull_speed)
            snap7.util.set_bool(data_to_write, 4, 0, cut_signal)
            snap7.util.set_dword(data_to_write, 6, 11770)
            try:
                plc.db_write(1, 0, data_to_write)
                print("成功写入plc")
            except Exception as e:
                print("写PLC失败：", e)
        sleep(0.5)

def calculation(plc, lock: Lock):
    """
    计算切割时刻 t2、进入时刻 t0 和 12m 处时刻 t3
    """
    data_hist = deque(maxlen=2000)  # 存历史 (ts, v, cut, Lcut)
    prev_cut = False
    Lcaster = 28.0  # 28m

    while calculating:
        with lock:
            try:
                data = plc.db_read(1, 0, 10)
                v = snap7.util.get_real(data, 0)  # 拉速 (m/s)
                cut = snap7.util.get_bool(data, 4, 0)
                Lcut = snap7.util.get_dword(data, 6) / 1000.0  # mm→m
            except Exception as e:
                print("读PLC失败：", e)
                sleep(0.1)
                continue

        ts = perf_counter()
        data_hist.append((ts, v, cut, Lcut))#从t1开始到t2的所有采样都被存入队列

        # 检测切割信号上升沿
        if (not prev_cut) and cut:
            #t2 = ts
            #print(f"检测到切割信号，上升沿时刻 {t2:.2f}s")
            # 开始回溯积分
            Sneed = Lcaster + Lcut  # 需要回溯的距离
            S = 0.0
            enter_ts = None

            # 倒序遍历历史数据->t2开始往前，从队列中取出每一次采样的信息，积分直到总位移==28+定尺
            for i in range(len(data_hist)-1, 0, -1):
                ts1, v1, _, _ = data_hist[i-1] 
                ts2_, v2, _, _ = data_hist[i]  
                dt = ts2_ - ts1  #段时间
                vavg = 0.5 * (v1 + v2)#段内平均速度
                ds = vavg * dt #产生的位移
                S += ds        #累加段位移
                if S >= Sneed:
                    # 在 [ts1, ts2_] 区间内找精确进入时刻
                    extra = S - Sneed   #当前段多加的距离
                    frac = (ds - extra) / ds if ds > 0 else 0#这段内所需的位移占整段位移的比例
                    enter_ts = ts1 + frac * dt #比例*dt得到这段实际需要的时间
                    break

            if enter_ts is not None:
                print(f"进入时刻 t0={enter_ts:.2f}s")

                # 计算12m时刻
                S12 = 0.0
                t3 = None
                for i in range(len(data_hist)):
                    ts1, v1, _, _ = data_hist[i]
                    if ts1 < enter_ts:#跳过t0之前的数据
                        continue
                    if i+1 >= len(data_hist):
                        break
                    ts2_, v2, _, _ = data_hist[i+1]
                    dt = ts2_ - ts1
                    vavg = 0.5 * (v1 + v2)
                    ds = vavg * dt
                    S12 += ds
                    if S12 >= 12.0:
                        extra = S12 - 12.0
                        frac = (ds - extra) / ds if ds > 0 else 0
                        t3 = ts1 + frac * dt
                        break

                if t3:
                    print(f"12m 处时刻 t3={t3:.2f}s")
                return t2, enter_ts, t3
            else:
                print("历史数据不足，无法推算进入时刻。")

        prev_cut = cut
        sleep(0.05)  # 控制采样周期
    return None, None, None




if __name__ == "__main__":
    conn()
