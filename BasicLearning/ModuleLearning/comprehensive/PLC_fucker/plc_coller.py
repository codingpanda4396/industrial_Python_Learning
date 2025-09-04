import os
import json
import logging
import threading
import requests
from datetime import datetime
from time import sleep

# ===== 配置区域 =====
PLC_DATA_DIR = r"D:\CodingPanda\Python\ModuleLearning\comprehensive\PLC_fucker\PLC data"       # PLC数据存放目录
API_ENDPOINT = "http://your-api.com/upload"  # 数据上报地址
LOG_FILE = "plc_collector.log"  # 日志文件路径
# ===================

def setup_logger():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(threadName)s] - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('PLCCollector')

logger = setup_logger()

def read_plc_data(file_path):
    """读取模拟PLC数据文件"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)  # 文件内容应为JSON格式
    except Exception as e:
        logger.error(f"文件读取失败 {file_path}: {str(e)}")
        return None

def process_data(raw_data):
    """数据处理（清洗+计算）"""
    if not raw_data:
        return None
    
    # 添加处理时间戳
    processed_data = raw_data.copy()
    processed_data['process_time'] = datetime.now().isoformat()
    
    # 模拟数据清洗：删除无效字段
    processed_data.pop('debug_info', None)
    
    # 模拟计算：功率 = 电压*电流
    if 'voltage' in raw_data and 'current' in raw_data:
        processed_data['power'] = raw_data['voltage'] * raw_data['current']
    
    return processed_data

def upload_data(data):
    """数据上报到云端API"""
    try:
        response = requests.post(
            API_ENDPOINT,
            json=data,
            timeout=5
        )
        response.raise_for_status()
        logger.info(f"数据上报成功！设备: {data.get('device_id')}")
        return True
    except Exception as e:
        logger.error(f"API上报失败: {str(e)}")
        return False

def process_file(file_path):
    """单文件处理全流程"""
    logger.info(f"开始处理: {os.path.basename(file_path)}")
    
    # 读取 → 处理 → 上报
    if (raw_data := read_plc_data(file_path)) is None:
        return
    
    if (clean_data := process_data(raw_data)) is None:
        return
        
    #if upload_data(clean_data):
        # 成功后移动文件
    archive_path = os.path.join("archived", os.path.basename(file_path))
    os.rename(file_path, archive_path)

def main():
    """主函数：多线程数据处理"""
    logger.info("====== PLC数据采集系统启动 ======")
    
    # 确保目录存在
    os.makedirs(PLC_DATA_DIR, exist_ok=True)
    os.makedirs("archived", exist_ok=True)
    
    while True:
        # 获取需要处理的文件列表
        files = [
            os.path.join(PLC_DATA_DIR, f)
            for f in os.listdir(PLC_DATA_DIR)
            if f.endswith('.json')
        ]
        
        if not files:
            logger.info("无待处理文件，等待5秒...")
            sleep(5)
            continue
            
        # 多线程处理
        threads = []
        for file_path in files:
            thread = threading.Thread(
                target=process_file,
                args=(file_path,),
                name=f"PLCThread-{os.path.basename(file_path)}"
            )
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
        logger.info(f"本轮完成: {len(files)}个文件处理")

if __name__ == "__main__":
    main()