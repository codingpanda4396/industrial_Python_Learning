from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
import json
import logging
import threading
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置数据库连接字符串
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:439695@192.168.56.10:3306/Light?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Lamp(db.Model):
    __tablename__ = 'tb_lamp'  # 明确指定表名
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.String(50), nullable=False, unique=True, comment='设备ID')
    status = db.Column(db.Integer, default=0, comment='1：上线 0：下线')
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f'<Lamp {self.deviceId}>'
    
class LampStatus(db.Model):
    __tablename__ = 'tb_lamp_status'  # 明确指定表名
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.String(50), nullable=False, comment='设备ID')
    status = db.Column(db.Integer, default=0, comment='0: 关灯 1：开灯')
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f'<LampStatus device:{self.deviceId}, status:{"开灯" if self.status == 1 else "关灯"}>'

MQTT_BROKER_URL = '192.168.56.10'
MQTT_BROKER_PORT = 1883
MQTT_USERNAME = 'panda'
MQTT_PASSWORD = '439695'
# 创建一个唯一的客户端ID，避免冲突
MQTT_CLIENT_ID = f'flask_light_server_{int(time.time())}'

# 创建 Paho MQTT 客户端实例
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)

# 设置用户名和密码
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# MQTT 回调函数
def on_connect(client, userdata, flags, rc):
    """ 当 broker 响应连接请求时调用 """
    if rc == 0:
        print("MQTT 连接成功！")
        # 订阅主题
        client.subscribe("device/+/online", qos=1)
        client.subscribe("device/+/state", qos=1)
        client.subscribe("device/+/command/response", qos=1)
        print("已订阅主题: device/+/online, device/+/state, device/+/command/response")
    else:
        print(f"MQTT 连接失败，状态码: {rc}")

def on_message(client, userdata, msg):
    """ 当从 broker 收到消息时调用 """
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"DEBUG [on_message]: 收到消息! Topic: '{topic}', Payload: '{payload}'")

    try:
        data = json.loads(payload)#尝试解析json数据
        device_id = data.get('device_id')
        
        if not device_id:
            print("错误：消息中缺少 device_id")# 核验核心数据
            return
            
        # 处理设备上线消息
        if topic.endswith('/online'):#确认是上线topic
            status = data.get('status')
            with app.app_context():# 确保在Flask应用上下文中操作数据库
                lamp = Lamp.query.filter_by(deviceId=device_id).first()#查询到deviceId对应的第一行
                if lamp:
                    lamp.status = 1 if status == 'online' else 0
                    lamp.update_time = datetime.now()
                else:
                    lamp = Lamp(deviceId=device_id, status=1 if status == 'online' else 0)
                    db.session.add(lamp)
                db.session.commit()
                print(f"设备 {device_id} 上线状态已更新")
        
        # 处理设备状态消息（开关状态）
        elif topic.endswith('/state'):
            lamp_status = data.get('status')
            status_code = 1 if lamp_status == 'on' else 0
            with app.app_context():
                new_status = LampStatus(deviceId=device_id, status=status_code)
                db.session.add(new_status)
                db.session.commit()
                print(f"设备 {device_id} 开关状态已记录: {lamp_status}")
            
        # 处理设备指令响应（可选）
        elif topic.endswith('/command/response'):
            command = data.get('received_command')
            result = data.get('result')
            print(f"设备 {device_id} 对指令 '{command}' 的响应: {result}")
            
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
    except Exception as e:
        print(f"处理消息时发生错误: {e}")

# 设置回调函数
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# 连接到 MQTT 代理并启动网络循环（在后台线程）
try:
    print("正在尝试连接到 MQTT Broker...")
    mqtt_client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, 60)
    # 启动网络循环（非阻塞）
    mqtt_client.loop_start()
    print("MQTT 网络循环已启动。")
except Exception as e:
    print(f"连接 MQTT Broker 时发生错误: {e}")

# RESTful API 接口
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/device/<device_id>/command', methods=['POST'])
def send_command(device_id):
    """向指定设备发送控制指令"""
    command_data = request.get_json()
    if not command_data:
        return jsonify({'error': '缺少JSON数据'}), 400
        
    command = command_data.get('command')
    if command not in ['on', 'off']:  # 简单的指令验证
        return jsonify({'error': '指令必须是 on 或 off'}), 400
        
    # 构建MQTT消息
    topic = f'device/{device_id}/command'
    message = json.dumps({
        'device_id': device_id,
        'command': command,
        'timestamp': datetime.now().isoformat()
    })
    
    # 发布消息
    publish_result = mqtt_client.publish(topic, message, qos=0)
    return jsonify({
        'message': '指令已发送',
        'topic': topic,
        'mqtt_result_code': publish_result[0]
    })

@app.route('/api/devices', methods=['GET'])
def get_all_devices():
    """获取所有设备及其最新状态"""
    with app.app_context():  # 确保在应用上下文中操作数据库
        devices = Lamp.query.all()
        result = []
        for device in devices:
            # 获取该设备的最新一条状态记录
            latest_status = LampStatus.query.filter_by(deviceId=device.deviceId).order_by(LampStatus.create_time.desc()).first()
            result.append({
                'device_id': device.deviceId,
                'online_status': device.status,
                'last_online_update': device.update_time.isoformat() if device.update_time else None,
                'light_status': latest_status.status if latest_status else None,
                'last_light_status_update': latest_status.create_time.isoformat() if latest_status else None
            })
        return jsonify({'devices': result})

@app.route('/api/device/<device_id>/status-history', methods=['GET'])
def get_device_status_history(device_id):
    """获取指定设备的状态历史记录"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    with app.app_context():  # 确保在应用上下文中操作数据库
        # 分页查询状态历史
        status_history = LampStatus.query.filter_by(deviceId=device_id).order_by(LampStatus.create_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        history_list = []
        for status in status_history.items:
            history_list.append({
                'status': status.status,
                'create_time': status.create_time.isoformat()
            })
        
        return jsonify({
            'device_id': device_id,
            'history': history_list,
            'total_pages': status_history.pages,
            'current_page': page,
            'total_items': status_history.total
        })

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '资源不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()  # 发生错误时回滚数据库会话
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    # 禁用调试器和重载器，避免干扰
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)