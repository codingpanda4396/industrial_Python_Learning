"""设备类定义"""
from abc import ABC, abstractmethod
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from config.settings import DeviceType, DeviceStatus
from core.mqtt_client import MQTTClientWrapper
import logging

class Device(ABC):
    """IoT设备抽象基类"""
    
    def __init__(self, device_id: int, device_type: DeviceType, 
                 interval: int, mqtt_config, logger: logging.Logger):
        self.device_id = device_id
        self.device_type = device_type
        self.interval = interval
        self.client_id = f"device_{device_id:02d}"
        self.logger = logger.getChild(self.client_id)
        
        self.mqtt_client = MQTTClientWrapper(
            self.client_id, mqtt_config, self.logger
        )
        self._setup_mqtt_will()
    
    def _setup_mqtt_will(self):
        """设置MQTT遗嘱消息"""
        will_topic = f"factory/lwt/{self.client_id}"
        will_payload = self._create_will_payload("abnormal_disconnection")
        self.mqtt_client.set_will(will_topic, will_payload)
    
    def _create_will_payload(self, reason: str) -> str:
        """创建遗嘱消息负载"""
        import json
        return json.dumps({
            "deviceId": self.client_id,
            "deviceType": self.device_type.value,
            "status": DeviceStatus.OFFLINE.value,
            "lastUpdate": datetime.now().isoformat(),
            "online": False,
            "reason": reason
        })
    
    def get_base_data(self) -> Dict[str, Any]:
        """获取基础设备数据"""
        return {
            "version": "1.0",
            "deviceId": self.client_id,
            "deviceType": self.device_type.value,
            "timestamp": datetime.now().isoformat()
        }
    
    @abstractmethod
    def generate_metrics(self) -> Dict[str, Any]:
        """生成设备指标数据（由子类实现）"""
        pass
    
    @abstractmethod
    def generate_telemetry(self) -> Dict[str, Any]:
        """生成设备遥测数据（由子类实现）"""
        pass
    
    def generate_data(self) -> Dict[str, Any]:
        """生成完整的设备数据"""
        base_data = self.get_base_data()
        metrics = self.generate_metrics()
        telemetry = self.generate_telemetry()
        
        return {
            **base_data,
            "status": random.choice([s.value for s in [
                DeviceStatus.RUNNING, DeviceStatus.IDLE, 
                DeviceStatus.MAINTENANCE, DeviceStatus.ERROR
            ]]),
            "metrics": metrics,
            "telemetry": telemetry
        }
    
    def connect(self, timeout: int = 10) -> bool:
        """连接到MQTT代理"""
        if not self.mqtt_client.connect():
            return False
        
        # 等待连接建立
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.mqtt_client.is_connected():
                return True
            time.sleep(0.1)
        return False
    
    def disconnect(self, reason: str = "normal_shutdown"):
        """断开连接并发送离线状态"""
        try:
            offline_data = {
                **self.get_base_data(),
                "status": DeviceStatus.OFFLINE.value,
                "online": False,
                "reason": reason
            }
            self.publish_status(offline_data, retain=True)
            time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error sending offline status: {e}")
        finally:
            self.mqtt_client.disconnect()
    
    def publish_data(self, data: Dict[str, Any]) -> bool:
        """发布设备数据"""
        line_num = self.device_id % 3 + 1
        topic = f"factory/line_{line_num}/{self.client_id}/data"
        import json
        return self.mqtt_client.publish(topic, json.dumps(data))
    
    def publish_status(self, status: Dict[str, Any], retain: bool = False) -> bool:
        """发布设备状态"""
        line_num = self.device_id % 3 + 1
        topic = f"factory/line_{line_num}/{self.client_id}/status"
        import json
        return self.mqtt_client.publish(topic, json.dumps(status), retain)
    
    def run(self, stop_event):
        """设备运行主循环"""
        try:
            if not self.connect():
                self.logger.error("Connection timeout")
                return
            
            self.logger.info("Started publishing data")
            
            while not stop_event.is_set():
                # 生成并发布状态数据
                status_data = self.generate_data()
                success = self.publish_status(status_data, retain=True)
                
                if success:
                    self.logger.debug("Status message published")
                else:
                    self.logger.warning("Publish failed")
                
                # 分段睡眠以便及时响应停止事件
                for _ in range(int(self.interval * 2)):
                    if stop_event.is_set():
                        break
                    time.sleep(0.5)
                    
        except Exception as e:
            self.logger.error(f"Exception occurred: {e}")
        finally:
            self.disconnect()
            self.logger.info("Stopped")

class SensorDevice(Device):
    """传感器设备"""
    
    def generate_metrics(self) -> Dict[str, Any]:
        return {
            "temperature": round(random.uniform(20.0, 85.0), 2),
            "pressure": round(random.uniform(0.5, 10.5), 2),
            "vibration": round(random.uniform(0.1, 5.0), 2),
            "output": random.randint(70, 100),
            "efficiency": round(random.uniform(0.65, 0.95), 3)
        }
    
    def generate_telemetry(self) -> Dict[str, Any]:
        return {
            "cpuUsage": round(random.uniform(10.0, 95.0), 2),
            "memoryUsage": round(random.uniform(200, 1024), 2),
            "uptime": random.randint(3600, 86400)
        }

class ControllerDevice(Device):
    """控制器设备"""
    
    def generate_metrics(self) -> Dict[str, Any]:
        return {
            "signalStrength": round(random.uniform(0.5, 1.0), 2),
            "responseTime": round(random.uniform(0.1, 2.0), 2),
            "throughput": random.randint(100, 1000),
            "errorRate": round(random.uniform(0.0, 5.0), 2)
        }
    
    def generate_telemetry(self) -> Dict[str, Any]:
        return {
            "cpuUsage": round(random.uniform(5.0, 60.0), 2),
            "memoryUsage": round(random.uniform(100, 512), 2),
            "networkUsage": round(random.uniform(10.0, 80.0), 2),
            "processCount": random.randint(10, 100)
        }

class MotorDevice(Device):
    """电机设备"""
    
    def generate_metrics(self) -> Dict[str, Any]:
        return {
            "rpm": random.randint(1000, 3000),
            "torque": round(random.uniform(10.0, 100.0), 2),
            "voltage": round(random.uniform(200.0, 240.0), 2),
            "current": round(random.uniform(5.0, 20.0), 2),
            "temperature": round(random.uniform(30.0, 90.0), 2)
        }
    
    def generate_telemetry(self) -> Dict[str, Any]:
        return {
            "operatingHours": random.randint(100, 10000),
            "maintenanceCount": random.randint(0, 10),
            "lastMaintenance": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
            "efficiency": round(random.uniform(0.7, 0.95), 3)
        }