import paho.mqtt.client as mqtt
import json

broker = "localhost"
port = 1883
username = "guest"
password = "guest"
topic = "test/topic"

client = mqtt.Client()
client.username_pw_set(username, password)
client.connect(broker, port)

# 发送简单消息
message = "Hello, MQTT from Python!"
client.publish(topic, message)
print(f"已发送消息: {message}")

# 发送JSON数据
data = {"sensor": "temperature", "value": 23.5, "unit": "celsius"}
json_message = json.dumps(data)
client.publish(topic, json_message)
print(f"已发送JSON消息: {json_message}")


client.publish(topic,"here is another Pub")

client.disconnect() 