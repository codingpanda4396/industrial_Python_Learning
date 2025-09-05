import mqtt from 'mqtt'
import { EventEmitter } from 'events'

class MQTTClient extends EventEmitter {
  constructor() {
    super()
    this.client = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
  }

  connect(brokerUrl, options = {}) {
    const defaultOptions = {
      clientId: `web-client_${Math.random().toString(16).substr(2, 8)}`,
      clean: true,
      reconnectPeriod: 2000,
      connectTimeout: 3000
    }

    const connectOptions = { ...defaultOptions, ...options }
    
    try {
      this.client = mqtt.connect(brokerUrl, connectOptions)
      
      this.client.on('connect', () => {
        this.isConnected = true
        this.reconnectAttempts = 0
        this.emit('connected')
        console.log('MQTT Connected successfully')
        
        // 订阅设备相关主题
        this.subscribe('factory/+/+/data')
        this.subscribe('factory/+/+/status')
        this.subscribe('factory/lwt/+')
      })

      this.client.on('message', (topic, message) => {
        this.handleMessage(topic, message)
      })

      this.client.on('reconnect', () => {
        this.reconnectAttempts++
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
      })

      this.client.on('error', (error) => {
        console.error('MQTT Error:', error)
        this.emit('error', error)
      })

      this.client.on('close', () => {
        this.isConnected = false
        this.emit('disconnected')
      })

    } catch (error) {
      console.error('MQTT Connection failed:', error)
      throw error
    }
  }

  subscribe(topic, qos = 1) {
    if (this.client && this.isConnected) {
      this.client.subscribe(topic, { qos }, (err) => {
        if (err) {
          console.error('Subscribe error:', err)
        } else {
          console.log(`Subscribed to ${topic}`)
        }
      })
    }
  }

  unsubscribe(topic) {
    if (this.client && this.isConnected) {
      this.client.unsubscribe(topic, (err) => {
        if (err) {
          console.error('Unsubscribe error:', err)
        }
      })
    }
  }

  handleMessage(topic, message) {
    try {
      const payload = message.toString()
      const data = JSON.parse(payload)
      
      // 提取设备ID和生产线信息
      const topicParts = topic.split('/')
      const line = topicParts[1]
      const deviceId = topicParts[2]
      const messageType = topicParts[3]

      const processedData = {
        ...data,
        topic,
        line,
        deviceId,
        messageType,
        timestamp: new Date().toISOString()
      }

      this.emit('message', processedData)
      
      // 根据消息类型分发到不同事件
      if (messageType === 'status') {
        this.emit('status-update', processedData)
      } else if (messageType === 'data') {
        this.emit('data-update', processedData)
      } else if (topic.includes('lwt')) {
        this.emit('device-lwt', processedData)
      }

    } catch (error) {
      console.error('Message processing error:', error)
      this.emit('message-error', { topic, message, error })
    }
  }

  disconnect() {
    if (this.client) {
      this.client.end(true)
      this.isConnected = false
    }
  }

  getConnectionStatus() {
    return this.isConnected
  }
}

export default new MQTTClient()