<template>
  <div class="sheng-flow-monitor">
    <h3 class="monitor-title">三省六部数据流监控</h3>

    <div class="flow-container">
      <!-- 太子院 -->
      <div class="sheng-card crown-prince">
        <div class="sheng-header">
          <el-icon><DataAnalysis /></el-icon>
          <span>太子院</span>
          <el-tag size="small" type="success">数据校验</el-tag>
        </div>
        <div class="sheng-stats">
          <div class="stat-item">
            <span class="stat-value">{{ crownPrinceStats.totalReceived }}</span>
            <span class="stat-label">总接收</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-success">{{ crownPrinceStats.valid }}</span>
            <span class="stat-label">有效</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-danger">{{ crownPrinceStats.invalid }}</span>
            <span class="stat-label">无效</span>
          </div>
        </div>
      </div>

      <div class="flow-arrow">
        <el-icon><ArrowRight /></el-icon>
      </div>

      <!-- 中书省 -->
      <div class="sheng-card zhongshu">
        <div class="sheng-header">
          <el-icon><TrendCharts /></el-icon>
          <span>中书省</span>
          <el-tag size="small" type="primary">信号生成</el-tag>
        </div>
        <div class="sheng-stats">
          <div class="stat-item">
            <span class="stat-value">{{ signalStats.generated }}</span>
            <span class="stat-label">已生成</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ signalStats.activeStrategies }}</span>
            <span class="stat-label">策略数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-warning">{{ signalStats.deduplicated }}</span>
            <span class="stat-label">去重</span>
          </div>
        </div>
        <div class="latest-signals">
          <div v-for="signal in latestSignals" :key="signal.id" class="signal-item">
            <el-tag :type="signal.type === 'buy' ? 'danger' : 'success'" size="small">
              {{ signal.type === 'buy' ? '买' : '卖' }}
            </el-tag>
            <span class="signal-symbol">{{ signal.symbol }}</span>
            <span class="signal-price">¥{{ signal.price.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <div class="flow-arrow">
        <el-icon><ArrowRight /></el-icon>
      </div>

      <!-- 门下省 -->
      <div class="sheng-card menxia" :class="{ 'circuit-breaker': menxiaStats.circuitBreakerActive }">
        <div class="sheng-header">
          <el-icon><Warning /></el-icon>
          <span>门下省</span>
          <el-tag size="small" :type="menxiaStats.circuitBreakerActive ? 'danger' : 'warning'">
            {{ menxiaStats.circuitBreakerActive ? '熔断中' : '风控审核' }}
          </el-tag>
        </div>
        <div class="sheng-stats">
          <div class="stat-item">
            <span class="stat-value">{{ menxiaStats.totalAudits }}</span>
            <span class="stat-label">已审核</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-success">{{ menxiaStats.approved }}</span>
            <span class="stat-label">通过</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-danger">{{ menxiaStats.rejected }}</span>
            <span class="stat-label">拒绝</span>
          </div>
        </div>
        <div v-if="menxiaStats.circuitBreakerActive" class="circuit-breaker-alert">
          <el-icon><CircleClose /></el-icon>
          <span>熔断: {{ menxiaStats.circuitBreakerReason }}</span>
        </div>
      </div>

      <div class="flow-arrow">
        <el-icon><ArrowRight /></el-icon>
      </div>

      <!-- 尚书省 -->
      <div class="sheng-card shangshu">
        <div class="sheng-header">
          <el-icon><CircleCheck /></el-icon>
          <span>尚书省</span>
          <el-tag size="small" type="info">执行调度</el-tag>
        </div>
        <div class="sheng-stats">
          <div class="stat-item">
            <span class="stat-value">{{ shangshuStats.submitted }}</span>
            <span class="stat-label">已提交</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-success">{{ shangshuStats.executed }}</span>
            <span class="stat-label">已执行</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-danger">{{ shangshuStats.rejected }}</span>
            <span class="stat-label">失败</span>
          </div>
        </div>
        <div class="pending-orders">
          <span class="pending-label">待处理:</span>
          <el-badge :value="pendingOrders.length" type="warning" />
        </div>
      </div>
    </div>

    <!-- 连接状态 -->
    <div class="connection-status">
      <el-tag :type="wsConnected ? 'success' : 'danger'" size="small">
        <el-icon><Connection /></el-icon>
        {{ wsConnected ? '行情连接正常' : '行情连接断开' }}
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useShengStore } from '@/stores/sheng'
import {
  DataAnalysis,
  TrendCharts,
  Warning,
  CircleCheck,
  ArrowRight,
  Connection,
  CircleClose
} from '@element-plus/icons-vue'

const shengStore = useShengStore()

const {
  crownPrinceStats,
  signalStats,
  menxiaStats,
  shangshuStats,
  signals,
  pendingOrders,
  wsConnected
} = shengStore

const latestSignals = computed(() => signals.slice(0, 3))
</script>

<style scoped lang="scss">
.sheng-flow-monitor {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--el-border-color-light);

  .monitor-title {
    margin: 0 0 16px;
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .flow-container {
    display: flex;
    align-items: stretch;
    gap: 8px;
    overflow-x: auto;
  }

  .sheng-card {
    flex: 1;
    min-width: 180px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
    padding: 12px;
    border: 2px solid transparent;
    transition: all 0.3s;

    &.crown-prince {
      border-color: #67c23a;
    }

    &.zhongshu {
      border-color: #409eff;
    }

    &.menxia {
      border-color: #e6a23c;

      &.circuit-breaker {
        border-color: #f56c6c;
        background: #fef0f0;
      }
    }

    &.shangshu {
      border-color: #909399;
    }
  }

  .sheng-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    font-weight: 600;

    .el-icon {
      font-size: 18px;
    }
  }

  .sheng-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;

    .stat-value {
      font-size: 20px;
      font-weight: 700;
      color: var(--el-text-color-primary);

      &.text-success {
        color: #67c23a;
      }

      &.text-danger {
        color: #f56c6c;
      }

      &.text-warning {
        color: #e6a23c;
      }
    }

    .stat-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
    }
  }

  .flow-arrow {
    display: flex;
    align-items: center;
    color: var(--el-text-color-secondary);
    font-size: 20px;
  }

  .latest-signals {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .signal-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      padding: 4px 8px;
      background: var(--el-bg-color);
      border-radius: 4px;

      .signal-symbol {
        font-weight: 600;
      }

      .signal-price {
        color: var(--el-text-color-secondary);
      }
    }
  }

  .circuit-breaker-alert {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px;
    background: #fef0f0;
    border-radius: 4px;
    color: #f56c6c;
    font-size: 12px;
  }

  .pending-orders {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px;
    background: var(--el-bg-color);
    border-radius: 4px;

    .pending-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }

  .connection-status {
    margin-top: 16px;
    text-align: center;
  }
}
</style>
