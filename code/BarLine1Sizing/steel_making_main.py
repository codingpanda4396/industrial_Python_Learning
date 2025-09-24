from utils.s7data import S7Client, S7data
from dbutils.pooled_db import PooledDB
from utils.logger import Logger
from models.data_sender import Sender
from models.mysql_data import MysqlData
import pymysql

# 配置S7连接
s7_1 = S7Client()
s7_1.connect("172.16.1.20", 0, 0)
data_1 = S7data("conf/s7@172.16.1.20.csv")
data_1.set_S7Client(s7_1)
data_1.auto_update_group()

s7_2 = S7Client()
s7_2.connect("172.16.1.21", 0, 0)
data_2 = S7data("conf/s7@172.16.1.21.csv")
data_2.set_S7Client(s7_2)
data_2.auto_update_group()

s7_3 = S7Client()
s7_3.connect("192.168.1.215", 0, 0)
data_3 = S7data("conf/s7@192.168.1.215.csv")
data_3.set_S7Client(s7_3)
data_3.auto_update_group()

s7_4 = S7Client()
s7_4.connect("192.168.1.215", 0, 0)

# 配置MySQL连接池
mysql_pool = PooledDB(
    creator=pymysql,
    maxconnections=60,
    mincached=2,
    blocking=True,
    host='localhost',
    user='root',
    password='qwer1234',
    database='steelmaking_data',
    charset='utf8mb4'
)

mysql_pool_web = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=1,
    blocking=True,
    host='192.168.3.165',
    user='zgzt',
    password='zgzt1234',
    database='lg_length',
    charset='utf8mb4'
)

# 配置日志模块
logger = Logger('steel_making')
logger.file_on_with_rotation('logs/steel_making.log')
# logger.screen_on()

# 配置主模块
sender_1 = Sender(data_1, mysql_pool, logger, "172.16.1.20")
sender_2 = Sender(data_2, mysql_pool, logger, "172.16.1.21")
sender_3 = Sender(data_3, mysql_pool, logger, "192.168.1.215")

# Mysql数据源
data_mysql = MysqlData(mysql_pool_web, s7_4, logger)
