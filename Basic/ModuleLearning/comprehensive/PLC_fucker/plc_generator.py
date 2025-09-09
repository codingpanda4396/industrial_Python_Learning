# generate_plc_data.py
import os
import json
import random
from datetime import datetime, timedelta
import time

PLC_DATA_DIR = r"D:\CodingPanda\Python\ModuleLearning\comprehensive\PLC_fucker\PLC data"  # 与主程序相同的目录

def generate_plc_data(device_id):
    """生成单条PLC设备数据"""
    return {
        "device_id": device_id,
        "timestamp": (datetime.now() - timedelta(seconds=random.randint(0, 60))).isoformat(),
        "voltage": round(random.uniform(210.0, 240.0), 2),
        "current": round(random.uniform(5.0, 12.0), 2),
        "temperature": round(random.uniform(30.0, 50.0), 2),
        "pressure": random.randint(80, 120),
        "status": random.choice([0, 1])  # 0:停止 1:运行
    }

def generate_files():
    """持续生成PLC数据文件"""
    os.makedirs(PLC_DATA_DIR, exist_ok=True)
    devices = [f"PLC-{line}{unit:02d}" for line in "ABC" for unit in range(1, 6)]#生成一些ID
    
    print(f"PLC数据生成器已启动，保存到目录: {os.path.abspath(PLC_DATA_DIR)}")
    
    file_count = 0
    while True:
        device = random.choice(devices)
        data = generate_plc_data(device)#以device中的id名，生成PLC数据
        
        # 创建带时间戳的文件名
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{device}_{timestamp_str}_{random.randint(1000,9999)}.json"
        filepath = os.path.join(PLC_DATA_DIR, filename)
        
        # 写入数据
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"已生成: {filename}")
        file_count += 1
        
        # 每5-15秒随机生成一个新文件（模拟设备数据刷新）
        time.sleep(random.uniform(5, 15))

if __name__ == "__main__":
    generate_files()