<template>
  <Line :data="chartData" :options="chartOptions" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const labels: string[] = []
const values: number[] = []
const startDate = new Date('2024-01-01')
let value = 1000000

for (let i = 0; i < 365; i++) {
  const date = new Date(startDate)
  date.setDate(date.getDate() + i)
  labels.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }))
  const change = (Math.random() - 0.45) * 0.02
  value *= (1 + change)
  values.push(value)
}

const chartData = computed(() => ({
  labels,
  datasets: [{
    label: '资产净值',
    data: values,
    borderColor: '#f59e0b',
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    borderWidth: 2,
    fill: true,
    tension: 0.4,
    pointRadius: 0,
    pointHoverRadius: 4
  }]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index' as const
  },
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      backgroundColor: '#1a1d24',
      titleColor: '#f8fafc',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      padding: 12,
      displayColors: false,
      callbacks: {
        label: (context: any) => {
          return `¥${context.parsed.y.toLocaleString()}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        color: '#1e293b',
        drawBorder: false
      },
      ticks: {
        color: '#64748b',
        font: {
          family: 'JetBrains Mono',
          size: 10
        }
      }
    },
    y: {
      grid: {
        color: '#1e293b',
        drawBorder: false
      },
      ticks: {
        color: '#64748b',
        font: {
          family: 'JetBrains Mono',
          size: 10
        },
        callback: (value: any) => {
          return `¥${(Number(value) / 1000000).toFixed(2)}M`
        }
      }
    }
  }
}
</script>
