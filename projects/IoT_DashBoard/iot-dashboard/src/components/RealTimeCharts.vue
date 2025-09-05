<template>
    <div class="real-time-charts">
      <h3>实时数据趋势</h3>
      
      <div class="chart-controls">
        <select v-model="selectedMetric">
          <option value="temperature">温度</option>
          <option value="pressure">压力</option>
          <option value="vibration">振动</option>
          <option value="efficiency">效率</option>
          <option value="cpuUsage">CPU使用率</option>
        </select>
        
        <select v-model="selectedDevice">
          <option value="all">所有设备</option>
          <option 
            v-for="device in availableDevices" 
            :key="device"
            :value="device"
          >
            {{ device }}
          </option>
        </select>
  
        <button @click="clearData">清除数据</button>
      </div>
  
      <div class="charts-container">
        <div class="chart-wrapper">
          <LineChart 
            :chart-data="chartData" 
            :options="chartOptions"
            :height="300"
          />
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { ref, computed, onMounted, onUnmounted } from 'vue'
  import { LineChart } from 'vue-chartjs'
  import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    LineElement,
    LinearScale,
    PointElement,
    CategoryScale,
    TimeScale
  } from 'chart.js'
  import 'chartjs-adapter-date-fns'
  
  ChartJS.register(
    Title,
    Tooltip,
    Legend,
    LineElement,
    LinearScale,
    PointElement,
    CategoryScale,
    TimeScale
  )
  
  export default {
    name: 'RealTimeCharts',
    components: { LineChart },
    
    setup() {
      const historicalData = ref([])
      const selectedMetric = ref('temperature')
      const selectedDevice = ref('all')
      const maxDataPoints = 100
  
      const availableDevices = computed(() => {
        const devices = new Set()
        historicalData.value.forEach(item => {
          devices.add(item.deviceId)
        })
        return Array.from(devices)
      })
  
      const chartData = computed(() => {
        const filteredData = selectedDevice.value === 'all' 
          ? historicalData.value
          : historicalData.value.filter(item => item.deviceId === selectedDevice.value)
  
        return {
          datasets: [
            {
              label: `${selectedMetric.value} (${selectedDevice.value})`,
              data: filteredData.map(item => ({
                x: new Date(item.timestamp),
                y: item[selectedMetric.value]
              })),
              borderColor: 'rgb(75, 192, 192)',
              backgroundColor: 'rgba(75, 192, 192, 0.2)',
              tension: 0.1,
              pointRadius: 2
            }
          ]
        }
      })
  
      const chartOptions = computed(() => ({
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'minute',
              displayFormats: {
                minute: 'HH:mm:ss'
              }
            },
            title: {
              display: true,
              text: '时间'
            }
          },
          y: {
            title: {
              display: true,
              text: getMetricUnit(selectedMetric.value)
            }
          }
        },
        plugins: {
          legend: {
            position: 'top'
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                return `${context.dataset.label}: ${context.raw.y.toFixed(2)} ${getMetricUnit(selectedMetric.value)}`
              }
            }
          }
        }
      }))
  
      const getMetricUnit = (metric) => {
        const units = {
          temperature: '°C',
          pressure: 'kPa',
          vibration: 'm/s²',
          efficiency: '%',
          cpuUsage: '%',
          memoryUsage: 'MB'
        }
        return units[metric] || ''
      }
  
      const updateChartData = (data) => {
        const newDataPoint = {
          deviceId: data.deviceId,
          deviceType: data.deviceType,
          timestamp: data.timestamp,
          temperature: data.metrics.temperature,
          pressure: data.metrics.pressure,
          vibration: data.metrics.vibration,
          efficiency: data.metrics.efficiency * 100,
          cpuUsage: data.telemetry.cpuUsage,
          memoryUsage: data.telemetry.memoryUsage
        }
  
        historicalData.value.push(newDataPoint)
        
        // 限制数据点数量
        if (historicalData.value.length > maxDataPoints) {
          historicalData.value = historicalData.value.slice(-maxDataPoints)
        }
      }
  
      onMounted(() => {
        mqttClient.on('data-update', updateChartData)
      })
  
      onUnmounted(() => {
        mqttClient.off('data-update', updateChartData)
      })
  
      const clearData = () => {
        historicalData.value = []
      }
  
      return {
        historicalData,
        selectedMetric,
        selectedDevice,
        availableDevices,
        chartData,
        chartOptions,
        clearData
      }
    }
  }
  </script>
  
  <style scoped>
  .chart-controls {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    align-items: center;
  }
  
  .chart-controls select,
  .chart-controls button {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
  }
  
  .chart-controls button {
    background: #f0f0f0;
    cursor: pointer;
  }
  
  .chart-controls button:hover {
    background: #e0e0e0;
  }
  
  .charts-container {
    display: grid;
    gap: 20px;
  }
  
  .chart-wrapper {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  </style>