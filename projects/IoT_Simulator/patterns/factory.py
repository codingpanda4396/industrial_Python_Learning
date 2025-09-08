"""设备工厂模式实现"""
from typing import Type
from core.devices import Device, SensorDevice, ControllerDevice, MotorDevice
from config.settings import DeviceType

class DeviceFactory:
    """设备工厂类，负责创建特定类型的设备"""
    
    _device_registry = {}#设备注册表
    
    @classmethod
    def register_device(cls, device_type: DeviceType, device_class: Type[Device]):
        """注册设备类型和对应的类"""
        cls._device_registry[device_type] = device_class
    
    @classmethod
    def create_device(cls, device_id: int, device_type: DeviceType, 
                     interval: int, mqtt_config, logger) -> Device:
        """创建特定类型的设备实例"""
        device_class = cls._device_registry.get(device_type, SensorDevice)#getOrDefault 获取设备类型对应的类，默认使用传感器类
        return device_class(device_id, device_type, interval, mqtt_config, logger)
    
    @classmethod
    def get_available_device_types(cls):
        """获取可用的设备类型"""
        return list(cls._device_registry.keys())

# 注册设备类型
DeviceFactory.register_device(DeviceType.SENSOR, SensorDevice)
DeviceFactory.register_device(DeviceType.CONTROLLER, ControllerDevice)
DeviceFactory.register_device(DeviceType.MOTOR, MotorDevice)
DeviceFactory.register_device(DeviceType.ACTUATOR, SensorDevice)  # 默认使用传感器
DeviceFactory.register_device(DeviceType.ROBOT, ControllerDevice)  # 默认使用控制器