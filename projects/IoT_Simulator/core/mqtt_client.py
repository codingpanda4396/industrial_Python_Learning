"""MQTT客户端包装类"""
import paho.mqtt.client as mqtt
import logging
from typing import Callable, Optional
from config.settings import MQTTConfig

class MQTTClientWrapper:
    """封装MQTT客户端功能的包装类"""
    
    def __init__(self, client_id: str, config: MQTTConfig, logger: logging.Logger):
        self.client_id = client_id
        self.config = config
        self.logger = logger
        self.client = self._create_client()
        self._setup_callbacks()
    
    def _create_client(self) -> mqtt.Client:
        """创建MQTT客户端实例"""
        protocol_map = {
            'MQTTv31': mqtt.MQTTv31,
            'MQTTv311': mqtt.MQTTv311,
            'MQTTv5': mqtt.MQTTv5
        }
        
        protocol = protocol_map.get(self.config.protocol, mqtt.MQTTv311)
        return mqtt.Client(client_id=self.client_id, protocol=protocol)
    
    def _setup_callbacks(self):
        """设置MQTT回调函数"""
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_disconnect = self._on_disconnect
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调函数"""
        if rc == 0:
            self.logger.info(f"{self.client_id} connected successfully")
        else:
            self.logger.error(f"{self.client_id} connection failed with code: {rc}")
    
    def _on_publish(self, client, userdata, mid):
        """发布回调函数"""
        self.logger.debug(f"Message {mid} published by {self.client_id}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调函数"""
        if rc != 0:
            self.logger.warning(f"{self.client_id} unexpected disconnection")
    
    def connect(self) -> bool:
        """连接到MQTT代理"""
        try:
            if self.config.username and self.config.password:
                self.client.username_pw_set(
                    self.config.username, 
                    self.config.password
                )
            
            self.client.connect(
                self.config.broker, 
                self.config.port, 
                self.config.keepalive
            )
            self.client.loop_start()
            return True
        except Exception as e:
            self.logger.error(f"{self.client_id} connection error: {e}")
            return False
    
    def disconnect(self):
        """断开MQTT连接"""
        try:
            self.client.loop_stop()
            if self.client.is_connected():
                self.client.disconnect()
            self.logger.info(f"{self.client_id} disconnected")
        except Exception as e:
            self.logger.error(f"{self.client_id} disconnection error: {e}")
    
    def publish(self, topic: str, payload: str, retain: bool = False) -> bool:
        """发布消息到指定主题"""
        try:
            result = self.client.publish(
                topic, 
                payload, 
                qos=self.config.qos, 
                retain=retain
            )
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self.logger.error(f"{self.client_id} publish error: {e}")
            return False
    
    def set_will(self, topic: str, payload: str):
        """设置遗嘱消息"""
        self.client.will_set(
            topic, 
            payload, 
            qos=self.config.qos, 
            retain=True
        )
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.client.is_connected()