"""设备管理类"""
import threading
import signal
import time
from typing import List
from core.devices import Device
from patterns.observer import Subject, DeviceMonitor, PerformanceMonitor
import logging

from config.settings import DeviceType

class DeviceManager(Subject):
    """设备管理器，负责管理所有设备线程和生命周期"""
    
    def __init__(self, config, logger: logging.Logger):
        super().__init__()
        self.config = config
        self.logger = logger
        self.devices: List[Device] = []#维护设备实例列表
        self.threads: List[threading.Thread] = []#维护设备线程列表
        self.stop_event = threading.Event()# 用于线程间通信，通知线程停止运行
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 设置观察者
        self._setup_observers()
    
    def _setup_observers(self):
        """设置观察者"""
        device_monitor = DeviceMonitor(self.logger)#设置设备状态监控观察者
        performance_monitor = PerformanceMonitor(self.logger, threshold=70.0)#设置性能监控观察者
        
        self.attach(device_monitor)#加入到内部维护的观察者列表
        self.attach(performance_monitor)
    
    def signal_handler(self, sig, frame):
        """处理中断信号"""
        self.logger.info("Received interrupt signal, stopping all devices...")
        self.stop_event.set()#通知所有线程停止运行
    
    def create_devices(self):
        """创建所有设备实例"""
        from patterns.factory import DeviceFactory
        
        device_types = list(DeviceType)
        
        for device_id in range(1, self.config.device_count + 1):
            device_type = device_types[device_id % len(device_types)]
            
            device = DeviceFactory.create_device(
                device_id=device_id,
                device_type=device_type,
                interval=self.config.default_interval,
                mqtt_config=self.config.mqtt,
                logger=self.logger
            )
            
            self.devices.append(device)
    
    def start_all(self):
        """启动所有设备线程"""
        self.logger.info(f"Starting simulation of {len(self.devices)} IoT devices...")
        self.logger.info("Press Ctrl+C to stop the program")
        
        for device in self.devices:
            thread = threading.Thread(
                target=device.run,          
                args=(self.stop_event,),
                name=f"{device.client_id}_Thread",
                daemon=False
            )
            self.threads.append(thread)
            thread.start()
            time.sleep(0.1)
        
        self.logger.info(f"All {len(self.devices)} device threads started")
    
    def stop_all(self):
        """停止所有设备线程"""
        self.stop_event.set()
        
        # 第一阶段：等待正常退出
        timeout = 5
        start_time = time.time()
        
        while (time.time() - start_time < timeout and 
               any(t.is_alive() for t in self.threads)):#未超时且有线程未关闭
            time.sleep(0.5)
        
        # 第二阶段：处理未退出的线程
        alive_threads = [t for t in self.threads if t.is_alive()]
        if alive_threads:
            self.logger.warning(
                f"{len(alive_threads)} threads did not exit normally, starting forced cleanup..."
            )
            
            for thread in alive_threads:
                try:
                    thread.join(timeout=1.0)
                    if thread.is_alive():
                        self.logger.error(
                            f"Thread {thread.name} could not exit normally"
                        )
                except Exception as e:
                    self.logger.error(f"Error handling thread {thread.name}: {e}")
        
        # 检查最终状态
        still_alive = [t for t in self.threads if t.is_alive()]
        if still_alive:
            self.logger.error(
                f"Warning: {len(still_alive)} threads may not be fully cleaned up"
            )
        else:
            self.logger.info("✅ All device threads exited safely")
        
        self.logger.info("Program shutdown completed")
    
    def monitor_devices(self):
        """监控设备运行状态"""
        try:
            while not self.stop_event.is_set():
                active_count = sum(1 for t in self.threads if t.is_alive())
                self.logger.debug(f"Active device threads: {active_count}/{len(self.threads)}")
                time.sleep(5)
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted")