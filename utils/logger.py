import logging
from logging.handlers import RotatingFileHandler

class Logger(logging.Logger):
    def __init__(self, name):
        super().__init__(name)

        self.setLevel(level=logging.DEBUG)
        self.format_default = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        self.console = None
        self.handler = None

    def screen_on(self, level=logging.DEBUG, format=None):
        if self.console:
            return None
        
        if format == None:
            #支持自定义格式
            formatter = logging.Formatter(self.format_default)
        else:
            formatter = logging.Formatter(format)

        self.console = logging.StreamHandler()
        self.console.setLevel(level)#支持自定义级别
        self.console.setFormatter(formatter)        
        self.addHandler(self.console)

    def file_on(self, path='log.txt', level=logging.DEBUG, format=None):
        if self.handler:
            return None
        
        if format == None:
            formatter = logging.Formatter(self.format_default)
        else:
            formatter = logging.Formatter(format)

        self.handler = logging.FileHandler(path)
        self.handler.setLevel(level)
        self.handler.setFormatter(formatter)
        self.addHandler(self.handler)

    def file_on_with_rotation(self, path='log.txt', level=logging.DEBUG, format=None, maxBytes=8*1024*1024, backupCount=3):
        if self.handler:
            return None
        
        if format == None:
            formatter = logging.Formatter(self.format_default)
        else:
            formatter = logging.Formatter(format)

        self.handler = RotatingFileHandler(
            path, 
            maxBytes=maxBytes,
            backupCount=backupCount
        )
        self.handler.setLevel(level)
        self.handler.setFormatter(formatter)
        self.addHandler(self.handler)