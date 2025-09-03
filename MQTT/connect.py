import paho.mqtt.client  as mqtt

# 连接参数
broker = "localhost"  # 或者 "127.0.0.1"
port = 1883
username = "guest"    # RabbitMQ默认用户名
password = "guest"    # RabbitMQ默认密码
topic = "test/topic"  # 你要发布/订阅的主题

# 创建客户端实例
client = mqtt.Client()
client.username_pw_set(username, password)  # 设置认证信息

# 连接回调函数
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("成功连接到MQTT服务器！")
        # 连接成功后订阅主题
        client.subscribe(topic)
    else:
        print(f"连接失败，错误代码: {rc}")

# 消息接收回调函数
def on_message(client, userdata, msg):
    print(f"收到消息: {msg.payload.decode()} [主题: {msg.topic}]")

# 设置回调函数
client.on_connect = on_connect
client.on_message = on_message

# 连接到服务器
client.connect(broker, port)

# 保持连接并处理消息
client.loop_forever()