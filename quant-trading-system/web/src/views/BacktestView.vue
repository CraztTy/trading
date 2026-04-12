<template>
  <div class="backtest-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">策略回测</h1>
        <p class="page-subtitle">回测您的交易策略</p>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          :icon="VideoPlay"
          @click="activeTab = 'create'"
        >
          新建回测
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <el-tabs v-model="activeTab" type="border-card" class="backtest-tabs">
      <!-- 新建回测 -->
      <el-tab-pane name="create">
        <template #label>
          <span class="tab-label">
            <el-icon><Plus /></el-icon>
            新建回测
          </span>
        </template>
        <BacktestForm @success="onTaskCreated" />
      </el-tab-pane>

      <!-- 回测任务 -->
      <el-tab-pane name="tasks">
        <template #label>
          <span class="tab-label">
            <el-icon><List /></el-icon>
            回测任务
            <el-badge
              v-if="runningTaskCount > 0"
              :value="runningTaskCount"
              class="task-badge"
            />
          </span>
        </template>
        <BacktestTaskList
          ref="taskListRef"
          @view-result="showResults"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 结果弹窗 -->
    <el-dialog
      v-model="resultDialogVisible"
      title="回测结果"
      width="90%"
      :fullscreen="isFullscreen"
      class="result-dialog"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-header">
          <span class="dialog-title">回测结果</span>
          <div class="dialog-actions">
            <el-button
              :icon="isFullscreen ? Crop : FullScreen"
              circle
              size="small"
              @click="isFullscreen = !isFullscreen"
            />
            <el-button
              :icon="Close"
              circle
              size="small"
              @click="resultDialogVisible = false"
            />
          </div>
        </div>
      </template>
      <BacktestResults
        v-if="selectedTask"
        :task-id="selectedTask.task_id"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Plus,
  List,
  VideoPlay,
  FullScreen,
  Crop,
  Close
} from '@element-plus/icons-vue'
import BacktestForm from '@/components/backtest/BacktestForm.vue'
import BacktestTaskList from '@/components/backtest/BacktestTaskList.vue'
import BacktestResults from '@/components/backtest/BacktestResults.vue'
import type { BacktestTask } from '@/api/backtest'

// 当前标签页
const activeTab = ref('create')

// 任务列表引用
const taskListRef = ref<InstanceType<typeof BacktestTaskList>>()

// 结果弹窗状态
const resultDialogVisible = ref(false)
const isFullscreen = ref(false)
const selectedTask = ref<BacktestTask | null>(null)

// 运行中任务数量
const runningTaskCount = computed(() => {
  // 实际应从taskListRef获取，这里简化处理
  return 0
})

// 任务创建成功回调
const onTaskCreated = (taskId: string) => {
  ElMessage.success(`回测任务已创建: ${taskId}`)
  activeTab.value = 'tasks'
  // 刷新任务列表
  setTimeout(() => {
    taskListRef.value?.refresh()
  }, 500)
}

// 显示结果
const showResults = (task: BacktestTask) => {
  selectedTask.value = task
  resultDialogVisible.value = true
}
</script>

<style scoped lang="scss">
.backtest-view {
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

.backtest-tabs {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);

  :deep(.el-tabs__header) {
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
    margin: 0;
  }

  :deep(.el-tabs__item) {
    color: var(--text-secondary);
    font-weight: 500;

    &.is-active {
      color: var(--accent-gold);
      background: var(--bg-secondary);
    }

    &:hover {
      color: var(--text-primary);
    }
  }

  :deep(.el-tabs__content) {
    padding: var(--space-4);
  }
}

.tab-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);

  .el-icon {
    font-size: 16px;
  }
}

.task-badge {
  margin-left: var(--space-2);

  :deep(.el-badge__content) {
    background: var(--accent-gold);
    color: var(--bg-primary);
    font-weight: 600;
  }
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dialog-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.dialog-actions {
  display: flex;
  gap: var(--space-2);
}

:deep(.result-dialog) {
  .el-dialog__header {
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
    margin-right: 0;
    padding: var(--space-4) var(--space-5);
  }

  .el-dialog__body {
    background: var(--bg-primary);
    padding: 0;
  }

  .el-dialog__headerbtn {
    display: none;
  }
}
</style>
