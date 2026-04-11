<template>
  <div class="risk-view">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">风险控制</h1>
        <p class="page-subtitle">监控和管理交易风险</p>
      </div>
    </div>

    <div class="risk-grid">
      <div class="risk-card status-card">
        <div class="card-header">
          <h3>风险状态</h3>
          <span class="risk-level safe">安全</span>
        </div>
        <div class="risk-gauge">
          <div class="gauge-value">28</div>
          <div class="gauge-label">风险评分</div>
        </div>
        <div class="risk-items">
          <div class="risk-item">
            <span>仓位集中度</span>
            <span class="value safe">正常</span>
          </div>
          <div class="risk-item">
            <span>杠杆使用率</span>
            <span class="value safe">0%</span>
          </div>
          <div class="risk-item">
            <span>流动性风险</span>
            <span class="value safe">低</span>
          </div>
        </div>
      </div>

      <div class="risk-card limits-card">
        <div class="card-header">
          <h3>风控限额</h3>
        </div>
        <div class="limit-list">
          <div class="limit-item">
            <div class="limit-info">
              <span class="limit-name">单日最大亏损</span>
              <span class="limit-value">¥5,000 / ¥10,000</span>
            </div>
            <div class="limit-bar">
              <div class="bar-fill" style="width: 50%"></div>
            </div>
          </div>
          <div class="limit-item">
            <div class="limit-info">
              <span class="limit-name">单日最大交易次数</span>
              <span class="limit-value">12 / 50</span>
            </div>
            <div class="limit-bar">
              <div class="bar-fill" style="width: 24%"></div>
            </div>
          </div>
          <div class="limit-item">
            <div class="limit-info">
              <span class="limit-name">持仓最大回撤</span>
              <span class="limit-value">3.2% / 10%</span>
            </div>
            <div class="limit-bar">
              <div class="bar-fill" style="width: 32%"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="risk-card alerts-card">
        <div class="card-header">
          <h3>风险预警</h3>
        </div>
        <div class="alert-list">
          <div class="alert-item warning">
            <el-icon><Warning /></el-icon>
            <div class="alert-content">
              <span class="alert-title">单一股票持仓占比过高</span>
              <span class="alert-desc">贵州茅台占比 35%，建议控制在 30% 以内</span>
            </div>
          </div>
          <div class="alert-item info">
            <el-icon><InfoFilled /></el-icon>
            <div class="alert-content">
              <span class="alert-title">市场波动率上升</span>
              <span class="alert-desc">当前市场 VIX 指数为 22，建议谨慎操作</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Warning, InfoFilled } from '@element-plus/icons-vue'
</script>

<style scoped lang="scss">
.risk-view {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
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

.risk-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-5);
}

.risk-card {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-4);

    h3 {
      font-size: var(--text-base);
      font-weight: 600;
      color: var(--text-primary);
    }

    .risk-level {
      padding: 4px 12px;
      border-radius: var(--radius-sm);
      font-size: var(--text-xs);
      font-weight: 600;

      &.safe {
        background: rgba(0, 208, 132, 0.15);
        color: var(--accent-green);
      }

      &.warning {
        background: rgba(255, 149, 0, 0.15);
        color: var(--accent-gold);
      }

      &.danger {
        background: rgba(255, 71, 87, 0.15);
        color: var(--accent-red);
      }
    }
  }
}

.risk-gauge {
  text-align: center;
  padding: var(--space-4) 0;
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-primary);

  .gauge-value {
    font-family: var(--font-mono);
    font-size: var(--text-4xl);
    font-weight: 700;
    color: var(--accent-green);
  }

  .gauge-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin-top: var(--space-2);
  }
}

.risk-items {
  .risk-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--border-primary);

    &:last-child {
      border-bottom: none;
    }

    span:first-child {
      font-size: var(--text-sm);
      color: var(--text-secondary);
    }

    .value {
      font-weight: 600;

      &.safe { color: var(--accent-green); }
      &.warning { color: var(--accent-gold); }
      &.danger { color: var(--accent-red); }
    }
  }
}

.limit-list {
  .limit-item {
    margin-bottom: var(--space-4);

    &:last-child {
      margin-bottom: 0;
    }

    .limit-info {
      display: flex;
      justify-content: space-between;
      margin-bottom: var(--space-2);

      .limit-name {
        font-size: var(--text-sm);
        color: var(--text-secondary);
      }

      .limit-value {
        font-family: var(--font-mono);
        font-size: var(--text-sm);
        color: var(--text-primary);
      }
    }

    .limit-bar {
      height: 6px;
      background: var(--bg-hover);
      border-radius: 3px;

      .bar-fill {
        height: 100%;
        background: var(--accent-gold);
        border-radius: 3px;
        transition: width var(--transition-base);
      }
    }
  }
}

.alert-list {
  .alert-item {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-3);
    border-radius: var(--radius-md);
    margin-bottom: var(--space-3);

    &:last-child {
      margin-bottom: 0;
    }

    &.warning {
      background: rgba(255, 149, 0, 0.1);
      border: 1px solid rgba(255, 149, 0, 0.2);

      .el-icon {
        color: var(--accent-gold);
      }
    }

    &.info {
      background: rgba(0, 217, 255, 0.1);
      border: 1px solid rgba(0, 217, 255, 0.2);

      .el-icon {
        color: var(--accent-cyan);
      }
    }

    &.danger {
      background: rgba(255, 71, 87, 0.1);
      border: 1px solid rgba(255, 71, 87, 0.2);

      .el-icon {
        color: var(--accent-red);
      }
    }

    .alert-content {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .alert-title {
        font-size: var(--text-sm);
        font-weight: 600;
        color: var(--text-primary);
      }

      .alert-desc {
        font-size: var(--text-xs);
        color: var(--text-muted);
      }
    }
  }
}

@media (max-width: 1200px) {
  .risk-grid {
    grid-template-columns: 1fr;
  }
}
</style>
