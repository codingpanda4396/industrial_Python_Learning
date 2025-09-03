import paho.mqtt.client as mqtt
import time

broker = "localhost"
port = 1883
username = "guest"
password = "guest"
topic = "test/topic"

def on_connect(client, userdata, flags, rc):
    print(f"连接结果代码: {rc}")
    if rc == 0:
        print("连接成功，开始订阅...")
        client.subscribe(topic)
    else:
        print("连接失败")

def on_message(client, userdata, msg):
    print(f"\n收到消息: {msg.payload.decode()}")
    print(f"主题: {msg.topic}, QoS: {msg.qos}")

# 创建客户端
client = mqtt.Client()
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_message = on_message

print("正在连接到MQTT服务器...")
client.connect(broker, port)

print("开始监听消息，按 Ctrl+C 退出...")
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n断开连接...")
    client.disconnect()