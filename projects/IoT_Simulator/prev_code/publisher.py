import paho.mqtt.client as mqtt
import json
import random
import time
import threading
import signal
import sys
from datetime import datetime

# 配置MQTT client
BROKER = '192.168.56.10'
PORT = 1883
QOS = 1
KEEPALIVE = 60

# 设备类型
DEVICE_TYPES = [
    "sensor", "controller", "actuator", "motor", "conveyor",
    "robot", "pump", "valve", "generator", "compressor"
]

# 全局停止事件
stop_event = threading.Event()

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n接收到中断信号，正在通知所有设备停止...！")
    stop_event.set()
    # 不立即退出，让主线程完成清理

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

def on_connect(client, userdata, flags, rc):
    """连接回调函数"""
    client_id = client._client_id.decode() if client._client_id else "Unknown"
    if rc == 0:
        print(f"{client_id} 连接成功")
    else:
        print(f"{client_id} 连接失败，返回码: {rc}")

def on_publish(client, userdata, mid):
    """发布回调函数（可选）"""
    # print(f"消息 {mid} 已发布")
    pass

def generate_device_data(device_id):
    """生成模拟设备数据"""
    current_time = datetime.now().isoformat()
    device_type = DEVICE_TYPES[int(device_id) % len(DEVICE_TYPES)]

    return {
        "version": "1.0",
        "deviceId": f"device_{device_id:02d}",
        "deviceType": device_type,
        "timestamp": current_time,
        "status": random.choice(["running", "idle", "maintenance", "error"]),
        "metrics": {
            "temperature": round(random.uniform(20.0, 85.0), 2),
            "pressure": round(random.uniform(0.5, 10.5), 2),
            "vibration": round(random.uniform(0.1, 5.0), 2),
            "output": random.randint(70, 100),
            "efficiency": round(random.uniform(0.65, 0.95), 3)
        },
        "telemetry": {
            "cpuUsage": round(random.uniform(10.0, 95.0), 2),
            "memoryUsage": round(random.uniform(200, 1024), 2),
            "uptime": random.randint(3600, 86400)
        }
    }

def generate_status_data(device_id,device_type):
    """生成设备状态数据，基于generate_device_data函数的字段"""
    current_time = datetime.now().isoformat()
    # 状态数据
    status = random.choice(["running", "idle", "maintenance", "error"])
    
    # 指标数据
    metrics = {
        "temperature": round(random.uniform(20.0, 85.0), 2),
        "pressure": round(random.uniform(0.5, 10.5), 2),
        "vibration": round(random.uniform(0.1, 5.0), 2),
        "output": random.randint(70, 100),
        "efficiency": round(random.uniform(0.65, 0.95), 3)
    }
    
    # 遥测数据
    telemetry = {
        "cpuUsage": round(random.uniform(10.0, 95.0), 2),
        "memoryUsage": round(random.uniform(200, 1024), 2),
        "uptime": random.randint(3600, 86400)
    }
    
    return {
        "version": "1.0",
        "deviceId": f"device_{device_id:02d}",
        "deviceType": device_type,
        "timestamp": current_time,
        "status": status,
        "metrics": metrics,
        "telemetry": telemetry
    }

def device_thread(device_id, interval=5):
    """单个设备线程函数"""
    client_id = f"device_{device_id:02d}"
    client = mqtt.Client(client_id)
    
    # 设置遗嘱消息（Last Will and Testament）
    will_topic = f"factory/lwt/{client_id}"
    will_payload = json.dumps({
        "deviceId": client_id,
        "status": "offline",
        "lastUpdate": datetime.now().isoformat(),
        "online": False,
        "reason": "abnormal_disconnection"
    })
    client.will_set(will_topic, will_payload, qos=QOS, retain=True)
    
    # 设置回调函数
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        # 连接到MQTT代理
        client.connect(BROKER, PORT, KEEPALIVE)
        client.loop_start()
        
        # 等待连接建立
        timeout = 10  # 10秒连接超时
        start_time = time.time()
        while not stop_event.is_set() and time.time() - start_time < timeout:
            if client.is_connected():
                print(f"{client_id} 连接成功")
                break
            time.sleep(0.1)
        else:
            if not client.is_connected():
                print(f"{client_id} 连接超时")
                return
                
        # 定义主题
        line_num = device_id % 3 + 1  # 生产线编号1-3
        topic_base = f"factory/line_{line_num}/{client_id}"
        data_topic = f"{topic_base}/data"
        status_topic = f"{topic_base}/status"
        
        print(f"{client_id} 开始发布数据，主题: {data_topic}")

        data = generate_device_data(device_id)
        data_payload = json.dumps(data)
        result = client.publish(data_topic, data_payload, qos=QOS)
        
        # 主发布循环--主要模拟20台设备的数据变化
        while not stop_event.is_set():#没有收到stop消息才循环
            
            status=generate_status_data(device_id,data['deviceType'])

            result = client.publish(status_topic,json.dumps(status),qos=QOS)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"{client_id} 发布消息到 {status_topic}")
            else:
                print(f"{client_id} 发布失败，错误码: {result.rc}")
            
            client.publish(status_topic, json.dumps(status), qos=QOS, retain=True)
            # 分段睡眠以便及时响应停止事件
            for _ in range(int(interval * 2)):  # 每0.5秒检查一次
                if stop_event.is_set():
                    break
                time.sleep(0.5)
                
    except Exception as e:
        print(f"{client_id} 发生异常: {e}")
    finally:
        # 优雅关闭：发送离线状态
        try:
            offline_status = {
                "deviceId": client_id,
                "status": "offline",
                "deviceType":data['deviceType'],
                "lastUpdate": datetime.now().isoformat(),
                "online": False,
                "reason": "normal_shutdown"
            }
            # 获取当前主题（如果之前定义过）
            line_num = device_id % 3 + 1
            status_topic = f"factory/line_{line_num}/{client_id}/status"
            client.publish(status_topic, json.dumps(offline_status), qos=QOS, retain=True)
            time.sleep(0.1)  # 短暂等待让消息发出
        except Exception as e:
            print(f"{client_id} 发送离线状态时出错: {e}")
        
        # 断开连接
        try:
            client.loop_stop()
            if client.is_connected():
                client.disconnect()
            print(f"{client_id} MQTT连接已关闭")
        except Exception as e:
            print(f"{client_id} 断开连接时出错: {e}")

def main():
    """主函数"""
    print("开始模拟20个IoT设备...")
    print("按 Ctrl+C 停止程序")
    
    threads = []
    
    # 创建并启动所有设备线程
    for device_id in range(1, 21):
        interval = 15  # 随机发布间隔
        thread = threading.Thread(
            target=device_thread,
            args=(device_id,),
            kwargs={"interval": interval},
            name=f"Device_{device_id:02d}_Thread",
            daemon=False  # 非守护线程，主线程会等待它们结束
        )
        threads.append(thread)
        thread.start()
        time.sleep(0.1)  # 稍微错开启动时间
    
    print("所有设备线程已启动")
    
    try:
        # 等待所有线程完成
        while any(thread.is_alive() for thread in threads):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n再次检测到中断信号，加速关闭中...")
    finally:
       #第一阶段、尝试关闭
       stop_event.set()
       first_timeout=5 #第一阶段超时时长
       start_time=time.time()
       
       while(time.time()-start_time<first_timeout and
             any(thread.is_alive() for thread in threads)):
           time.sleep(0.5)#如果未超时、还有线程活着--继续等待
        #第二阶段 检查并处理未退出的线程
        
       alive_threads =[t for t in threads if t.is_alive()]

       if alive_threads:
            print(f"仍有 {len(alive_threads)} 个线程未正常退出，开始强制清理...")
            for thread in alive_threads:
                try:
                    thread.join(timeout=1.0)#等待一秒
                    if thread.is_alive():
                        print(f"线程 {thread.name} 无法正常退出，可能需要强制干预")    
                except Exception as e:
                    print(f"处理线程 {thread.name} 时出错: {e}")
       still_alive=[t for t in threads if t.is_alive()]
       if still_alive:
           print(f"⚠️  警告: {len(still_alive)} 个线程可能未完全清理")
           print("可能需要手动干预或重启程序")
       else:
            print("✅ 所有设备线程已安全退出")
        
       print("程序关闭完成")


       
if __name__ == "__main__":
    main()