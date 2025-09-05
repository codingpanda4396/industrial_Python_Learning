from enum import Enum


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