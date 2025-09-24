from utils.s7data import S7Client, S7data
from dbutils.pooled_db import PooledDB
from utils.logger import Logger
from models.data_sender import Sender
import pymysql

# 配置S7连接
s7 = S7Client()
s7.connect("192.168.0.3", 0, 3)
data = S7data("conf/s7@192.168.0.3.csv")
data.set_S7Client(s7)
data.auto_update_group()

# 配置MySQL连接池
mysql_pool = PooledDB(
    creator=pymysql,
    maxconnections=40,
    mincached=2,
    blocking=True,
    host='localhost',
    user='root',
    password='5538..',
    database='industrial_data',
    charset='utf8mb4'
)

# 配置日志模块
logger = Logger('steel_rolling')
logger.file_on_with_rotation('logs/steel_rolling.log')
logger.screen_on()

# 配置主模块
sender = Sender(data, mysql_pool, logger, "192.168.0.3")