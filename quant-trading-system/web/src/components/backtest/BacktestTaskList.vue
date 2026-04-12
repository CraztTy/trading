<template>
  <div class="backtest-task-list">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-radio-group v-model="filterStatus" size="small">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="pending">待处理</el-radio-button>
          <el-radio-button label="running">运行中</el-radio-button>
          <el-radio-button label="completed">已完成</el-radio-button>
          <el-radio-button label="failed">失败</el-radio-button>
        </el-radio-group>
      </div>
      <div class="toolbar-right">
        <el-button
          type="primary"
          size="small"
          :icon="Refresh"
          :loading="refreshing"
          @click="refreshTasks"
        >
          刷新
        </el-button>
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          size="small"
        />
      </div>
    </div>

    <!-- 任务列表表格 -->
    <el-table
      :data="filteredTasks"
      stripe
      style="width: 100%"
      v-loading="loading"
    >
      <el-table-column prop="task_id" label="任务ID" width="180">
        <template #default="{ row }">
          <span class="mono task-id">{{ row.task_id }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag
            :type="getStatusType(row.status)"
            size="small"
            effect="dark"
          >
            <el-icon v-if="row.status === 'running'" class="is-loading">
              <Loading />
            </el-icon>
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="progress" label="进度" width="180">
        <template #default="{ row }">
          <el-progress
            :percentage="row.progress"
            :status="getProgressStatus(row.status)"
            :stroke-width="8"
          />
        </template>
      </el-table-column>

      <el-table-column prop="strategy_id" label="策略" width="140">
        <template #default="{ row }">
          <span class="strategy-name">{{ getStrategyName(row.strategy_id) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="symbols" label="股票数量" width="100">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.symbols.length }}只</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="dateRange" label="回测区间" width="200">
        <template #default="{ row }">
          <div class="date-range">
            <span class="mono">{{ row.start_date }}</span>
            <span class="date-separator">至</span>
            <span class="mono">{{ row.end_date }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="initial_capital" label="初始资金" width="140">
        <template #default="{ row }">
          <span class="mono">¥{{ row.initial_capital.toLocaleString() }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          <span class="mono">{{ formatTime(row.created_at) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              v-if="row.status === 'completed'"
              type="primary"
              size="small"
              :icon="View"
              @click="viewResult(row)"
            >
              查看
            </el-button>
            <el-button
              v-else-if="row.status === 'failed'"
              type="danger"
              size="small"
              :icon="Warning"
              @click="showError(row)"
            >
              错误
            </el-button>
            <el-button
              v-else
              type="info"
              size="small"
              disabled
            >
              等待中
            </el-button>
            <el-popconfirm
              title="确定要删除这个任务吗？"
              @confirm="deleteTask(row.task_id)"
            >
              <template #reference>
                <el-button
                  type="danger"
                  size="small"
                  :icon="Delete"
                  plain
                />
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        background
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 错误详情弹窗 -->
    <el-dialog
      v-model="errorDialogVisible"
      title="错误详情"
      width="500px"
    >
      <div class="error-content">
        <el-alert
          :title="selectedTask?.error_message || '未知错误'"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, View, Delete, Loading, Warning } from '@element-plus/icons-vue'
import {
  listBacktestTasks,
  deleteBacktestTask,
  type BacktestTask
} from '@/api/backtest'

const emit = defineEmits<{
  'view-result': [task: BacktestTask]
}>()

// 状态
const loading = ref(false)
const refreshing = ref(false)
const tasks = ref<BacktestTask[]>([])
const filterStatus = ref('')
const autoRefresh = ref(true)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const errorDialogVisible = ref(false)
const selectedTask = ref<BacktestTask | null>(null)

// 自动刷新定时器
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 策略名称映射
const strategyNames: Record<string, string> = {
  dual_ma: '双均线策略',
  macd: 'MACD动量策略',
  rsi: 'RSI超买超卖策略',
  bollinger: '布林带策略',
  value: '价值投资策略'
}

// 计算属性：过滤后的任务
const filteredTasks = computed(() => {
  if (!filterStatus.value) return tasks.value
  return tasks.value.filter(t => t.status === filterStatus.value)
})

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

// 获取进度条状态
const getProgressStatus = (status: string) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return ''
}

// 获取策略名称
const getStrategyName = (strategyId: string) => {
  return strategyNames[strategyId] || strategyId
}

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 加载任务列表
const loadTasks = async () => {
  if (loading.value) return

  loading.value = true
  try {
    const response = await listBacktestTasks({
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    }) as unknown as { tasks: BacktestTask[]; total: number }

    tasks.value = response.tasks
    total.value = response.total
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

// 刷新任务列表
const refreshTasks = async () => {
  refreshing.value = true
  await loadTasks()
  refreshing.value = false
}

// 删除任务
const deleteTask = async (taskId: string) => {
  try {
    await deleteBacktestTask(taskId)
    ElMessage.success('任务已删除')
    await loadTasks()
  } catch (error) {
    ElMessage.error('删除任务失败')
  }
}

// 查看结果
const viewResult = (task: BacktestTask) => {
  emit('view-result', task)
}

// 显示错误
const showError = (task: BacktestTask) => {
  selectedTask.value = task
  errorDialogVisible.value = true
}

// 分页处理
const handleSizeChange = (val: number) => {
  pageSize.value = val
  loadTasks()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  loadTasks()
}

// 启动自动刷新
const startAutoRefresh = () => {
  if (refreshTimer) return
  refreshTimer = setInterval(() => {
    // 检查是否有运行中的任务
    const hasRunning = tasks.value.some(t => t.status === 'running' || t.status === 'pending')
    if (hasRunning) {
      loadTasks()
    }
  }, 3000)
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 监听自动刷新开关
watch(autoRefresh, (val: boolean) => {
  if (val) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

onMounted(() => {
  loadTasks()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

// 暴露刷新方法
defineExpose({
  refresh: loadTasks
})
</script>

<style scoped lang="scss">
.backtest-task-list {
  padding: var(--space-4);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.task-id {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.strategy-name {
  font-weight: 500;
  color: var(--text-primary);
}

.date-range {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--text-xs);

  .date-separator {
    color: var(--text-muted);
    font-size: 10px;
  }
}

.action-buttons {
  display: flex;
  gap: var(--space-2);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-primary);
}

.error-content {
  padding: var(--space-4);
}

:deep(.el-progress-bar__outer) {
  background-color: var(--bg-tertiary);
}

:deep(.el-tag--dark) {
  border: none;
}

:deep(.is-loading) {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
