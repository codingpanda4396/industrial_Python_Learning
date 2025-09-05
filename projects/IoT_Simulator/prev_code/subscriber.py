import json
import logging
from time import sleep
import paho.mqtt.client as mqtt
import pymysql
from dbutils.pooled_db import PooledDB


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BROKER = '192.168.56.10'
PORT = 1883
QOS = 1
DATA_TOPIC=f"factory/+/+/data"
STATUS_TOPIC=f"factory/+/+/status"

# 数据库连接池配置
db_pool = PooledDB(
    creator=pymysql,
    host='192.168.56.10',
    port=3306,
    user='root',
    password='439695',
    database='task1_mqtt_device',
    mincached=2,      # 初始空闲连接数
    maxcached=5,      # 最大空闲连接数
    maxconnections=10, # 最大连接数
    blocking=True,    # 超过最大连接数时阻塞等待
    charset='utf8mb4'
)

def on_connect(client, userdata, flags, rc):#与服务器连接时执行的回调
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(DATA_TOPIC)
        client.subscribe(STATUS_TOPIC)
        print(f"Subscribe {DATA_TOPIC}!")
        print(f"Subscribe {STATUS_TOPIC}!")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):#收到消息时执行的回调
    """
    MQTT消息回调函数，处理设备数据并存储到数据库
    
    Args:
        client: MQTT客户端实例
        userdata: 用户数据--自定义的数据
        msg: MQTT消息对象，包含topic和payload
    """
    try:
        payload=msg.payload.decode('utf-8')
        data= json.loads(payload)
        logger.info(f"收到来自主题 [{msg.topic}] 的消息")
        
        
    
         # 存储设备数据和状态
        try:
            store_device_data(msg.topic,data)
            logger.info(f"设备 {data.get("deviceId")} 数据存储成功")
            
        except Exception as db_error:
            logger.error(f"数据库操作失败: {db_error}")
            
    except json.JSONDecodeError as json_error:
        logger.error(f"JSON解析失败: {json_error}, 原始数据: {msg.payload}")
    except UnicodeDecodeError as decode_error:
        logger.error(f"消息解码失败: {decode_error}")
    except Exception as unexpected_error:
        logger.error(f"处理消息时发生意外错误: {unexpected_error}")

def store_device_data(topic:str,data) -> None:
    """
    存储设备数据和状态到数据库
    
    Args:
        device_id: 设备ID
        device_type: 设备类型
        device_status: 设备状态
    """
    device_id=data.get("deviceId")
    device_type=data.get("deviceType")
    device_status=data.get("status")
    temperature=data.get("metrics")["temperature"]
    pressure=data.get("metrics")["pressure"]
    vibration=data.get("metrics")["vibration"]
    output=data.get("metrics")["output"]
    efficiency=data.get("metrics")["efficiency"]
    
    
    cpu_usage=data.get("telemetry")["cpuUsage"]
    memory_usage=data.get("telemetry")["memoryUsage"]
    uptime=data.get("telemetry")["uptime"]

    # 使用数据库连接池获取连接
    with db_pool.connection() as conn:
        with conn.cursor() as cursor:
            


            # 插入设备基本信息
            device_sql = """
                INSERT INTO devices (device_id, device_type)
                VALUES (%s, %s)
            """
            if topic.endswith('data'):
                cursor.execute(device_sql, (device_id, device_type))
            
            # 插入设备状态信息
            status_sql = """
                INSERT INTO device_status (device_id, device_status)
                VALUES (%s, %s)
            """
            metric_sql = """
                INSERT INTO device_metrics (status_id,temperature,pressure,vibration,output,efficiency)
                VALUES (%s, %s,%s,%s,%s,%s)
            """
            telemetry_sql = """
                INSERT INTO device_telemetry (status_id,cpu_usage,memory_usage,uptime)
                VALUES (%s, %s,%s,%s)
            """
            if topic.endswith("status"):
                cursor.execute(status_sql, (device_id, device_status))
                status_id=cursor.lastrowid
                cursor.execute(metric_sql,(status_id,temperature,pressure,vibration,output,efficiency))
                cursor.execute(telemetry_sql,(status_id,cpu_usage,memory_usage,uptime))
            # 提交事务
            conn.commit()

def Suber(device_id):

    #创建客户端并连接mqtt服务器
    client_id = f"client_{device_id}"
    client= mqtt.Client(client_id)
    client.on_connect=on_connect
    client.on_message=on_message
    #连接
    client.connect(BROKER,PORT)
    client.loop_forever()


if __name__=="__main__":
    Suber("001")
