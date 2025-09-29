import pymysql
from utils.s7util import Logger
from dbutils.pooled_db import PooledDB

class Persistence():
    def __init__(self):
        self.logger=Logger(__name__)
        self.logger.file_on()
        self.logger.screen_on()

        self.pool=PooledDB(
            creator=pymysql,          # 使用pymysql作为底层连接创建器
            maxconnections=60,       # 连接池允许的最大连接数
            mincached=2,             # 初始化时创建的闲置连接数
            blocking=True,           # 当连接池耗尽时是否阻塞等待
            host='localhost',        # 数据库服务器地址
            user='root',             # 数据库用户名
            password='qwer1234',     # 数据库密码
            database='steelmaking_data_2',  
            charset='utf8mb4'        # 字符编码
        )

    #i：流号   avg_params：{name:平均值}    
    def save_flow_event(self,i,cutting_time, t0, t2,water_temperature, water_pressure,water_volume, water_pressure_sd, steel_temperature,drawing_speed, water_temperature_difference):
        # self.logger.info(f"""{i+1}流
        #                     进入时间:{t0}
        #                     出前12m时间:{t2}
        #                     总水量:{total_water}
        #                     各参数平均值：{avg_params}
        #                     平均流量：{avg_flow_rate}
        #                  """)
        sql = "INSERT INTO steel_billet_monitoring(strand_no, cutting_time, entry_time, exit_time, \
                water_temperature, water_pressure, water_volume, water_pressure_sd, steel_temperature, \
                drawing_speed, water_temperature_difference)\
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        with self.pool.connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql,i,cutting_time, t0, t2,water_temperature, water_pressure,water_volume, water_pressure_sd, steel_temperature,drawing_speed, water_temperature_difference)
                    conn.commit()
                    return True
            except pymysql.Error as e:
                self.logger.error(f"[SENDER]MYSQL:{e}")