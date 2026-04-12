<template>
  <div class="live-view">
    <!-- 顶部控制栏 -->
    <el-page-header title="实盘监控" @back="$router.back()" />

    <el-row :gutter="20" class="control-bar">
      <!-- 状态卡片 -->
      <el-col :span="6">
        <el-card class="status-card">
          <div class="status-indicator" :class="isRunning ? 'running' : 'stopped'">
            <el-icon><CircleCheck v-if="isRunning" /><CircleClose v-else /></el-icon>
            <span>{{ isRunning ? '运行中' : '已停止' }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 模式选择 -->
      <el-col :span="12">
        <el-card class="mode-card">
          <div class="mode-selector">
            <span class="label">交易模式:</span>
            <el-radio-group v-model="tradeMode" @change="handleModeChange" :disabled="!isRunning">
              <el-radio-button label="manual">手动</el-radio-button>
              <el-radio-button label="auto">自动</el-radio-button>
              <el-radio-button label="simulate">模拟</el-radio-button>
            </el-radio-group>
            <el-button
              type="danger"
              size="small"
              @click="setPauseMode"
              v-if="tradeMode !== 'pause' && isRunning"
            >
              暂停
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 启停按钮 -->
      <el-col :span="6">
        <el-card class="control-card">
          <el-button
            v-if="!isRunning"
            type="success"
            size="large"
            @click="startLive"
          >
            <el-icon><VideoPlay /></el-icon>启动实盘
          </el-button>
          <el-button
            v-else
            type="danger"
            size="large"
            @click="stopLive"
          >
            <el-icon><VideoPause /></el-icon>停止实盘
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时信号面板 -->
    <el-row :gutter="20" class="main-content">
      <el-col :span="16">
        <el-card class="signal-panel">
          <template #header>
            <div class="panel-header">
              <span>实时信号</span>
              <el-tag v-if="pendingCount > 0" type="warning">{{ pendingCount }} 个待确认</el-tag>
            </div>
          </template>

          <div class="signal-list" v-if="signals.length > 0">
            <div
              v-for="signal in signals"
              :key="signal.id"
              class="signal-item"
              :class="[signal.signal_type, signal.status]"
            >
              <div class="signal-info">
                <div class="signal-header">
                  <span class="symbol">{{ signal.symbol }}</span>
                  <el-tag :type="signal.signal_type === 'buy' ? 'success' : 'danger'" size="small">
                    {{ signal.signal_type === 'buy' ? '买入' : '卖出' }}
                  </el-tag>
                  <span class="time">{{ formatTime(signal.timestamp) }}</span>
                </div>
                <div class="signal-detail">
                  <span>价格: {{ signal.price }}</span>
                  <span>数量: {{ signal.volume }}</span>
                  <span>置信度: {{ (signal.confidence * 100).toFixed(0) }}%</span>
                  <span class="reason">{{ signal.reason }}</span>
                </div>
              </div>

              <div class="signal-actions" v-if="signal.status === 'pending' && tradeMode === 'manual'">
                <el-button type="success" size="small" @click="confirmSignal(signal.id)">确认</el-button>
                <el-button type="danger" size="small" @click="ignoreSignal(signal.id)">忽略</el-button>
              </div>
              <el-tag v-else :type="getStatusType(signal.status)" size="small">
                {{ getStatusText(signal.status) }}
              </el-tag>
            </div>
          </div>
          <el-empty v-else description="暂无信号" />
        </el-card>
      </el-col>

      <!-- 统计面板 -->
      <el-col :span="8">
        <el-card class="stats-panel">
          <template #header>
            <span>今日统计</span>
          </template>

          <div class="stats-content">
            <div class="stat-item">
              <span class="label">总信号数</span>
              <span class="value">{{ stats.total_signals || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">已执行</span>
              <span class="value success">{{ stats.executed || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">待确认</span>
              <span class="value warning">{{ stats.pending || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">已忽略</span>
              <span class="value">{{ stats.ignored || 0 }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { CircleCheck, CircleClose, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import { liveApi, type SignalEvent, type TradeMode } from '@/api/live'
import { ElMessage } from 'element-plus'

const isRunning = ref(false)
const tradeMode = ref<TradeMode>('manual')
const signals = ref<SignalEvent[]>([])
const stats = ref({
  total_signals: 0,
  executed: 0,
  pending: 0,
  ignored: 0
})

const pendingCount = computed(() => signals.value.filter(s => s.status === 'pending').length)

// WebSocket连接
let ws: WebSocket | null = null
let refreshInterval: number | null = null

onMounted(() => {
  checkStatus()
  connectWebSocket()
  // 轮询刷新
  refreshInterval = window.setInterval(refreshData, 3000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (refreshInterval) clearInterval(refreshInterval)
})

const connectWebSocket = () => {
  const wsUrl = `ws://${window.location.host}/api/v1/live/ws`
  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'signal') {
      // 新信号到达
      signals.value.unshift(data.data)
      if (signals.value.length > 100) signals.value.pop()

      // 播放提示音
      playNotificationSound()
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
}

const playNotificationSound = () => {
  // 简单的提示音
  const audio = new Audio('/notification.mp3')
  audio.play().catch(() => {})
}

const checkStatus = async () => {
  try {
    const res = await liveApi.getStatus()
    isRunning.value = res.data.is_running
    tradeMode.value = res.data.mode || 'manual'
  } catch (e) {
    console.error(e)
  }
}

const refreshData = async () => {
  if (!isRunning.value) return

  try {
    // 刷新信号列表
    const res = await liveApi.getSignals({ limit: 50 })
    signals.value = res.data

    // 刷新统计
    const perf = await liveApi.getPerformance()
    stats.value = perf.data.signals
  } catch (e) {
    console.error(e)
  }
}

const startLive = async () => {
  try {
    await liveApi.start({ strategy_ids: [] })
    isRunning.value = true
    ElMessage.success('实盘已启动')
  } catch (e) {
    ElMessage.error('启动失败')
  }
}

const stopLive = async () => {
  try {
    await liveApi.stop()
    isRunning.value = false
    ElMessage.success('实盘已停止')
  } catch (e) {
    ElMessage.error('停止失败')
  }
}

const handleModeChange = async (mode: TradeMode) => {
  try {
    await liveApi.setMode(mode)
    ElMessage.success(`已切换到${getModeText(mode)}模式`)
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

const setPauseMode = async () => {
  await handleModeChange('pause')
  tradeMode.value = 'pause'
}

const confirmSignal = async (signalId: string) => {
  try {
    await liveApi.confirmSignal(signalId)
    ElMessage.success('信号已确认')
    refreshData()
  } catch (e) {
    ElMessage.error('确认失败')
  }
}

const ignoreSignal = async (signalId: string) => {
  try {
    await liveApi.ignoreSignal(signalId)
    ElMessage.success('信号已忽略')
    refreshData()
  } catch (e) {
    ElMessage.error('忽略失败')
  }
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString()
}

const getModeText = (mode: string) => {
  const map: Record<string, string> = {
    manual: '手动',
    auto: '自动',
    simulate: '模拟',
    pause: '暂停'
  }
  return map[mode] || mode
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    confirmed: 'success',
    executed: 'success',
    ignored: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待确认',
    confirmed: '已确认',
    executed: '已执行',
    ignored: '已忽略'
  }
  return map[status] || status
}
</script>

<style scoped>
.live-view {
  padding: 20px;
}

.control-bar {
  margin: 20px 0;
}

.status-card {
  .status-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-size: 18px;
    font-weight: 600;

    &.running {
      color: #67c23a;
    }

    &.stopped {
      color: #f56c6c;
    }
  }
}

.mode-card {
  .mode-selector {
    display: flex;
    align-items: center;
    gap: 15px;

    .label {
      color: #999;
    }
  }
}

.control-card {
  display: flex;
  justify-content: center;
  align-items: center;
}

.main-content {
  margin-top: 20px;
}

.signal-panel {
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .signal-list {
    max-height: 600px;
    overflow-y: auto;
  }

  .signal-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    &:last-child {
      border-bottom: none;
    }

    &.buy {
      border-left: 3px solid #67c23a;
    }

    &.sell {
      border-left: 3px solid #f56c6c;
    }

    .signal-info {
      flex: 1;

      .signal-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;

        .symbol {
          font-size: 16px;
          font-weight: 600;
          color: #d4af37;
        }

        .time {
          color: #666;
          font-size: 12px;
        }
      }

      .signal-detail {
        display: flex;
        gap: 15px;
        color: #999;
        font-size: 13px;

        .reason {
          color: #666;
          font-style: italic;
        }
      }
    }

    .signal-actions {
      display: flex;
      gap: 10px;
    }
  }
}

.stats-panel {
  .stats-content {
    .stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);

      &:last-child {
        border-bottom: none;
      }

      .label {
        color: #999;
      }

      .value {
        font-size: 20px;
        font-weight: 600;

        &.success {
          color: #67c23a;
        }

        &.warning {
          color: #e6a23c;
        }
      }
    }
  }
}
</style>
