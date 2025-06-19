import os
import json
import logging
from datetime import datetime
#配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("equipment_monitor.log"),
        logging.StreamHandler()
    ]
)   
logger=logging.getLogger("IndustrialMonitor")

class EquipmentMonitor:
    def __init__(self,data_dir="data",processed_dir=""):
        self.data_dir = data_dir
        self.processed_dir = processed_dir
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs("reports", exist_ok=True)
    
    def process_new_files(self):
        """处理所有未处理的日志文件"""
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                self.process_file(filename)


    def process_file(self, filename):
        """处理单个日志文件"""
        filepath = os.path.join(self.data_dir, filename)
        logger.info(f"Processing: {filename}")
        
        try:
            with open(filepath,'r') as f:
                data=json.load(f)#文件对象反序列化为python对象
            #校验数据完整性
            if not self.validate_data(data):
                logger.warning(f"Invalid data format: {filename}")
                return
            processed_data = {
                "timestamp": data["timestamp"],
                "device_id": data["device_id"],
                "metrics": {
                    "temperature": data["readings"]["temp"],
                    "vibration": data["readings"]["vib"],
                    "power_consumption": data["readings"]["power"]
                },
                "status": "Normal"
            }
            # 异常检测
            if processed_data["metrics"]["temperature"] > 85:
                processed_data["status"] = "OVERHEAT"
                logger.error(f"Device {data['device_id']} OVERHEAT at {data['timestamp']}")
                
            # 保存处理结果
            output_path = os.path.join(self.processed_dir, f"proc_{filename}")
            with open(output_path, 'w') as out:
                json.dump(processed_data, out, indent=2)#处理结果输出到文件中
                
            logger.info(f"Processed: {filename} -> Status: {processed_data['status']}")       
        except Exception as e:
            logger.exception(f"Error processing {filename}: {str(e)}")

    def validate_data(self, data):
        """验证JSON数据结构完整性"""
        required_keys = {"device_id", "timestamp", "readings"}#readings是嵌套dict
        if not all(k in data for k in required_keys):
            return False
            
        reading_keys = {"temp", "vib", "power"}#嵌套dict中的三个参数
        return all(k in data["readings"] for k in reading_keys)
    
    def generate_daily_report(self):
        """生成每日分析报告"""
        report_date = datetime.now().strftime("%Y%m%d")
        report_path = f"./reports/daily_report_{report_date}.txt"
        
        # 收集所有处理过的数据
        all_data = []
        for filename in os.listdir(self.processed_dir):#遍历process目录中所有条目名
            if filename.startswith("proc_"):
                with open(os.path.join(self.processed_dir, filename), 'r') as f:
                    all_data.append(json.load(f))
        
        # 分析数据（示例：统计异常率）
        status_count = {"Normal": 0, "OVERHEAT": 0}
        for entry in all_data:
            status_count[entry["status"]] += 1
            
        total = len(all_data)
        with open(report_path, 'w') as report:
            report.write(f"设备状态日报 ({report_date})\n")
            report.write("="*40 + "\n")
            report.write(f"分析样本总数: {total}\n")
            report.write(f"正常运行: {status_count['Normal']} ({status_count['Normal']/total:.1%})\n")
            report.write(f"过热告警: {status_count['OVERHEAT']}\n")
            
        logger.info(f"Generated daily report: {report_path}")


        # 主程序执行
if __name__ == "__main__":
    monitor = EquipmentMonitor("D:\CodingPanda\Python\projects\p1\\testData","D:\CodingPanda\Python\projects\p1\process")
    
    # 模拟定时任务执行（实际部署可用cron或APScheduler）
    logger.info("Starting industrial monitoring system")
    monitor.process_new_files()
    monitor.generate_daily_report()
    logger.info("Monitoring cycle completed")