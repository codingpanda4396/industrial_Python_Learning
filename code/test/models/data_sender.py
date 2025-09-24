from utils.s7data import S7data
from utils.logger import Logger
from dbutils.pooled_db import PooledDB
from datetime import datetime
import pymysql, threading, time

class Sender:
    def __init__(self, s7data: S7data, mysql_pool: PooledDB, logger: Logger, ipaddr):
        self.s7data = s7data
        self.mysql_pool = mysql_pool
        self.logger = logger
        self.point_info = self.get_init_node_info(ipaddr)

        self.thread_run = True
        self.thread = threading.Thread(target=self.update_all_forever)
        self.thread.start()

    def __del__(self):
        if isinstance(self.thread, threading.Thread) and self.thread.is_alive():
            self.thread_run = False
            self.thread.join()

    def update_all_forever(self, round_sleep=500):
        while self.thread_run:
            time.sleep(round_sleep/1000)
            threads = []
            for i in self.point_info.keys():
                thread = threading.Thread(target=self.update_point, args=(i,))
                thread.start()
                threads.append(thread)
            for i in threads:
                i.join()
            self.logger.debug("更新成功")

    def update_point(self, name):
        dataid = self.point_info[name][1]
        datatype = self.point_info[name][2]
        datatype = datatype if datatype != 'dint' else 'int'
        timestamp = datetime.now()
        datavalue = self.s7data.get_value(name)
        sql = "UPDATE realtime_data SET {}_value = %s, timestamp = %s WHERE point_id = %s;".format(datatype)
        sql2 = "INSERT INTO historical_data(point_id, {}_value, timestamp) VALUES(%s, %s, %s);".format(datatype)
        sql3 = "INSERT INTO recent_data(point_id, {}_value, timestamp) VALUES(%s, %s, %s);".format(datatype)
        with self.mysql_pool.connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (datavalue, timestamp, dataid))
                    cursor.execute(sql2, (dataid, datavalue, timestamp))
                    # cursor.execute(sql3, (dataid, datavalue, timestamp))
                    conn.commit()
                    return True
            except pymysql.Error as e:
                self.logger.error(f"[SENDER]MYSQL:{e}")

    def get_init_node_info(self, ipaddr):
        sql = "SELECT name, id, type FROM data_points where ip_address = %s;"
        res_dict = {}
        with self.mysql_pool.connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (ipaddr,))
                    res = cursor.fetchall()
            except pymysql.Error as e:
                self.logger.error(f"[SENDER]MYSQL:{e}")
                raise ConnectionError("mysql connection error."+str(e))
        for i in res:
            res_dict[i[0]] = i
        
        return res_dict

    def upload_billet(self, arg_dict: dict):
        sql = "INSERT INTO steel_billet_monitoring(strand_no, cutting_time, entry_time, exit_time, \
                water_temperature, water_pressure, water_volume, water_pressure_sd, steel_temperature, \
                drawing_speed, water_temperature_difference)\
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        with self.mysql_pool.connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (arg_dict["strand_no"], arg_dict["cutting_time"], arg_dict["entry_time"], arg_dict["exit_time"],
                                         arg_dict.get("water_temperature"), arg_dict.get("water_pressure"), arg_dict.get("water_volume"), arg_dict.get("water_pressure_sd"),
                                         arg_dict.get("steel_temperature"), arg_dict.get("drawing_speed"), arg_dict.get("water_temperature_difference")))
                    conn.commit()
                    return True
            except pymysql.Error as e:
                self.logger.error(f"[SENDER]MYSQL:{e}")
