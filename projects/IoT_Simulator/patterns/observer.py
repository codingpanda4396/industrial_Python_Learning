"""观察者模式实现"""
from abc import ABC, abstractmethod
from typing import List
import logging

class Observer(ABC):
    """观察者抽象基类"""
    @abstractmethod
    def update(self, device, data: dict):
        """接收更新通知"""
        pass

class Subject(ABC):
    """主题抽象基类"""
    
    def __init__(self):
        self._observers: List[Observer] = []#维护观察者列表
    
    def attach(self, observer: Observer):
        """添加观察者"""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: Observer):
        """移除观察者"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, data: dict):
        """通知所有观察者"""
        for observer in self._observers:
            observer.update(self, data)
class DeviceMonitor(Observer):
    """设备监控观察者"""
    #监控设备的运行并根据状态进行日志记录
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def update(self, device, data: dict):
        """处理设备数据更新：记录状态变化"""
        device_id = data.get('deviceId', 'unknown')
        status = data.get('status', 'unknown')
        
        if status == 'error':
            self.logger.warning(f"Device {device_id} is in error state")
        elif status == 'maintenance':
            self.logger.info(f"Device {device_id} requires maintenance")

class PerformanceMonitor(Observer):
    """性能监控观察者：threshold低时报警"""
    
    def __init__(self, logger: logging.Logger, threshold: float = 80.0):
        self.logger = logger
        self.threshold = threshold
    
    def update(self, device, data: dict):
        """监控设备性能"""
        metrics = data.get('metrics', {})
        efficiency = metrics.get('efficiency', 0)
        
        if efficiency < self.threshold:
            device_id = data.get('deviceId', 'unknown')
            self.logger.warning(
                f"Device {device_id} efficiency below threshold: {efficiency}%"
            )