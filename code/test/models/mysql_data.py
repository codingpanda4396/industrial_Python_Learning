import time, threading, snap7.util
from utils.s7data import S7Client
from utils.logger import Logger
from dbutils.pooled_db import PooledDB


class MysqlData:
    """mysql与PLC的数据交互"""
    def __init__(self, mysql_pool: PooledDB, s7conn: S7Client, logger: Logger):
        self.mysql_pool = mysql_pool
        self.s7conn = s7conn
        self.logger = logger
        self.datas = {"is_use_model": False, "is_use_length": False, "棒一变棒三定尺": False}
        self.model_datas = [0 for i in range(8)]

        self.thread_flag = True
        self.thread = threading.Thread(target=self.update_forever)
        self.thread.start()
        self.thread_write = threading.Thread(target=self.write_forever)
        self.thread_write.start()
    
    def get_value(self, name, default=0):
        if name == "棒一变棒三定尺":
            sql = f"SELECT bool_value from industrial_data.realtime_data WHERE point_id = 64;"
        else:
            sql = f"SELECT {name} from length_config;"
        try:
            with self.mysql_pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    result = cursor.fetchall()
            if len(result) == 0:
                raise ValueError("Read no data from mysql.")
            return result[0][0]
        except Exception as e:
            self.logger.error(f"[mysql]:{e}")
            return default
        
    def get_model_value(self, strand_no, default=0):
        sql = f"SELECT model_compensation FROM prediction_full_data.prediction{strand_no}_full_data WHERE model_compensation IS NOT NULL ORDER BY prediction_timestamp DESC LIMIT 1;"
        try:
            with self.mysql_pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    result = cursor.fetchall()
            if len(result) == 0:
                raise ValueError("Read no data from mysql.")
            return result[0][0]
        except Exception as e:
            self.logger.error(f"[mysql]:{e}")
            return default
        
    def update_forever(self, fru=500):
        while self.thread_flag:
            for i in self.datas.keys():
                self.datas[i] = self.get_value(i)
            for i in range(8):
                self.model_datas[i] = self.get_model_value(i+1)
            time.sleep(fru/1000)

    def write_forever(self, fru=500):
        while self.thread_flag:
            data = bytearray(1)
            snap7.util.set_bool(data, 0, 1, self.datas["is_use_model"])
            snap7.util.set_bool(data, 0, 0, not self.datas["棒一变棒三定尺"])
            snap7.util.set_bool(data, 0, 3, self.datas["棒一变棒三定尺"])
            self.s7conn.db_write(420, 32, data)
            self.s7conn.db_write(421, 32, data)

            data = bytearray(32)
            for i in range(8):
                snap7.util.set_real(data, i*4, self.model_datas[i])
            self.s7conn.db_write(420, 0, data)
            self.s7conn.db_write(421, 0, data)

            time.sleep(fru/1000)