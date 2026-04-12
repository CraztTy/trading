<template>
  <div class="strategy-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">策略管理</h1>
        <p class="page-subtitle">创建、编辑和管理您的交易策略</p>
      </div>
    </div>

    <!-- 策略列表 -->
    <StrategyList
      :strategies="strategies"
      :total="total"
      @create="handleCreate"
      @detail="handleDetail"
      @edit="handleEdit"
      @delete="handleDelete"
      @start="handleStart"
      @stop="handleStop"
      @pause="handlePause"
      @backtest="handleBacktest"
      @optimize="handleOptimize"
    />

    <!-- 策略编辑器 -->
    <StrategyEditor
      v-model="editorVisible"
      :strategy="selectedStrategy"
      @saved="handleSaved"
      @run-backtest="handleRunBacktest"
    />

    <!-- 回测对话框 -->
    <el-dialog
      v-model="backtestDialogVisible"
      title="运行回测"
      width="600px"
      destroy-on-close
    >
      <BacktestForm
        v-if="selectedStrategy"
        :strategy-id="selectedStrategy.strategy_id"
        @success="onBacktestCreated"
      />
    </el-dialog>

    <!-- 参数优化对话框 -->
    <el-dialog
      v-model="optimizeDialogVisible"
      title="参数优化"
      width="800px"
      destroy-on-close
    >
      <div v-if="selectedStrategy" class="optimize-content">
        <el-alert
          title="参数优化功能"
          description="使用网格搜索或遗传算法自动寻找最优参数组合"
          type="info"
          :closable="false"
          class="optimize-alert"
        />
        <div class="optimize-params">
          <h4>可优化参数</h4>
          <el-table :data="optimizeParamList" border>
            <el-table-column prop="name" label="参数名" width="150" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column label="优化范围">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.min"
                  size="small"
                  placeholder="最小值"
                  class="range-input"
                />
                <span class="range-separator">~</span>
                <el-input-number
                  v-model="row.max"
                  size="small"
                  placeholder="最大值"
                  class="range-input"
                />
              </template>
            </el-table-column>
            <el-table-column label="步长" width="120">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.step"
                  size="small"
                  :precision="row.type === 'float' ? 4 : 0"
                  :step="row.type === 'float' ? 0.01 : 1"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="optimize-actions">
          <el-button type="primary" @click="startOptimization">
            开始优化
          </el-button>
          <el-button @click="optimizeDialogVisible = false">
            取消
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 策略详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="策略详情"
      width="700px"
      destroy-on-close
    >
      <div v-if="selectedStrategy" class="strategy-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="策略名称">
            {{ selectedStrategy.name }}
          </el-descriptions-item>
          <el-descriptions-item label="策略ID">
            {{ selectedStrategy.strategy_id }}
          </el-descriptions-item>
          <el-descriptions-item label="策略类型">
            {{ selectedStrategy.strategy_type }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedStrategy.status)">
              {{ getStatusText(selectedStrategy.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(selectedStrategy.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(selectedStrategy.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="总收益">
            <span :class="(selectedStrategy.total_return || 0) >= 0 ? 'up' : 'down'">
              {{ formatReturn(selectedStrategy.total_return) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="夏普比率">
            {{ selectedStrategy.sharpe_ratio?.toFixed(2) || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="最大回撤">
            <span class="down">
              {{ formatDrawdown(selectedStrategy.max_drawdown) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="胜率">
            {{ selectedStrategy.win_rate ? (selectedStrategy.win_rate * 100).toFixed(1) + '%' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="总交易次数">
            {{ selectedStrategy.total_trades }}
          </el-descriptions-item>
          <el-descriptions-item label="当前版本">
            {{ selectedStrategy.current_version }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ selectedStrategy.description || '暂无描述' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>参数配置</h4>
          <el-table :data="paramTableData" border>
            <el-table-column prop="name" label="参数名" />
            <el-table-column prop="type" label="类型" />
            <el-table-column prop="default" label="默认值" />
            <el-table-column prop="description" label="描述" />
          </el-table>
        </div>

        <div class="detail-actions">
          <el-button type="primary" @click="handleEditFromDetail">
            编辑策略
          </el-button>
          <el-button @click="detailDialogVisible = false">
            关闭
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import StrategyList from '@/components/strategy/StrategyList.vue'
import StrategyEditor from '@/components/strategy/StrategyEditor.vue'
import BacktestForm from '@/components/backtest/BacktestForm.vue'
import { strategyApi, type Strategy } from '@/api/strategy'

// 策略列表数据
const strategies = ref<Strategy[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(12)

// 对话框状态
const editorVisible = ref(false)
const backtestDialogVisible = ref(false)
const optimizeDialogVisible = ref(false)
const detailDialogVisible = ref(false)

// 选中的策略
const selectedStrategy = ref<Strategy | undefined>(undefined)

// 优化参数列表
const optimizeParamList = ref<any[]>([])

// 参数表格数据
const paramTableData = computed(() => {
  if (!selectedStrategy.value) return []
  const schema = selectedStrategy.value.parameters_schema || {}
  const defaults = selectedStrategy.value.default_parameters || {}

  return Object.entries(schema).map(([name, config]: [string, any]) => ({
    name,
    type: config.type,
    default: defaults[name],
    description: config.description || '-'
  }))
})

// 加载策略列表
const loadStrategies = async () => {
  loading.value = true
  try {
    const res = await strategyApi.getStrategies({
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    })
    strategies.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('加载策略列表失败')
  } finally {
    loading.value = false
  }
}

// 状态相关
const getStatusType = (status: string): string => {
  const map: Record<string, string> = {
    draft: 'info',
    active: 'success',
    paused: 'warning',
    stopped: 'danger',
    error: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    draft: '草稿',
    active: '运行中',
    paused: '已暂停',
    stopped: '已停止',
    error: '错误'
  }
  return map[status] || status
}

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const formatReturn = (val?: number): string => {
  if (val == null) return '-'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${(val * 100).toFixed(2)}%`
}

const formatDrawdown = (val?: number): string => {
  if (val == null) return '-'
  return `-${(val * 100).toFixed(2)}%`
}

// 事件处理
const handleCreate = () => {
  selectedStrategy.value = undefined
  editorVisible.value = true
}

const handleEdit = (strategy: Strategy) => {
  selectedStrategy.value = strategy
  editorVisible.value = true
}

const handleDetail = (strategy: Strategy) => {
  selectedStrategy.value = strategy
  detailDialogVisible.value = true
}

const handleEditFromDetail = () => {
  detailDialogVisible.value = false
  editorVisible.value = true
}

const handleDelete = async (strategy: Strategy) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除策略 "${strategy.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await strategyApi.deleteStrategy(strategy.strategy_id)
    ElMessage.success('策略已删除')
    loadStrategies()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleStart = async (strategy: Strategy) => {
  try {
    await strategyApi.startStrategy(strategy.strategy_id)
    ElMessage.success('策略已启动')
    loadStrategies()
  } catch (error) {
    ElMessage.error('启动失败')
  }
}

const handleStop = async (strategy: Strategy) => {
  try {
    await strategyApi.stopStrategy(strategy.strategy_id)
    ElMessage.success('策略已停止')
    loadStrategies()
  } catch (error) {
    ElMessage.error('停止失败')
  }
}

const handlePause = async (strategy: Strategy) => {
  try {
    await strategyApi.pauseStrategy(strategy.strategy_id)
    ElMessage.success('策略已暂停')
    loadStrategies()
  } catch (error) {
    ElMessage.error('暂停失败')
  }
}

const handleBacktest = (strategy: Strategy) => {
  selectedStrategy.value = strategy
  backtestDialogVisible.value = true
}

const handleOptimize = (strategy: Strategy) => {
  selectedStrategy.value = strategy

  // 构建优化参数列表
  const schema = strategy.parameters_schema || {}
  optimizeParamList.value = Object.entries(schema).map(([name, config]: [string, any]) => {
    const defaultValue = strategy.default_parameters?.[name] || 0
    return {
      name,
      type: config.type,
      min: config.min ?? defaultValue * 0.5,
      max: config.max ?? defaultValue * 1.5,
      step: config.type === 'float' ? 0.01 : 1
    }
  })

  optimizeDialogVisible.value = true
}

const startOptimization = () => {
  ElMessage.info('参数优化功能开发中...')
  optimizeDialogVisible.value = false
}

const handleSaved = () => {
  loadStrategies()
}

const handleRunBacktest = () => {
  backtestDialogVisible.value = true
}

const onBacktestCreated = (taskId: string) => {
  ElMessage.success(`回测任务已创建: ${taskId}`)
  backtestDialogVisible.value = false
}

// 初始化
onMounted(() => {
  loadStrategies()
})
</script>

<style scoped lang="scss">
.strategy-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-4);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);

  .page-title {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: var(--space-2);
  }

  .page-subtitle {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
}

.optimize-content {
  .optimize-alert {
    margin-bottom: var(--space-4);
  }

  .optimize-params {
    margin-bottom: var(--space-4);

    h4 {
      font-size: var(--text-base);
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: var(--space-3);
    }
  }

  .range-input {
    width: 100px;
  }

  .range-separator {
    margin: 0 var(--space-2);
    color: var(--text-muted);
  }

  .optimize-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-3);
    padding-top: var(--space-4);
    border-top: 1px solid var(--border-primary);
  }
}

.strategy-detail {
  .up {
    color: var(--accent-red);
  }

  .down {
    color: var(--accent-green);
  }

  .detail-section {
    margin-top: var(--space-4);

    h4 {
      font-size: var(--text-base);
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: var(--space-3);
    }
  }

  .detail-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-3);
    margin-top: var(--space-4);
    padding-top: var(--space-4);
    border-top: 1px solid var(--border-primary);
  }
}
</style>
