"""日志系统配置"""
import logging
import logging.config
from typing import Optional
from config.settings import AppConfig

def setup_logging(config: AppConfig) -> logging.Logger:
    """配置并返回日志记录器"""
    
    logging_config = {
        'version': 1, #标识配置架构的版本
        'disable_existing_loggers': False, #避免禁用已存在的日志记录器
        'formatters': {#日志输出格式
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
            }
        },
        'handlers': {#输出目标和处理方式
            'console': {
                'class': 'logging.StreamHandler',   
                'level': config.log_level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': config.log_level,
                'formatter': 'detailed',
                'filename': config.log_file,
                'mode': 'a',
                'encoding': 'utf-8'
            }
        },
        'loggers': {#日志记录器的配置
            '': {
                'handlers': ['console', 'file'],
                'level': config.log_level,
                'propagate': True
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    return logging.getLogger('iot_simulator')