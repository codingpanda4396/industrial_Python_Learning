"""应用配置设置"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

class DeviceType(Enum):
    SENSOR = "sensor"
    CONTROLLER = "controller"
    ACTUATOR = "actuator"
    MOTOR = "motor"
    CONVEYOR = "conveyor"
    ROBOT = "robot"
    PUMP = "pump"
    VALVE = "valve"
    GENERATOR = "generator"
    COMPRESSOR = "compressor"

class DeviceStatus(Enum):
    RUNNING = "running"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class MQTTConfig:
    broker: str = '192.168.56.10'
    port: int = 1883
    qos: int = 1
    keepalive: int = 60
    username: str = "panda"
    password: str = "439695"
    client_id_prefix: str = "device_"
    protocol: str = 'MQTTv311'

@dataclass
class AppConfig:
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    device_count: int = 20
    default_interval: int = 15
    log_level: str = "INFO"
    log_file: str = "iot_simulator.log"