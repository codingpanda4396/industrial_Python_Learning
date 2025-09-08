import json
import logging
import paho.mqtt.client as mqtt
import pymysql
from dbutils.pooled_db import PooledDB
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import signal
import threading
import time
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mqtt_subscriber.log')
    ]
)
logger = logging.getLogger(__name__)

class TopicType(Enum):
    """主题类型枚举"""
    DATA = "data"
    STATUS = "status"

@dataclass
class MQTTConfig:
    """MQTT配置数据类"""
    broker: str = '192.168.56.10'
    port: int = 1883
    qos: int = 1
    client_id_prefix: str = "subscriber_"
    data_topic: str = "factory/+/+/data"
    status_topic: str = "factory/+/+/status"
    keepalive: int = 60
    reconnect_delay: int = 5
    max_reconnect_attempts: int = 10

@dataclass
class DBConfig:
    """数据库配置数据类"""
    host: str = '192.168.56.10'
    port: int = 3306
    user: str = 'root'
    password: str = '439695'
    database: str = 'task1_mqtt_device'
    min_connections: int = 2
    max_connections: int = 10
    charset: str = 'utf8mb4'

class DatabaseManager:
    """数据库管理类，封装所有数据库操作"""
    
    def __init__(self, config: DBConfig):
        self.config = config
        self.pool = self._create_connection_pool()
        logger.info("数据库连接池初始化完成")
    
    def _create_connection_pool(self) -> PooledDB:
        """创建数据库连接池"""
        return PooledDB(
            creator=pymysql,
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            mincached=self.config.min_connections,
            maxcached=self.config.max_connections,
            maxconnections=self.config.max_connections,
            blocking=True,
            charset=self.config.charset
        )
    
    def get_connection(self):
        """从连接池获取连接"""
        return self.pool.connection()
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[int]:
        """执行SQL查询并返回影响的行数或最后插入的ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ()) 
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"数据库查询执行失败: {e}")
            raise
    
    def execute_many(self, query: str, params_list: list) -> int:
        """批量执行SQL查询"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"批量数据库操作失败: {e}")
            raise

class DeviceDataProcessor:
    """设备数据处理类，负责解析和验证设备数据"""
    
    @staticmethod
    def parse_message(payload: str, topic: str) -> Optional[Dict[str, Any]]:
        """解析MQTT消息负载"""
        try:
            data = json.loads(payload)
            
            # 验证必需字段
            required_fields = ['deviceId', 'deviceType', 'status', 'metrics', 'telemetry']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"消息缺少必需字段: {field}")
                    return None
            
            # 添加主题信息
            data['topic'] = topic
            data['topic_type'] = TopicType.DATA if topic.endswith('data') else TopicType.STATUS
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始数据: {payload}")
            return None
        except Exception as e:
            logger.error(f"消息解析异常: {e}")
            return None
    
    @staticmethod
    def extract_device_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
        """提取设备指标数据"""
        metrics = data.get('metrics', {})#getOrdefault
        return {
            'temperature': metrics.get('temperature'),
            'pressure': metrics.get('pressure'),
            'vibration': metrics.get('vibration'),
            'output': metrics.get('output'),
            'efficiency': metrics.get('efficiency')
        }
    
    @staticmethod
    def extract_device_telemetry(data: Dict[str, Any]) -> Dict[str, Any]:
        """提取设备遥测数据"""
        telemetry = data.get('telemetry', {})
        return {
            'cpu_usage': telemetry.get('cpuUsage'),
            'memory_usage': telemetry.get('memoryUsage'),
            'uptime': telemetry.get('uptime')
        }

class MQTTSubscriber:
    """MQTT订阅客户端类"""
    
    def __init__(self, config: MQTTConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.client = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.stop_event = threading.Event()
        
        self._setup_mqtt_client()
    
    def _setup_mqtt_client(self):
        """设置MQTT客户端"""
        client_id = f"{self.config.client_id_prefix}{threading.get_ident()}"
        self.client = mqtt.Client(client_id=client_id)
        
        # 设置回调函数
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("成功连接到MQTT Broker!")
            
            # 订阅主题
            client.subscribe(self.config.data_topic, qos=self.config.qos)
            client.subscribe(self.config.status_topic, qos=self.config.qos)
        else:
            logger.error(f"连接失败，返回码: {rc}")
            self.is_connected = False
    
    def _on_message(self, client, userdata, msg):
        """消息回调函数"""
        try:
            logger.info(f"收到来自主题 [{msg.topic}] 的消息")
            
            # 解析消息
            processor = DeviceDataProcessor()
            data = processor.parse_message(msg.payload.decode('utf-8'), msg.topic)
            
            if data:
                # 存储数据
                self._store_device_data(data)
                logger.info(f"设备 {data.get('deviceId')} 数据处理完成")
                
        except Exception as e:
            logger.error(f"处理消息时发生意外错误: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"意外断开连接，返回码: {rc}")
            self._attempt_reconnect()
        else:
            logger.info("正常断开连接")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """订阅回调函数"""
        logger.info(f"成功订阅主题，QoS: {granted_qos[0]}")
    
    def _attempt_reconnect(self):
        """尝试重新连接"""
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("达到最大重连尝试次数，停止重连")
            return
        
        self.reconnect_attempts += 1
        delay = self.config.reconnect_delay * self.reconnect_attempts
        
        logger.info(f"尝试第 {self.reconnect_attempts} 次重连，等待 {delay} 秒...")
        time.sleep(delay)
        
        try:
            self.connect()
        except Exception as e:
            logger.error(f"重连失败: {e}")
    
    def _store_device_data(self, data: Dict[str, Any]):
        """存储设备数据到数据库"""
        try:
            device_id = data.get('deviceId')
            device_type = data.get('deviceType')
            device_status = data.get('status')
            
            # 提取指标和遥测数据
            processor = DeviceDataProcessor()
            metrics = processor.extract_device_metrics(data)
            telemetry = processor.extract_device_telemetry(data)
            
            # 根据主题类型执行不同的存储逻辑
            if data['topic_type'] == TopicType.DATA:
                self._store_device_info(device_id, device_type)
            elif data['topic_type'] == TopicType.STATUS:
                self._store_device_status(device_id, device_status, metrics, telemetry)
                
        except Exception as e:
            logger.error(f"存储设备数据失败: {e}")
            raise
    
    def _store_device_info(self, device_id: str, device_type: str):
        """存储设备基本信息"""
        query = """
            INSERT INTO devices (device_id, device_type)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE device_type = VALUES(device_type)
        """
        self.db_manager.execute_query(query, (device_id, device_type))
    
    def _store_device_status(self, device_id: str, status: str, 
                            metrics: Dict[str, Any], telemetry: Dict[str, Any]):
        """存储设备状态信息"""
        # 插入状态记录
        status_query = """
            INSERT INTO device_status (device_id, device_status)
            VALUES (%s, %s)
        """
        status_id = self.db_manager.execute_query(status_query, (device_id, status))
        
        if status_id:
            # 插入指标数据
            metrics_query = """
                INSERT INTO device_metrics 
                (status_id, temperature, pressure, vibration, output, efficiency)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.db_manager.execute_query(metrics_query, (
                status_id, metrics['temperature'], metrics['pressure'], 
                metrics['vibration'], metrics['output'], metrics['efficiency']
            ))
            
            # 插入遥测数据
            telemetry_query = """
                INSERT INTO device_telemetry 
                (status_id, cpu_usage, memory_usage, uptime)
                VALUES (%s, %s, %s, %s)
            """
            self.db_manager.execute_query(telemetry_query, (
                status_id, telemetry['cpu_usage'], 
                telemetry['memory_usage'], telemetry['uptime']
            ))
    
    def connect(self):
        """连接到MQTT代理"""
        try:
            logger.info(f"尝试连接到 {self.config.broker}:{self.config.port}")
            self.client.connect(
                self.config.broker, 
                self.config.port, 
                self.config.keepalive
            )
            self.client.loop_start()
        except Exception as e:
            logger.error(f"连接失败: {e}")
            raise
    
    def disconnect(self):
        """断开MQTT连接"""
        try:
            self.stop_event.set()
            self.client.loop_stop()
            if self.is_connected:
                self.client.disconnect()
            logger.info("MQTT连接已关闭")
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")
    
    def run(self):
        """运行订阅客户端"""
        try:
            self.connect()
            
            # 等待中断信号
            while not self.stop_event.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"运行过程中发生错误: {e}")
        finally:
            self.disconnect()

class Application:
    """主应用程序类"""
    
    def __init__(self):
        self.mqtt_config = MQTTConfig()
        self.db_config = DBConfig()
        self.db_manager = None
        self.subscriber = None
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """信号处理函数"""
        logger.info(f"接收到信号 {sig}，正在关闭应用...")
        if self.subscriber:
            self.subscriber.disconnect()
    
    def initialize(self):
        """初始化应用组件"""
        try:
            # 初始化数据库管理器
            self.db_manager = DatabaseManager(self.db_config)
            
            # 初始化MQTT订阅器
            self.subscriber = MQTTSubscriber(self.mqtt_config, self.db_manager)
            
            logger.info("应用初始化完成")
            return True
        except Exception as e:
            logger.error(f"应用初始化失败: {e}")
            return False
    
    def run(self):
        """运行主应用程序"""
        if not self.initialize():
            return
        
        try:
            logger.info("启动MQTT订阅客户端...")
            self.subscriber.run()
        except Exception as e:
            logger.error(f"应用程序运行错误: {e}")
        finally:
            logger.info("应用程序关闭完成")

def main():
    """主函数"""
    app = Application()
    app.run()

if __name__ == "__main__":
    main()