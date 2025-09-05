<template>
    <div class="status-monitor">
      <h3>设备状态监控</h3>
      <div class="devices-grid">
        <div 
          v-for="device in devices" 
          :key="device.id"
          :class="['device-card', device.status, { offline: !device.online }]"
          @click="showDeviceDetails(device)"
        >
          <div class="device-header">
            <span class="device-id">{{ device.deviceId }}</span>
            <span class="device-type">{{ device.deviceType }}</span>
          </div>
          
          <div class="device-status">
            <span class="status-indicator" :class="device.status"></span>
            {{ device.status }}
          </div>
  
          <div class="device-metrics">
            <div class="metric">
              <span class="label">温度:</span>
              <span class="value">{{ device.metrics.temperature }}°C</span>
            </div>
            <div class="metric">
              <span class="label">压力:</span>
              <span class="value">{{ device.metrics.pressure }}kPa</span>
            </div>
            <div class="metric">
              <span class="label">效率:</span>
              <span class="value">{{ (device.metrics.efficiency * 100).toFixed(1) }}%</span>
            </div>
          </div>
  
          <div class="device-telemetry">
            <div class="telemetry">
              <span class="label">CPU:</span>
              <progress 
                :value="device.telemetry.cpuUsage" 
                max="100"
                :class="getUsageClass(device.telemetry.cpuUsage)"
              ></progress>
              <span class="value">{{ device.telemetry.cpuUsage }}%</span>
            </div>
            <div class="telemetry">
              <span class="label">内存:</span>
          <progress 
                :value="device.telemetry.memoryUsage / 1024 * 100" 
                max="100"
                :class="getUsageClass(device.telemetry.memoryUsage / 1024 * 100)"
              ></progress>
              <span class="value">{{ device.telemetry.memoryUsage }}MB</span>
            </div>
          </div>
  
          <div class="last-update">
            最后更新: {{ formatTime(device.timestamp) }}
          </div>
        </div>
      </div>
  
      <DeviceDetailModal 
        v-if="selectedDevice"
        :device="selectedDevice"
        @close="selectedDevice = null"
      />
    </div>
  </template>
  
  <script>
  import { ref, onMounted, onUnmounted } from 'vue'
  import mqttClient from '@/services/mqttClient'
  import DeviceDetailModal from './DeviceDetailModal.vue'
  
  export default {
    name: 'StatusMonitor',
    components: { DeviceDetailModal },
    
    setup() {
      const devices = ref({})
      const selectedDevice = ref(null)
  
      const updateDeviceData = (data) => {
        const deviceKey = data.deviceId
        
        if (!devices.value[deviceKey]) {
          devices.value[deviceKey] = {
            id: deviceKey,
            deviceId: data.deviceId,
            deviceType: data.deviceType,
            line: data.line,
            online: true,
            status: 'unknown',
            metrics: { temperature: 0, pressure: 0, vibration: 0, output: 0, efficiency: 0 },
            telemetry: { cpuUsage: 0, memoryUsage: 0, uptime: 0 },
            timestamp: new Date().toISOString()
          }
        }
  
        // 更新设备数据
        devices.value[deviceKey] = {
          ...devices.value[deviceKey],
          status: data.status,
          online: data.status !== 'offline',
          metrics: { ...data.metrics },
          telemetry: { ...data.telemetry },
          timestamp: data.timestamp
        }
  
        // 触发响应式更新
        devices.value = { ...devices.value }
      }
  
      const handleLWT = (data) => {
        const deviceKey = data.deviceId
        if (devices.value[deviceKey]) {
          devices.value[deviceKey].online = false
          devices.value[deviceKey].status = 'offline'
          devices.value[deviceKey].timestamp = data.timestamp
          devices.value = { ...devices.value }
        }
      }
  
      onMounted(() => {
        mqttClient.on('status-update', updateDeviceData)
        mqttClient.on('data-update', updateDeviceData)
        mqttClient.on('device-lwt', handleLWT)
      })
  
      onUnmounted(() => {
        mqttClient.off('status-update', updateDeviceData)
        mqttClient.off('data-update', updateDeviceData)
        mqttClient.off('device-lwt', handleLWT)
      })
  
      const getUsageClass = (usage) => {
        if (usage > 80) return 'high'
        if (usage > 60) return 'medium'
        return 'low'
      }
  
      const formatTime = (timestamp) => {
        return new Date(timestamp).toLocaleTimeString()
      }
  
      const showDeviceDetails = (device) => {
        selectedDevice.value = device
      }
  
      return {
        devices: Object.values(devices.value),
        selectedDevice,
        getUsageClass,
        formatTime,
        showDeviceDetails
      }
    }
  }
  </script>
  
  <style scoped>
  .devices-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
    margin-top: 20px;
  }
  
  .device-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: white;
  }
  
  .device-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
  }
  
  .device-card.offline {
    opacity: 0.6;
    background-color: #f5f5f5;
  }
  
  .device-card.running {
    border-left: 4px solid #4caf50;
  }
  
  .device-card.error {
    border-left: 4px solid #f44336;
  }
  
  .device-card.maintenance {
    border-left: 4px solid #ff9800;
  }
  
  .device-card.idle {
    border-left: 4px solid #2196f3;
  }
  
  .device-header {
    display: flex;
    justify-content: between;
    align-items: center;
    margin-bottom: 12px;
  }
  
  .device-id {
    font-weight: bold;
    font-size: 16px;
  }
  
  .device-type {
    background: #f0f0f0;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
  }
  
  .device-status {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
  }
  
  .status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
  }
  
  .status-indicator.running { background: #4caf50; }
  .status-indicator.error { background: #f44336; }
  .status-indicator.maintenance { background: #ff9800; }
  .status-indicator.idle { background: #2196f3; }
  .status-indicator.offline { background: #9e9e9e; }
  
  .device-metrics,
  .device-telemetry {
    margin-bottom: 12px;
  }
  
  .metric, .telemetry {
    display: flex;
    justify-content: between;
    align-items: center;
    margin-bottom: 4px;
  }
  
  .metric .label,
  .telemetry .label {
    font-weight: 500;
    margin-right: 8px;
    min-width: 60px;
  }
  
  .metric .value,
  .telemetry .value {
    font-family: monospace;
  }
  
  progress {
    width: 60px;
    height: 6px;
    margin: 0 8px;
  }
  
  progress.low { accent-color: #4caf50; }
  progress.medium { accent-color: #ff9800; }
  progress.high { accent-color: #f44336; }
  
  .last-update {
    font-size: 12px;
    color: #666;
    text-align: right;
  }
  </style>