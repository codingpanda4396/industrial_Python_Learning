"""
模拟完整PLC数据处理流程：
1. 扫描数据目录
2. 多线程处理文件
3. 记录详细日志
4. 上报处理结果

代码逻辑： 日志配置->定义处理单个文件的函数->定义上报数据的函数->多线程处理文件
"""

import os
import json
import logging
import threading
from datetime import datetime
import requests

# 日志配置
logging.basicConfig(
    level=logging.INFO,#日志级别设置为INFO
    format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("plc_pipeline.log"),
        logging.StreamHandler()
    ]   #输出到控制台、文件
)

API_URL = "http://industry-api.example.com/report"

def process_plc_file(file_path):
    """处理单个PLC数据文件"""
    try:
        logging.info(f"开始处理: {os.path.basename(file_path)}")
        
        # 模拟文件处理
        with open(file_path) as f:
            data = json.load(f)
        
        # 添加处理时间戳
        data['processed_at'] = datetime.now().isoformat()
        
        # 模拟数据处理
        data['status'] = 'PROCESSED'
        
        logging.info(f"处理完成: {os.path.basename(file_path)}")
        return data
        
    except Exception as e:
        logging.error(f"文件处理失败: {file_path} - {str(e)}")
        return None

def report_to_api(data):
    """数据上报API"""
    if not data:
        return
        
    try:
        response = requests.post(API_URL, json=data, timeout=5)
        response.raise_for_status()
        logging.info(f"数据上报成功: {data['device_id']}")
    except Exception as e:
        logging.error(f"上报失败: {data['device_id']} - {str(e)}")

def main():
    data_dir = "plc_data"
    processed_dir = "processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    logging.info(f"发现 {len(files)} 个PLC数据文件")
    
    # 多线程处理
    threads = []
    for file in files:
        file_path = os.path.join(data_dir, file)
        
        # 为每个文件创建处理线程
        thread = threading.Thread(
            target=lambda fp: (
                # 处理文件      
                result := process_plc_file(fp),
                # 上报结果
                report_to_api(result),
                # 移动文件
                os.rename(fp, os.path.join(processed_dir, os.path.basename(fp)))
            ),
            args=(file_path,),
            name=f"Thread-{file}"
        )
        thread.start()
        threads.append(thread)
    
    # 等待所有线程结束
    for thread in threads:
        thread.join()
    
    logging.info("所有PLC数据处理完成!")

if __name__ == "__main__":
    main()