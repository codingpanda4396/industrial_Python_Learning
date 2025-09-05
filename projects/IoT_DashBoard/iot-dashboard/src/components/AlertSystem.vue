<template>
    <div class="alert-system">
      <h3>设备告警系统</h3>
      
      <div class="alert-config">
        <h4>告警规则配置</h4>
        <div class="rule-form">
          <select v-model="newRule.metric">
            <option value="temperature">温度</option>
            <option value="pressure">压力</option>
            <option value="vibration">振动</option>
            <option value="cpuUsage">CPU使用率</option>
          </select>
          
          <select v-model="newRule.condition">
            <option value="gt">大于</option>
            <option value="lt">小于</option>
            <option value="eq">等于</option>
          </select>
          
          <input type="number" v-model="newRule.threshold" placeholder="阈值">
          
          <select v-model="newRule.severity">
            <option value="warning">警告</option>
            <option value="error">错误</option>
            <option value="critical">严重</option>
          </select>
          
          <button @click="addRule">添加规则</button>
        </div>
      </div>
  
      <div class="active-alerts">
        <h4>活跃告警 ({{ activeAlerts.length }})</h4>
        <div class="alerts-list">
          <div 
            v-for="alert in activeAlerts" 
            :key="alert.id"
            :class="['alert-item', alert.severity]"
          >
            <div class="alert-content">
              <span class="alert-title">{{ alert.deviceId }} - {{ alert.metric }}</span>
              <span class="alert-message">{{ alert.message }}</span>
              <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
            </div>
            <button @click="acknowledgeAlert(alert.id)">确认</button>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { ref, onMounted, onUnmounted } from 'vue'
  import mqttClient from '@/services/mqttClient'
  
  export default {
    name: 'AlertSystem',
    
    setup() {
      const alertRules = ref([
        {
          id: 1,
          metric: 'temperature',
          condition: 'gt',
          threshold: 80,
          severity: 'warning',
          message: '温度过高'
        },
        {
          id: 2,
          metric: 'cpuUsage',
          condition: 'gt',
          threshold: 90,
          severity: 'error',
          message: 'CPU使用率过高'
        }
      ])
  
      const activeAlerts = ref([])
      const newRule = ref({
        metric: 'temperature',
        condition: 'gt',
        threshold: 0,
        severity: 'warning'
      })
  
      const checkAlerts = (data) => {
        alertRules.value.forEach(rule => {
          let value
          if (data.metrics[rule.metric] !== undefined) {
            value = data.metrics[rule.metric]
          } else if (data.telemetry[rule.metric] !== undefined) {
            value = data.telemetry[rule.metric]
          }
  
          if (value !== undefined) {
            let shouldAlert = false
            
            switch (rule.condition) {
              case 'gt':
                shouldAlert = value > rule.threshold
                break
              case 'lt':
                shouldAlert = value < rule.threshold
                break
              case 'eq':
                shouldAlert = Math.abs(value - rule.threshold) < 0.001
                break
            }
  
            if (shouldAlert) {
              const existingAlert = activeAlerts.value.find(
                alert => alert.deviceId === data.deviceId && 
                        alert.metric === rule.metric &&
                        !alert.acknowledged
              )
  
              if (!existingAlert) {
                const alert = {
                  id: Date.now(),
                  deviceId: data.deviceId,
                  deviceType: data.deviceType,
                  metric: rule.metric,
                  value: value,
                  threshold: rule.threshold,
                  condition: rule.condition,
                  severity: rule.severity,
                  message: `${data.deviceId} ${rule.message}: ${value} (阈值: ${rule.threshold})`,
                  timestamp: new Date().toISOString(),
                  acknowledged: false
                }
  
                activeAlerts.value.unshift(alert)
                
                // 触发通知
                triggerNotification(alert)
              }
            }
          }
        })
      }
  
      const triggerNotification = (alert) => {
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('设备告警', {
            body: alert.message,
            icon: '/favicon.ico'
          })
        }
      }
  
      const acknowledgeAlert = (alertId) => {
        const alert = activeAlerts.value.find(a => a.id === alertId)
        if (alert) {
          alert.acknowledged = true
          activeAlerts.value = activeAlerts.value.filter(a => !a.acknowledged)
        }
      }
  
      const addRule = () => {
        const rule = {
          id: Date.now(),
          ...newRule.value,
          message: `${newRule.value.metric} ${newRule.value.condition === 'gt' ? '过高' : '过低'}`
        }
        alertRules.value.push(rule)
        newRule.value = { metric: 'temperature', condition: 'gt', threshold: 0, severity: 'warning' }
      }
  
      const formatTime = (timestamp) => {
        return new Date(timestamp).toLocaleTimeString()
      }
  
      onMounted(() => {
        // 请求通知权限
        if ('Notification' in window) {
          Notification.requestPermission()
        }
  
        mqttClient.on('data-update', checkAlerts)
        mqttClient.on('status-update', checkAlerts)
      })
  
      onUnmounted(() => {
        mqttClient.off('data-update', checkAlerts)
        mqttClient.off('status-update', checkAlerts)
      })
  
      return {
        alertRules,
        activeAlerts,
        newRule,
        acknowledgeAlert,
        addRule,
        formatTime
      }
    }
  }
  </script>
  
  <style scoped>
  .alert-config {
    background: white;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
  }
  
  .rule-form {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  
  .rule-form select,
  .rule-form input {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
  
  .rule-form input {
    width: 80px;
  }
  
  .active-alerts {
    background: white;
    padding: 20px;
    border-radius: 8px;
  }
  
  .alerts-list {
    max-height: 400px;
    overflow-y: auto;
  }
  
  .alert-item {
    display: flex;
    justify-content: between;
    align-items: center;
    padding: 12px;
    margin-bottom: 8px;
    border-radius: 4px;
    border-left: 4px solid;
  }
  
  .alert-item.warning {
    border-left-color: #ff9800;
    background: #fff3e0;
  }
  
  .alert-item.error {
    border-left-color: #f44336;
    background: #ffebee;
  }
  
  .alert-item.critical {
    border-left-color: #d32f2f;
    background: #ffcdd2;
  }
  
  .alert-content {
    flex: 1;
  }
  
  .alert-title {
    font-weight: bold;
    display: block;
    margin-bottom: 4px;
  }
  
  .alert-message {
    display: block;
    color: #666;
    margin-bottom: 4px;
  }
  
  .alert-time {
    font-size: 12px;
    color: #999;
  }
  
  .alert-item button {
    padding: 6px 12px;
    border: none;
    border-radius: 4px;
    background: #e0e0e0;
    cursor: pointer;
  }
  
  .alert-item button:hover {
    background: #d0d0d0;
  }
  </style>