<template>
  <div class="strategy-list">
    <!-- 搜索和筛选 -->
    <div class="filter-row">
      <div class="filter-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索策略名称"
          clearable
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          clearable
          class="filter-select"
          @change="handleFilter"
        >
          <el-option label="草稿" value="draft" />
          <el-option label="运行中" value="active" />
          <el-option label="已暂停" value="paused" />
          <el-option label="已停止" value="stopped" />
          <el-option label="错误" value="error" />
        </el-select>
      </div>
      <el-button type="primary" @click="$emit('create')">
        <el-icon><Plus /></el-icon>
        新建策略
      </el-button>
    </div>

    <!-- 策略卡片网格 -->
    <div class="strategy-grid">
      <el-card
        v-for="strategy in strategies"
        :key="strategy.strategy_id"
        class="strategy-card"
        shadow="hover"
      >
        <div class="card-header">
          <h3 class="strategy-name" @click="$emit('detail', strategy)">
            {{ strategy.name }}
          </h3>
          <el-tag :type="getStatusType(strategy.status)" size="small">
            {{ getStatusText(strategy.status) }}
          </el-tag>
        </div>

        <p class="strategy-desc">{{ strategy.description || '暂无描述' }}</p>

        <div class="strategy-type">
          <el-tag type="info" size="small">{{ strategy.strategy_type }}</el-tag>
        </div>

        <div class="strategy-metrics">
          <div class="metric">
            <span class="label">总收益</span>
            <span :class="['value', (strategy.total_return || 0) >= 0 ? 'up' : 'down']">
              {{ formatReturn(strategy.total_return) }}
            </span>
          </div>
          <div class="metric">
            <span class="label">夏普比率</span>
            <span class="value">{{ strategy.sharpe_ratio?.toFixed(2) || '-' }}</span>
          </div>
          <div class="metric">
            <span class="label">最大回撤</span>
            <span class="value down">{{ formatDrawdown(strategy.max_drawdown) }}</span>
          </div>
        </div>

        <div class="card-footer">
          <div class="strategy-stats">
            <span>{{ strategy.total_trades }} 笔交易</span>
            <span>版本 {{ strategy.current_version }}</span>
          </div>

          <div class="card-actions">
            <el-button-group>
              <el-button
                v-if="strategy.status === 'stopped' || strategy.status === 'draft'"
                type="success"
                size="small"
                @click="$emit('start', strategy)"
              >
                启动
              </el-button>
              <el-button
                v-if="strategy.status === 'active'"
                type="warning"
                size="small"
                @click="$emit('pause', strategy)"
              >
                暂停
              </el-button>
              <el-button
                v-if="['active', 'paused'].includes(strategy.status)"
                type="danger"
                size="small"
                @click="$emit('stop', strategy)"
              >
                停止
              </el-button>
            </el-button-group>

            <el-dropdown trigger="click">
              <el-button size="small">
                <el-icon><More /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="$emit('edit', strategy)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-dropdown-item>
                  <el-dropdown-item @click="$emit('backtest', strategy)">
                    <el-icon><TrendCharts /></el-icon> 回测
                  </el-dropdown-item>
                  <el-dropdown-item @click="$emit('optimize', strategy)">
                    <el-icon><SetUp /></el-icon> 参数优化
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="$emit('delete', strategy)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="strategies.length === 0" description="暂无策略" />

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[12, 24, 48]"
      layout="total, sizes, prev, pager, next"
      class="pagination"
      @change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  Search,
  Plus,
  More,
  Edit,
  Delete,
  TrendCharts,
  SetUp
} from '@element-plus/icons-vue'
import type { Strategy } from '@/api/strategy'

interface Props {
  strategies: Strategy[]
  total: number
}

defineProps<Props>()

defineEmits<[
  'create',
  'detail',
  'edit',
  'delete',
  'start',
  'stop',
  'pause',
  'backtest',
  'optimize'
]>()

const searchQuery = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(12)

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

const formatReturn = (val?: number): string => {
  if (val == null) return '-'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${(val * 100).toFixed(2)}%`
}

const formatDrawdown = (val?: number): string => {
  if (val == null) return '-'
  return `-${(val * 100).toFixed(2)}%`
}

const handleSearch = (): void => {
  // TODO: 实现搜索
}

const handleFilter = (): void => {
  // TODO: 实现筛选
}

const handlePageChange = (): void => {
  // TODO: 实现分页
}
</script>

<style scoped lang="scss">
.strategy-list {
  padding: var(--space-4);
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
  gap: var(--space-4);
}

.filter-left {
  display: flex;
  gap: var(--space-4);
  flex: 1;
}

.search-input {
  width: 280px;
}

.filter-select {
  width: 160px;
}

.strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

.strategy-card {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  transition: all var(--transition-base);

  &:hover {
    border-color: var(--accent-gold);
    transform: translateY(-2px);
  }

  :deep(.el-card__body) {
    padding: var(--space-4);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.strategy-name {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--accent-gold);
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}

.strategy-desc {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin-bottom: var(--space-3);
  min-height: 40px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.strategy-type {
  margin-bottom: var(--space-3);
}

.strategy-metrics {
  display: flex;
  justify-content: space-between;
  padding: var(--space-3) 0;
  border-top: 1px solid var(--border-primary);
  border-bottom: 1px solid var(--border-primary);
  margin-bottom: var(--space-3);
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;

  .label {
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .value {
    font-family: var(--font-mono);
    font-size: var(--text-base);
    font-weight: 600;

    &.up {
      color: var(--accent-red);
    }

    &.down {
      color: var(--accent-green);
    }
  }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strategy-stats {
  font-size: var(--text-xs);
  color: var(--text-muted);

  span {
    margin-right: var(--space-3);
  }
}

.card-actions {
  display: flex;
  gap: var(--space-2);
}

.pagination {
  justify-content: flex-end;
  margin-top: var(--space-4);
}
</style>
