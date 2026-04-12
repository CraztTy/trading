<template>
  <div class="risk-view">
    <!-- 顶部状态栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">风险控制</h1>
        <p class="page-subtitle">实时监控和管理交易风险</p>
      </div>
      <div class="header-actions">
        <el-button
          type="danger"
          size="large"
          @click="showEmergencyDialog = true"
          :disabled="emergencyLoading"
        >
          <el-icon><Warning /></el-icon>
          紧急清仓
        </el-button>
      </div>
    </div>

    <!-- 状态概览卡片 -->
    <el-row :gutter="20" class="status-row">
      <el-col :span="6">
        <el-card class="status-card" :class="riskStatus.status">
          <div class="status-header">
            <span class="label">风险状态</span>
            <el-tag :type="getStatusType(riskStatus.status)" effect="dark">
              {{ getStatusText(riskStatus.status) }}
            </el-tag>
          </div>
          <div class="risk-score">
            <el-progress
              type="dashboard"
              :percentage="riskStatus.score"
              :color="scoreColors"
              :width="120"
            />
            <div class="score-label">风险评分</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <span class="label">启用规则</span>
            <el-icon><SetUp /></el-icon>
          </div>
          <div class="metric-value">{{ riskStatus.active_rules }}</div>
          <div class="metric-desc">条风控规则运行中</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card" :class="{ warning: riskStatus.pending_alerts > 0 }">
          <div class="metric-header">
            <span class="label">待处理预警</span>
            <el-icon><Bell /></el-icon>
          </div>
          <div class="metric-value">{{ riskStatus.pending_alerts }}</div>
          <div class="metric-desc">条风险预警待确认</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <span class="label">总仓位</span>
            <el-icon><Wallet /></el-icon>
          </div>
          <div class="metric-value">{{ formatPercent(positionSummary.total_position_weight) }}</div>
          <div class="metric-desc">{{ formatCurrency(positionSummary.total_position_value) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧：风控规则和持仓风险 -->
      <el-col :span="16">
        <!-- 风控规则面板 -->
        <el-card class="panel-card">
          <template #header>
            <div class="panel-header">
              <span>风控规则</span>
              <el-button text size="small" @click="refreshRules">
                <el-icon><Refresh /></el-icon>刷新
              </el-button>
            </div>
          </template>

          <el-table :data="rules" stripe style="width: 100%">
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="name" label="规则名称" />
            <el-table-column prop="type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="level" label="级别" width="100">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.level)" size="small">
                  {{ row.level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="检查/拦截" width="120">
              <template #default="{ row }">
                {{ row.stats.total_checks }} / {{ row.stats.failures }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  @change="toggleRule(row.code, row.enabled)"
                  :loading="ruleLoading === row.code"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 持仓风险面板 -->
        <el-card class="panel-card">
          <template #header>
            <div class="panel-header">
              <span>持仓风险</span>
              <el-radio-group v-model="riskFilter" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="high">高风险</el-radio-button>
                <el-radio-button label="medium">中风险</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <el-table :data="filteredPositions" stripe style="width: 100%">
            <el-table-column prop="symbol" label="股票代码" width="100" />
            <el-table-column prop="quantity" label="持仓数量" width="100" />
            <el-table-column label="市值/权重" width="150">
              <template #default="{ row }">
                <div>{{ formatCurrency(row.market_value) }}</div>
                <div class="text-muted">{{ formatPercent(row.weight) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="盈亏" width="120">
              <template #default="{ row }">
                <span :class="getPnlClass(row.unrealized_pnl_pct)">
                  {{ formatPercent(row.unrealized_pnl_pct) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="止损/止盈" min-width="200">
              <template #default="{ row }">
                <div class="sl-tp-row">
                  <span v-if="row.stop_loss" class="stop-loss">
                    止损: {{ row.stop_loss.toFixed(2) }}
                  </span>
                  <span v-else class="no-sl">未设置止损</span>
                  <el-button
                    v-if="!row.stop_loss"
                    type="danger"
                    size="small"
                    text
                    @click="openStopLossDialog(row)"
                  >
                    设置
                  </el-button>
                  <span v-if="row.take_profit" class="take-profit">
                    止盈: {{ row.take_profit.toFixed(2) }}
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskLevelType(row.risk_level)" size="small">
                  {{ getRiskLevelText(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：预警通知 -->
      <el-col :span="8">
        <el-card class="panel-card alerts-panel">
          <template #header>
            <div class="panel-header">
              <span>风险预警</span>
              <div>
                <el-button
                  v-if="hasUnacknowledgedAlerts"
                  type="primary"
                  size="small"
                  text
                  @click="acknowledgeAll"
                >
                  全部确认
                </el-button>
                <el-button
                  size="small"
                  text
                  @click="clearAcknowledged"
                  :disabled="!hasAcknowledgedAlerts"
                >
                  清空已确认
                </el-button>
              </div>
            </div>
          </template>

          <div class="alert-list" v-if="alerts.length > 0">
            <div
              v-for="alert in alerts"
              :key="alert.id"
              class="alert-item"
              :class="[alert.level.toLowerCase(), { acknowledged: alert.acknowledged }]"
            >
              <div class="alert-icon">
                <el-icon v-if="alert.level === 'CRITICAL'"><WarningFilled /></el-icon>
                <el-icon v-else><InfoFilled /></el-icon>
              </div>
              <div class="alert-content">
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-message">{{ alert.message }}</div>
                <div class="alert-footer">
                  <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
                  <el-button
                    v-if="!alert.acknowledged"
                    type="primary"
                    size="small"
                    text
                    @click="acknowledgeAlert(alert.id)"
                  >
                    确认
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无风险预警" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 紧急清仓对话框 -->
    <el-dialog
      v-model="showEmergencyDialog"
      title="⚠️ 紧急清仓"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="emergency-warning">
        <p>确定要执行紧急清仓吗？</p>
        <p class="warning-text">此操作将立即平仓所有持仓，且无法撤销！</p>
      </div>
      <el-form :model="emergencyForm">
        <el-form-item label="原因">
          <el-input
            v-model="emergencyForm.reason"
            type="textarea"
            rows="3"
            placeholder="请输入紧急清仓原因"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="emergencyForm.confirm">
            我理解此操作的风险，确认执行
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEmergencyDialog = false">取消</el-button>
        <el-button
          type="danger"
          @click="executeEmergencyClose"
          :loading="emergencyLoading"
          :disabled="!emergencyForm.confirm"
        >
          确认清仓
        </el-button>
      </template>
    </el-dialog>

    <!-- 设置止损对话框 -->
    <el-dialog
      v-model="showStopLossDialog"
      title="设置止损价"
      width="400px"
    >
      <el-form :model="stopLossForm" label-width="100px">
        <el-form-item label="股票代码">
          <span>{{ stopLossForm.symbol }}</span>
        </el-form-item>
        <el-form-item label="当前止损">
          <span>{{ stopLossForm.currentPrice || '未设置' }}</span>
        </el-form-item>
        <el-form-item label="止损价格">
          <el-input-number
            v-model="stopLossForm.price"
            :precision="2"
            :step="0.01"
            :min="0"
            controls-position="right"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showStopLossDialog = false">取消</el-button>
        <el-button type="primary" @click="saveStopLoss" :loading="stopLossLoading">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import {
  Warning, WarningFilled, InfoFilled, Bell, Wallet,
  SetUp, Refresh
} from '@element-plus/icons-vue'
import { riskApi, type RiskStatus, type RiskRule, type RiskAlert, type PositionRisk } from '@/api/risk'
import { ElMessage, ElMessageBox } from 'element-plus'

// ============ 响应式数据 ============
const riskStatus = ref<RiskStatus>({
  status: 'safe',
  score: 100,
  active_rules: 0,
  pending_alerts: 0
})

const rules = ref<RiskRule[]>([])
const alerts = ref<RiskAlert[]>([])
const positions = ref<PositionRisk[]>([])
const positionSummary = ref({
  total_position_weight: 0,
  total_position_value: 0
})

const riskFilter = ref('all')
const loading = ref(false)
const ruleLoading = ref<string | null>(null)
const emergencyLoading = ref(false)
const stopLossLoading = ref(false)

// 对话框显示状态
const showEmergencyDialog = ref(false)
const showStopLossDialog = ref(false)

// 表单数据
const emergencyForm = ref({
  reason: '',
  confirm: false
})

const stopLossForm = ref({
  symbol: '',
  currentPrice: null as number | null,
  price: 0
})

// 自动刷新定时器
let refreshTimer: number | null = null

// ============ 计算属性 ============
const filteredPositions = computed(() => {
  if (riskFilter.value === 'all') return positions.value
  return positions.value.filter(p => p.risk_level === riskFilter.value)
})

const hasUnacknowledgedAlerts = computed(() => {
  return alerts.value.some(a => !a.acknowledged)
})

const hasAcknowledgedAlerts = computed(() => {
  return alerts.value.some(a => a.acknowledged)
})

// ============ 方法 ============
const fetchRiskStatus = async () => {
  try {
    const res = await riskApi.getStatus()
    riskStatus.value = res.data
  } catch (e) {
    console.error('获取风控状态失败:', e)
  }
}

const fetchRules = async () => {
  try {
    const res = await riskApi.getRules()
    rules.value = res.data
  } catch (e) {
    console.error('获取规则失败:', e)
  }
}

const fetchAlerts = async () => {
  try {
    const res = await riskApi.getAlerts({ limit: 20 })
    alerts.value = res.data
  } catch (e) {
    console.error('获取预警失败:', e)
  }
}

const fetchPositions = async () => {
  try {
    const res = await riskApi.getPositionRisks()
    positions.value = res.data
  } catch (e) {
    console.error('获取持仓风险失败:', e)
  }
}

const fetchReport = async () => {
  try {
    const res = await riskApi.getReport()
    positionSummary.value = res.data.position_summary
  } catch (e) {
    console.error('获取报告失败:', e)
  }
}

const refreshRules = async () => {
  await fetchRules()
  ElMessage.success('规则列表已刷新')
}

const toggleRule = async (code: string, enabled: boolean) => {
  ruleLoading.value = code
  try {
    await riskApi.toggleRule(code)
    ElMessage.success(`规则已${enabled ? '启用' : '禁用'}`)
  } catch (e) {
    ElMessage.error('操作失败')
    // 恢复原状态
    const rule = rules.value.find(r => r.code === code)
    if (rule) rule.enabled = !enabled
  } finally {
    ruleLoading.value = null
  }
}

const acknowledgeAlert = async (alertId: number) => {
  try {
    await riskApi.acknowledgeAlert(alertId)
    const alert = alerts.value.find(a => a.id === alertId)
    if (alert) alert.acknowledged = true
    ElMessage.success('预警已确认')
  } catch (e) {
    ElMessage.error('确认失败')
  }
}

const acknowledgeAll = async () => {
  try {
    await ElMessageBox.confirm('确认所有未处理的预警？', '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const unacknowledged = alerts.value.filter(a => !a.acknowledged)
    for (const alert of unacknowledged) {
      await riskApi.acknowledgeAlert(alert.id)
      alert.acknowledged = true
    }
    ElMessage.success('所有预警已确认')
  } catch {
    // 取消
  }
}

const clearAcknowledged = async () => {
  try {
    await riskApi.clearAcknowledgedAlerts()
    alerts.value = alerts.value.filter(a => !a.acknowledged)
    ElMessage.success('已清空确认过的预警')
  } catch (e) {
    ElMessage.error('清空失败')
  }
}

const executeEmergencyClose = async () => {
  if (!emergencyForm.value.confirm) {
    ElMessage.warning('请先确认风险')
    return
  }

  emergencyLoading.value = true
  try {
    await riskApi.emergencyClose(emergencyForm.value.reason, true)
    ElMessage.success('紧急清仓已执行')
    showEmergencyDialog.value = false
    emergencyForm.value = { reason: '', confirm: false }
    // 刷新数据
    await fetchPositions()
    await fetchAlerts()
  } catch (e) {
    ElMessage.error('执行失败')
  } finally {
    emergencyLoading.value = false
  }
}

const openStopLossDialog = (position: PositionRisk) => {
  stopLossForm.value = {
    symbol: position.symbol,
    currentPrice: position.stop_loss,
    price: position.stop_loss || position.market_value / position.quantity * 0.95
  }
  showStopLossDialog.value = true
}

const saveStopLoss = async () => {
  stopLossLoading.value = true
  try {
    await riskApi.updateStopLoss(stopLossForm.value.symbol, stopLossForm.value.price)
    ElMessage.success('止损价已更新')
    showStopLossDialog.value = false
    await fetchPositions()
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    stopLossLoading.value = false
  }
}

// ============ 工具函数 ============
const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    safe: 'success',
    warning: 'warning',
    danger: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    safe: '安全',
    warning: '警告',
    danger: '危险'
  }
  return map[status] || status
}

const getLevelType = (level: string) => {
  const map: Record<string, string> = {
    critical: 'danger',
    high: 'warning',
    medium: '',
    low: 'info'
  }
  return map[level.toLowerCase()] || 'info'
}

const getRiskLevelType = (level: string) => {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'success'
  }
  return map[level] || 'info'
}

const getRiskLevelText = (level: string) => {
  const map: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[level] || level
}

const getPnlClass = (pnl: number) => {
  return pnl >= 0 ? 'positive' : 'negative'
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value || 0)
}

const formatPercent = (value: number) => {
  return (value * 100).toFixed(2) + '%'
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString()
}

const scoreColors = [
  { color: '#f56c6c', percentage: 60 },
  { color: '#e6a23c', percentage: 80 },
  { color: '#67c23a', percentage: 100 }
]

// ============ 生命周期 ============
const refreshAll = async () => {
  await Promise.all([
    fetchRiskStatus(),
    fetchRules(),
    fetchAlerts(),
    fetchPositions(),
    fetchReport()
  ])
}

onMounted(() => {
  refreshAll()
  // 每10秒自动刷新
  refreshTimer = window.setInterval(refreshAll, 10000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped lang="scss">
.risk-view {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  .header-left {
    .page-title {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .page-subtitle {
      font-size: 14px;
      color: var(--text-muted);
    }
  }
}

.status-row {
  margin-bottom: 20px;
}

.status-card {
  .status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .label {
      font-size: 14px;
      color: var(--text-muted);
    }
  }

  .risk-score {
    display: flex;
    flex-direction: column;
    align-items: center;

    .score-label {
      margin-top: 8px;
      font-size: 14px;
      color: var(--text-muted);
    }
  }

  &.safe {
    border-left: 4px solid #67c23a;
  }

  &.warning {
    border-left: 4px solid #e6a23c;
  }

  &.danger {
    border-left: 4px solid #f56c6c;
  }
}

.metric-card {
  height: 100%;

  .metric-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .label {
      font-size: 14px;
      color: var(--text-muted);
    }

    .el-icon {
      font-size: 20px;
      color: var(--text-muted);
    }
  }

  .metric-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  .metric-desc {
    font-size: 14px;
    color: var(--text-muted);
  }

  &.warning {
    .metric-value {
      color: #e6a23c;
    }
  }
}

.main-content {
  .panel-card {
    margin-bottom: 20px;

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}

.sl-tp-row {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .stop-loss {
    color: #f56c6c;
    font-size: 12px;
  }

  .take-profit {
    color: #67c23a;
    font-size: 12px;
  }

  .no-sl {
    color: #e6a23c;
    font-size: 12px;
  }
}

.alerts-panel {
  .alert-list {
    max-height: 600px;
    overflow-y: auto;
  }

  .alert-item {
    display: flex;
    gap: 12px;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid transparent;

    &.critical {
      background: rgba(245, 108, 108, 0.1);
      border-color: rgba(245, 108, 108, 0.3);

      .alert-icon {
        color: #f56c6c;
      }
    }

    &.warning {
      background: rgba(230, 162, 60, 0.1);
      border-color: rgba(230, 162, 60, 0.3);

      .alert-icon {
        color: #e6a23c;
      }
    }

    &.acknowledged {
      opacity: 0.6;
    }

    .alert-icon {
      font-size: 20px;
      margin-top: 2px;
    }

    .alert-content {
      flex: 1;

      .alert-title {
        font-weight: 600;
        margin-bottom: 4px;
      }

      .alert-message {
        font-size: 13px;
        color: var(--text-muted);
        margin-bottom: 8px;
      }

      .alert-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .alert-time {
          font-size: 12px;
          color: var(--text-muted);
        }
      }
    }
  }
}

.emergency-warning {
  margin-bottom: 20px;

  p {
    margin-bottom: 8px;
  }

  .warning-text {
    color: #f56c6c;
    font-weight: 600;
  }
}

.text-muted {
  color: var(--text-muted);
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}

:deep(.el-progress__text) {
  font-size: 24px !important;
  font-weight: 700;
}
</style>
