from time import time
from logging import Logger
import logging
from logging import FileHandler, StreamHandler, Formatter

class DataLogger:
    """记录监控数据，使用 logging 模块写入文件并输出到控制台"""
    def __init__(self, log_file: str = 'plc_alarm_log.txt', logger_name: str = 'alarmer'):
        self.log_file = log_file
        self.logger = logging.getLogger(logger_name)
        # 防止重复添加 handler（多次实例化时）
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            fh = FileHandler(self.log_file, encoding='utf-8')
            sh = StreamHandler()
            fmt = Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            fh.setFormatter(fmt)
            sh.setFormatter(fmt)
            self.logger.addHandler(fh)
            self.logger.addHandler(sh)

    def log_message(self, message: str, level: str = 'info'):
        """将消息记录到日志文件和控制台。level 支持: debug, info, warning, error, critical"""
        level = (level or 'info').lower()
        if level == 'debug':
            self.logger.debug(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        elif level == 'critical':
            self.logger.critical(message)
        else:
            self.logger.info(message)