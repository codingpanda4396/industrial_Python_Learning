'''
模拟20台设备，通过mqtt，通过不同的topic、自定义json数据结构发布生产数据。使用多线程完成。
'''
import paho.mqtt.client as mqtt
import json
import random
import time
import threading
from datetime import datetime

# 配置MQTT client
BROKER = '192.168.56.10'
PORT   = 1883
QOS    = 1

# 设备基础信息
DEVICE_TYPES = [
    "sensor", "controller", "actuator", "motor", "conveyor",
    "robot", "pump", "valve", "generator", "compressor"
]

def generate_device_data(device_id):
    #生产数据generator
    current_time = datetime.now().isoformat()
    device_type  = DEVICE_TYPES[int(device_id)%len(DEVICE_TYPES)]#随机一个设备类型

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

def on_connect(client, userdata, flags, rc):
    """连接回调函数"""
    if rc == 0:
        print(f"{client._client_id.decode()} 连接成功")
    else:
        print(f"{client._client_id.decode()} 链接失败 return code {rc}")

def device_thread(device_id,interval=5):
    "模拟设备线程"
    client_id = f"device_{device_id:02d}"#创建 mqtt client
    client = mqtt.Client(client_id)
    client.on_connect = on_connect 

    client.connect(BROKER,PORT)
    client.loop_start()

    topic_base=f"factory/line_{device_id%3}/{client_id}"
    data_topic=f"{topic_base}/data"
    status_topic=f"{topic_base}/status"

    try:
        while True:
            # 生成设备数据
            device_data = generate_device_data(device_id)
            
            # 发布到数据主题
            data_payload = json.dumps(device_data)
            result = client.publish(data_topic, data_payload, QOS)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"{client_id} published data to {data_topic}")
            else:
                print(f"{client_id} failed to publish data")
            
            # 发布状态信息（保留消息--后续订阅者上线立即收到）
            status_data = {
                "deviceId": device_data["deviceId"],
                "status": device_data["status"],
                "lastUpdate": device_data["timestamp"],
                "online": True
            }
            client.publish(status_topic, json.dumps(status_data), QOS, retain=True)
            
            # 等待下一次发布
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"{client_id} stopping...")
    finally:
        client.loop_stop()
        client.disconnect()


def main():
    """主函数"""
    print("Starting 20 device simulators...")
    
    # 创建并启动设备线程
    threads = []
    for device_id in range(1, 21):
        thread = threading.Thread(
            target=device_thread,
            args=(device_id,),
            kwargs={"interval": random.randint(3, 8)},  # 随机间隔
            name=f"Device_{device_id:02d}_Thread"
        )
        thread.daemon = True
        threads.append(thread)#加入list
        thread.start()
        print(f"Started device {device_id:02d}")
    
    # 等待所有线程
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nShutting down all devices...")

if __name__ == "__main__":
    main()