"""主程序入口"""
import sys
import threading
import time
from config.settings import AppConfig, MQTTConfig
from utils.logger import setup_logging
from core.managers import DeviceManager

def main():
    """主函数"""
    # 配置应用设置
    config = AppConfig(
        mqtt=MQTTConfig(
            broker='192.168.56.10',
            port=1883,
            username=None,  # 根据需要设置
            password=None   # 根据需要设置
        ),
        device_count=20,
        default_interval=15,
        log_level="INFO"
    )
    
    # 设置日志
    logger = setup_logging(config)
    
    try:
        # 创建设备管理器
        manager = DeviceManager(config, logger)
        
        # 创建设备实例
        manager.create_devices()
        
        # 启动所有设备
        manager.start_all()
        
        # 启动监控
        monitor_thread = threading.Thread(
            target=manager.monitor_devices,
            name="DeviceMonitorThread",
            daemon=True
        )
        monitor_thread.start()
        
        # 等待所有线程完成
        try:
            while any(thread.is_alive() for thread in manager.threads):
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("\nInterrupt detected again, accelerating shutdown...")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        manager.stop_all()

if __name__ == "__main__":
    main()