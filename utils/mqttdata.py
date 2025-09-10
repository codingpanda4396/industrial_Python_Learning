import paho.mqtt.client as mqtt
import json, warnings
from utils.statepoint import *

class MqttClient(mqtt.Client):
    def __init__(self, client_id, username=None, password=None, version=mqtt.CallbackAPIVersion.VERSION2):
        super().__init__(version, client_id)

        if username and password:
            self.username_pw_set(username, password)

class Mqttdata:
    def __init__(self):
        self.logger = None

        self.thread = None #维护MQTT客户端循环的线程
        self.node_data = {'5#开浇信号': {}, '5#停浇信号': {}, '6#开浇信号': {}, '6#停浇信号': {}, '5#手动换炉': {}, '6#手动换炉': {}}
        self.target_from_name = {}#名称-目标对象的映射

    def set_logger(self, logger):# 允许外部注入日志记录器
        self.logger = logger

    def set_mqtt_client(self, cli): 
        self.cli = cli 
        #接收客户端实例并设置回调函数
        self.cli.on_connect = self.on_connect
        self.cli.on_message = self.on_message
        #订阅两个主题
        self.cli.subscribe('data/service/cast/info', qos=2)
        self.cli.subscribe('syn/pushbillethotsend/nexthosend', qos=2)

    def start_auto_update(self):
        if self.thread == None:
            # 启动独立线程运行MQTT客户端消息循环
            self.thread = threading.Thread(target=self.cli.loop_forever)
        self.thread.start()

    def send(self, name):
        if name in self.target_from_name:
            #根据名称找到对应目标对象 调用每个目标的inject方法
            for i in self.target_from_name[name]:
                i.inject(self.node_data[name])
                #五秒后调用set_state（False）的定时器
                timer = threading.Timer(5, lambda i=i: i.set_state(False))
                timer.start()
        
    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        if reason_code_list[0].is_failure:
            warnings.warn(f"Broker rejected your subscription: {reason_code_list[0]}")
            if self.logger:
                self.logger.error(f"Broker rejected your subscription: {reason_code_list[0]}")
        else:
            if self.logger:
                self.logger.info(f"Broker granted the following QoS: {reason_code_list[0].value}")

    def on_message(self, client, userdata, message):
        # logger.debug(message.payload.decode())
        topic = message.topic
        if topic == 'syn/pushbillethotsend/nexthosend':
            data = json.loads(message.payload.decode())
            if 'ccmNo' not in data:
                warnings.warn('[MES]MQTT报文格式错误')
                if self.logger:
                    self.logger.error('[MES]MQTT报文格式错误')
                return None
            if int(data['ccmNo']) == 6:
                if data != self.node_data['6#手动换炉']:
                    self.node_data['6#手动换炉'] = data
                    self.send('6#手动换炉')
            elif int(data['ccmNo']) == 5:
                if data != self.node_data['5#手动换炉']:
                    self.node_data['5#手动换炉'] = data
                    self.send('5#手动换炉')
            else:
                warnings.warn('[MES]MQTT收到未知铸机号')
                if self.logger:
                    self.logger.error('[MES]MQTT收到未知铸机号')
        elif topic == 'data/service/cast/info':
            data = json.loads(message.payload.decode())
            if 'ccmNo' not in data or 'castState' not in data:
                warnings.warn('[MES]MQTT报文格式错误')
                if self.logger:
                    self.logger.error('[MES]MQTT报文格式错误')
                return None
            if int(data['ccmNo']) == 6:
                if data['castState'] and data != self.node_data['6#开浇信号']:
                    self.node_data['6#开浇信号'] = data
                    self.send('6#开浇信号')
                elif not data['castState'] and data != self.node_data['6#停浇信号']:
                    self.node_data['6#停浇信号'] = data
                    self.send('6#停浇信号')
            elif int(data['ccmNo']) == 5:
                if data['castState'] and data != self.node_data['5#开浇信号']:
                    self.node_data['5#开浇信号'] = data
                    self.send('5#开浇信号')
                elif not data['castState'] and data != self.node_data['5#停浇信号']:
                    self.node_data['5#停浇信号'] = data
                    self.send('5#停浇信号')
            else:
                warnings.warn('[MES]MQTT收到未知铸机号')
                if self.logger:
                    self.logger.error('[MES]MQTT收到未知铸机号')

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            warnings.warn(f"Failed to connect: {reason_code}. loop_forever() will retry connection")
            if self.logger:
                self.logger.error(f"Failed to connect: {reason_code}. loop_forever() will retry connection")
        else:
            client.subscribe('data/service/cast/info', qos=2)
            client.subscribe('syn/pushbillethotsend/nexthosend', qos=2)
            if self.logger:
                self.logger.info("MQTT connection succeeded")

    def make_point(self, name):
        if name not in self.node_data:
            raise ValueError("创建了未配置的点")
        if name not in self.target_from_name: 
            self.target_from_name[name] = []
        res = Statepoint()
        self.target_from_name[name].append(res)
        return res
