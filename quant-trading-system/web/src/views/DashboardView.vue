<template>
  <div class="dashboard-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-glow"></div>
      <div class="header-content">
        <div class="header-title">
          <span class="title-icon">◈</span>
          <h1>系统概览</h1>
          <span class="header-badge">L3</span>
        </div>
        <div class="header-actions">
          <button class="cyber-btn" @click="refreshData" :disabled="loading">
            <span class="btn-icon">↻</span>
            <span class="btn-text">{{ loading ? '加载中...' : '刷新数据' }}</span>
          </button>
          <button class="cyber-btn primary" @click="showCreateOrder = true">
            <span class="btn-icon">+</span>
            <span class="btn-text">新建订单</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <div class="metrics-section">
      <div
        v-for="(metric, index) in computedMetrics"
        :key="metric.label"
        class="metric-card"
        :class="{ 'card-large': metric.large, 'positive': metric.positive, 'negative': metric.negative }"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <div class="card-glow"></div>
        <div class="card-border"></div>

        <div class="metric-header">
          <span class="metric-label">{{ metric.label }}</span>
          <span class="metric-code">{{ metric.code }}</span>
        </div>

        <div class="metric-value">
          <span class="value-main data-value">{{ metric.value }}</span>
          <span v-if="metric.trend" class="value-trend" :class="getTrendClass(metric.trend)">
            {{ metric.trend }}
          </span>
        </div>

        <div class="metric-footer">
          <span class="metric-sub">{{ metric.subtext }}</span>
          <div class="metric-bar">
            <div class="metric-bar-fill" :style="{ width: `${metric.fill || 0}%` }"></div>
          </div>
        </div>

        <div class="corner tl"></div>
        <div class="corner tr"></div>
        <div class="corner bl"></div>
        <div class="corner br"></div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-main">
      <!-- 左侧：资产走势 -->
      <div class="main-panel chart-section">
        <div class="panel-header">
          <div class="header-left">
            <span class="panel-icon">◫</span>
            <h3 class="panel-title">账户资产</h3>
            <span class="live-indicator">
              <span class="live-dot"></span>
              LIVE
            </span>
          </div>
        </div>
        <div class="panel-content">
          <div v-if="accountStore.currentAccount" class="account-stats">
            <div class="stat-row">
              <div class="stat-item">
                <span class="stat-label">初始资金</span>
                <span class="stat-value">¥{{ formatMoney(accountStore.currentAccount.initial_capital) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">当前净值</span>
                <span class="stat-value positive">¥{{ formatMoney(accountStore.totalEquity) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">总收益率</span>
                <span class="stat-value" :class="accountStore.totalReturn >= 0 ? 'positive' : 'negative'">
                  {{ accountStore.totalReturn >= 0 ? '+' : '' }}{{ accountStore.totalReturn.toFixed(2) }}%
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">可用资金</span>
                <span class="stat-value">¥{{ formatMoney(accountStore.currentAccount?.available || 0) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="loading-text">加载中...</div>
        </div>
      </div>

      <!-- 右侧：实时订单 -->
      <div class="side-panel signals-section">
        <div class="panel-header">
          <span class="panel-icon">⚡</span>
          <h3 class="panel-title">活跃订单</h3>
          <span class="panel-badge">{{ orderStore.activeOrderCount }}</span>
        </div>
        <div class="panel-content">
          <div
            v-for="order in orderStore.activeOrders.slice(0, 5)"
            :key="order.order_id"
            class="signal-item"
            :class="order.direction.toLowerCase()"
          >
            <div class="signal-icon">{{ order.direction === 'BUY' ? '▲' : '▼' }}</div>
            <div class="signal-info">
              <span class="signal-symbol">{{ order.symbol }}</span>
              <span class="signal-strategy">{{ order.status }}</span>
            </div>
            <div class="signal-price">
              <span class="price-value">{{ order.price?.toFixed(2) || '市价' }}</span>
              <span class="price-time">{{ order.filled_qty }}/{{ order.qty }}</span>
            </div>
            <button class="cancel-btn" @click="cancelOrder(order.order_id)">撤</button>
          </div>
          <div v-if="orderStore.activeOrders.length === 0" class="empty-text">
            暂无活跃订单
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：持仓与策略 -->
    <div class="dashboard-bottom">
      <!-- 策略状态 -->
      <div class="bottom-panel strategies-panel">
        <div class="panel-header">
          <span class="panel-icon">◈</span>
          <h3 class="panel-title">策略状态</h3>
        </div>
        <div class="panel-content">
          <div v-for="strategy in strategyStore.activeStrategies" :key="strategy.id" class="strategy-item">
            <div class="strategy-info">
              <span class="strategy-name">{{ strategy.name }}</span>
              <span class="strategy-type">{{ strategy.type }}</span>
            </div>
            <div class="strategy-metrics">
              <div class="metric">
                <span class="metric-label">收益</span>
                <span :class="strategy.performance && strategy.performance.return >= 0 ? 'positive' : 'negative'" class="metric-value">
                  {{ strategy.performance?.return?.toFixed(1) || 0 }}%
                </span>
              </div>
              <div class="metric">
                <span class="metric-label">夏普</span>
                <span class="metric-value">{{ strategy.performance?.sharpe?.toFixed(2) || 0 }}</span>
              </div>
            </div>
            <div class="strategy-status">
              <span class="status-dot" :class="strategy.status"></span>
              <span class="status-text">{{ strategy.status === 'active' ? '运行中' : '已暂停' }}</span>
            </div>
          </div>
          <div v-if="strategyStore.activeStrategies.length === 0" class="empty-text">
            暂无运行中策略
          </div>
        </div>
      </div>

      <!-- 最近订单 -->
      <div class="bottom-panel positions-panel">
        <div class="panel-header">
          <span class="panel-icon">◐</span>
          <h3 class="panel-title">最近订单</h3>
        </div>
        <div class="panel-content">
          <table class="cyber-table">
            <thead>
              <tr>
                <th>标的</th>
                <th>方向</th>
                <th>数量</th>
                <th>价格</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orderStore.orders.slice(0, 5)" :key="order.order_id">
                <td>
                  <span class="cell-symbol">{{ order.symbol }}</span>
                </td>
                <td>
                  <span class="cyber-tag" :class="order.direction.toLowerCase()">
                    {{ order.direction === 'BUY' ? '买' : '卖' }}
                  </span>
                </td>
                <td class="data-value">{{ order.qty }}</td>
                <td class="data-value">{{ order.price?.toFixed(2) || '-' }}</td>
                <td>
                  <span class="status-badge" :class="order.status.toLowerCase()">
                    {{ getStatusText(order.status) }}
                  </span>
                </td>
              </tr>
              <tr v-if="orderStore.orders.length === 0">
                <td colspan="5" class="empty-text">暂无订单</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 创建订单弹窗 -->
    <div v-if="showCreateOrder" class="modal-overlay" @click="showCreateOrder = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>新建订单</h3>
          <button class="close-btn" @click="showCreateOrder = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>股票代码</label>
            <input v-model="newOrder.symbol" type="text" placeholder="如: 600519.SH" class="cyber-input">
          </div>
          <div class="form-group">
            <label>股票名称</label>
            <input v-model="newOrder.symbol_name" type="text" placeholder="如: 贵州茅台" class="cyber-input">
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>方向</label>
              <select v-model="newOrder.direction" class="cyber-select">
                <option value="BUY">买入</option>
                <option value="SELL">卖出</option>
              </select>
            </div>
            <div class="form-group">
              <label>数量</label>
              <input v-model.number="newOrder.qty" type="number" placeholder="100" class="cyber-input" min="100" step="100">
            </div>
          </div>
          <div class="form-group">
            <label>价格 (限价单)</label>
            <input v-model.number="newOrder.price" type="number" placeholder="留空为市价单" class="cyber-input" min="0" step="0.01">
          </div>
        </div>
        <div class="modal-footer">
          <button class="cyber-btn" @click="showCreateOrder = false">取消</button>
          <button class="cyber-btn primary" @click="submitOrder" :disabled="orderStore.loading">
            {{ orderStore.loading ? '提交中...' : '确认下单' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAccountStore, useOrderStore, useStrategyStore } from '@/stores'

// Stores
const accountStore = useAccountStore()
const orderStore = useOrderStore()
const strategyStore = useStrategyStore()

// State
const loading = ref(false)
const showCreateOrder = ref(false)
const newOrder = ref({
  symbol: '',
  symbol_name: '',
  direction: 'BUY' as 'BUY' | 'SELL',
  qty: 100,
  price: undefined as number | undefined
})

// 计算指标卡片数据
const computedMetrics = computed(() => {
  const account = accountStore.currentAccount
  if (!account) return []

  const equity = accountStore.totalEquity
  const initial = account.initial_capital
  const totalReturn = ((equity - initial) / initial) * 100
  const available = account.available
  const frozen = account.frozen
  const marketValue = account.market_value

  return [
    {
      label: '总资产',
      code: 'AUM-001',
      value: `¥${formatMoney(equity)}`,
      trend: `${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`,
      subtext: '较初始资金',
      large: true,
      positive: totalReturn >= 0,
      negative: totalReturn < 0,
      fill: Math.min((equity / initial) * 50, 100),
    },
    {
      label: '可用资金',
      code: 'AVL-001',
      value: `¥${formatMoney(available)}`,
      subtext: '可交易资金',
      fill: (available / equity) * 100,
    },
    {
      label: '冻结资金',
      code: 'FRZ-001',
      value: `¥${formatMoney(frozen)}`,
      subtext: '委托占用',
      fill: (frozen / equity) * 100,
    },
    {
      label: '持仓市值',
      code: 'POS-001',
      value: `¥${formatMoney(marketValue)}`,
      subtext: `占比 ${((marketValue / equity) * 100).toFixed(1)}%`,
      fill: (marketValue / equity) * 100,
    },
    {
      label: '活跃订单',
      code: 'ORD-ACT',
      value: orderStore.activeOrderCount.toString(),
      subtext: '待成交',
      fill: Math.min(orderStore.activeOrderCount * 10, 100),
    },
    {
      label: '运行策略',
      code: 'STG-ACT',
      value: strategyStore.activeCount.toString(),
      subtext: '策略数',
      fill: Math.min(strategyStore.activeCount * 20, 100),
    },
  ]
})

// Methods
function formatMoney(value: number): string {
  if (!value) return '0.00'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function getTrendClass(trend: string): string {
  if (trend.startsWith('+')) return 'trend-up'
  if (trend.startsWith('-')) return 'trend-down'
  return 'trend-neutral'
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'CREATED': '已创建',
    'PENDING': '已报',
    'PARTIAL': '部成',
    'FILLED': '已成',
    'CANCELLED': '已撤',
    'REJECTED': '已拒'
  }
  return statusMap[status] || status
}

async function refreshData() {
  loading.value = true
  const accountId = accountStore.currentAccount?.id || 1

  await Promise.all([
    accountStore.fetchAccounts(),
    orderStore.fetchActiveOrders(accountId),
    orderStore.fetchOrders(accountId),
    strategyStore.fetchStrategies()
  ])

  loading.value = false
}

async function cancelOrder(orderId: string) {
  try {
    await orderStore.cancelOrder(orderId)
    alert('撤单成功')
  } catch (err: any) {
    alert('撤单失败: ' + err.message)
  }
}

async function submitOrder() {
  if (!newOrder.value.symbol || !newOrder.value.qty) {
    alert('请填写完整信息')
    return
  }

  try {
    await orderStore.createOrder({
      account_id: accountStore.currentAccount?.id || 1,
      symbol: newOrder.value.symbol,
      symbol_name: newOrder.value.symbol_name,
      direction: newOrder.value.direction,
      qty: newOrder.value.qty,
      price: newOrder.value.price,
      order_type: newOrder.value.price ? 'LIMIT' : 'MARKET'
    })

    alert('下单成功')
    showCreateOrder.value = false
    newOrder.value = { symbol: '', symbol_name: '', direction: 'BUY', qty: 100, price: undefined }
    refreshData()
  } catch (err: any) {
    alert('下单失败: ' + err.message)
  }
}

// Lifecycle
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
/* 样式保持原有设计 */
.dashboard-page {
  animation: fade-in-up 0.6s ease;
}

/* ... 其他样式与原版相同 ... */

/* 添加弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-layer);
  border: 1px solid var(--border-subtle);
  width: 400px;
  max-width: 90%;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-subtle);
}

.modal-header h3 {
  font-family: var(--font-display);
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.cyber-input,
.cyber-select {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 0.875rem;
}

.cyber-input:focus,
.cyber-select:focus {
  outline: none;
  border-color: var(--neon-cyan);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1rem;
  border-top: 1px solid var(--border-subtle);
}

.loading-text,
.empty-text {
  text-align: center;
  padding: 2rem;
  color: var(--text-tertiary);
}

.cancel-btn {
  padding: 0.25rem 0.5rem;
  background: rgba(255, 0, 170, 0.1);
  border: 1px solid var(--neon-magenta);
  color: var(--neon-magenta);
  font-size: 0.625rem;
  cursor: pointer;
}

.cancel-btn:hover {
  background: var(--neon-magenta);
  color: var(--bg-void);
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.625rem;
  text-transform: uppercase;
}

.status-badge.created { background: rgba(255, 184, 0, 0.1); color: var(--signal-hold); }
.status-badge.pending { background: rgba(0, 240, 255, 0.1); color: var(--neon-cyan); }
.status-badge.partial { background: rgba(107, 44, 255, 0.1); color: var(--neon-purple); }
.status-badge.filled { background: rgba(0, 255, 136, 0.1); color: #00ff88; }
.status-badge.cancelled { background: rgba(255, 0, 170, 0.1); color: var(--neon-magenta); }
.status-badge.rejected { background: rgba(255, 0, 0, 0.1); color: #ff0000; }

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 复用原有样式 */
.page-header { position: relative; margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border-subtle); }
.header-glow { position: absolute; bottom: -1px; left: 0; width: 200px; height: 1px; background: linear-gradient(90deg, var(--neon-cyan), transparent); box-shadow: 0 0 20px var(--neon-cyan); }
.header-content { display: flex; justify-content: space-between; align-items: center; }
.header-title { display: flex; align-items: center; gap: 1rem; }
.title-icon { font-size: 1.5rem; color: var(--neon-cyan); text-shadow: 0 0 20px var(--neon-cyan); }
.header-title h1 { font-family: var(--font-display); font-size: 1.75rem; font-weight: 600; color: var(--text-primary); letter-spacing: 0.02em; }
.header-badge { font-family: var(--font-mono); font-size: 0.625rem; padding: 0.25rem 0.75rem; background: var(--neon-cyan-dim); border: 1px solid var(--neon-cyan); color: var(--neon-cyan); letter-spacing: 0.1em; }
.header-actions { display: flex; gap: 1rem; }

.metrics-section { display: grid; grid-template-columns: repeat(6, 1fr); gap: 1rem; margin-bottom: 2rem; }
.metric-card { position: relative; background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%); border: 1px solid var(--border-subtle); padding: 1.25rem; overflow: hidden; animation: fade-in-up 0.6s ease backwards; }
.metric-card:hover { border-color: var(--border-medium); }
.metric-card.positive:hover { border-color: rgba(0, 240, 255, 0.3); box-shadow: 0 0 30px rgba(0, 240, 255, 0.1); }
.metric-card.negative:hover { border-color: rgba(255, 0, 170, 0.3); box-shadow: 0 0 30px rgba(255, 0, 170, 0.1); }
.card-glow { position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent); opacity: 0.3; }
.metric-card.positive .card-glow { background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent); }
.metric-card.negative .card-glow { background: linear-gradient(90deg, transparent, var(--neon-magenta), transparent); }
.corner { position: absolute; width: 6px; height: 6px; border-color: var(--border-medium); }
.corner.tl { top: 0; left: 0; border-top: 1px solid; border-left: 1px solid; }
.corner.tr { top: 0; right: 0; border-top: 1px solid; border-right: 1px solid; }
.corner.bl { bottom: 0; left: 0; border-bottom: 1px solid; border-left: 1px solid; }
.corner.br { bottom: 0; right: 0; border-bottom: 1px solid; border-right: 1px solid; }
.metric-card.positive .corner { border-color: rgba(0, 240, 255, 0.3); }
.metric-card.negative .corner { border-color: rgba(255, 0, 170, 0.3); }
.metric-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.metric-label { font-size: 0.75rem; color: var(--text-tertiary); }
.metric-code { font-family: var(--font-mono); font-size: 0.625rem; color: var(--text-muted); letter-spacing: 0.05em; }
.metric-value { display: flex; align-items: baseline; gap: 0.75rem; margin-bottom: 1rem; }
.value-main { font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; color: var(--text-primary); }
.value-trend { font-family: var(--font-mono); font-size: 0.75rem; font-weight: 600; }
.value-trend.trend-up { color: var(--signal-buy); }
.value-trend.trend-down { color: var(--signal-sell); }
.metric-footer { display: flex; flex-direction: column; gap: 0.5rem; }
.metric-sub { font-size: 0.625rem; color: var(--text-tertiary); }
.metric-bar { height: 2px; background: var(--bg-elevated); overflow: hidden; }
.metric-bar-fill { height: 100%; background: linear-gradient(90deg, var(--neon-cyan), var(--neon-amber)); transition: width 0.6s ease; }
.metric-card.positive .metric-bar-fill { background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple)); }
.metric-card.negative .metric-bar-fill { background: linear-gradient(90deg, var(--neon-magenta), var(--neon-amber)); }

.dashboard-main { display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
.main-panel, .side-panel { background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%); border: 1px solid var(--border-subtle); position: relative; }
.main-panel::before, .side-panel::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, var(--neon-cyan), transparent); opacity: 0.5; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.5rem; border-bottom: 1px solid var(--border-subtle); background: var(--bg-surface); }
.header-left { display: flex; align-items: center; gap: 0.75rem; }
.panel-icon { font-size: 1rem; color: var(--neon-cyan); }
.panel-title { font-family: var(--font-display); font-size: 0.9375rem; font-weight: 600; color: var(--text-primary); }
.live-indicator { display: flex; align-items: center; gap: 0.375rem; font-family: var(--font-mono); font-size: 0.625rem; letter-spacing: 0.1em; color: var(--neon-magenta); margin-left: 0.5rem; }
.live-dot { width: 6px; height: 6px; background: var(--neon-magenta); border-radius: 50%; animation: blink 1s ease-in-out infinite; }
.panel-badge { font-family: var(--font-mono); font-size: 0.625rem; padding: 0.25rem 0.5rem; background: var(--neon-cyan-dim); border: 1px solid var(--neon-cyan); color: var(--neon-cyan); }
.panel-content { padding: 1.5rem; }
.panel-footer { padding: 1rem 1.5rem; border-top: 1px solid var(--border-subtle); background: var(--bg-surface); }
.stat-row { display: flex; justify-content: space-around; gap: 1rem; }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; }
.stat-label { font-family: var(--font-mono); font-size: 0.625rem; letter-spacing: 0.1em; color: var(--text-tertiary); }
.stat-value { font-family: var(--font-mono); font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
.stat-value.positive { color: var(--signal-buy); text-shadow: 0 0 10px rgba(0, 240, 255, 0.3); }
.stat-value.negative { color: var(--signal-sell); }

.signals-section .panel-content { display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; }
.signal-item { position: relative; display: flex; align-items: center; gap: 0.75rem; padding: 0.875rem 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); cursor: pointer; transition: all 0.3s ease; overflow: hidden; }
.signal-item:hover { border-color: var(--border-medium); }
.signal-icon { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 0.625rem; border-radius: 50%; }
.signal-item.buy .signal-icon { background: rgba(0, 240, 255, 0.1); color: var(--signal-buy); }
.signal-item.sell .signal-icon { background: rgba(255, 0, 170, 0.1); color: var(--signal-sell); }
.signal-info { display: flex; flex-direction: column; gap: 0.125rem; flex: 1; }
.signal-symbol { font-family: var(--font-mono); font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
.signal-strategy { font-size: 0.625rem; color: var(--text-tertiary); }
.signal-price { display: flex; flex-direction: column; align-items: flex-end; gap: 0.125rem; }
.price-value { font-family: var(--font-mono); font-size: 0.875rem; font-weight: 600; color: var(--neon-amber); }
.price-time { font-family: var(--font-mono); font-size: 0.625rem; color: var(--text-muted); }

.dashboard-bottom { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.bottom-panel { background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%); border: 1px solid var(--border-subtle); position: relative; }
.bottom-panel::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, var(--neon-cyan), transparent); opacity: 0.5; }

.strategies-panel .panel-content { padding: 1rem; }
.strategy-item { display: flex; align-items: center; justify-content: space-between; padding: 1rem; border-bottom: 1px solid var(--border-subtle); }
.strategy-item:last-child { border-bottom: none; }
.strategy-info { display: flex; flex-direction: column; gap: 0.25rem; }
.strategy-name { font-weight: 600; color: var(--text-primary); }
.strategy-type { font-size: 0.625rem; color: var(--text-tertiary); }
.strategy-metrics { display: flex; gap: 1.5rem; }
.metric { display: flex; flex-direction: column; align-items: flex-end; gap: 0.125rem; }
.metric-label { font-family: var(--font-mono); font-size: 0.625rem; color: var(--text-tertiary); }
.metric-value { font-family: var(--font-mono); font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
.metric-value.positive { color: var(--signal-buy); }
.metric-value.negative { color: var(--signal-sell); }
.strategy-status { display: flex; align-items: center; gap: 0.5rem; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.active { background: var(--neon-cyan); box-shadow: 0 0 10px var(--neon-cyan); animation: blink 2s ease-in-out infinite; }
.status-dot.paused { background: var(--text-muted); }
.status-text { font-family: var(--font-mono); font-size: 0.625rem; color: var(--text-tertiary); }

.cyber-table { width: 100%; border-collapse: collapse; }
.cyber-table th { font-family: var(--font-mono); font-size: 0.625rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-tertiary); padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border-subtle); background: var(--bg-surface); }
.cyber-table td { padding: 0.875rem 1rem; font-size: 0.875rem; color: var(--text-secondary); border-bottom: 1px solid var(--border-subtle); }
.cyber-table tbody tr:hover { background: var(--bg-surface); }
.cell-symbol { font-family: var(--font-mono); font-weight: 600; color: var(--text-primary); margin-right: 0.5rem; }
.cyber-tag { display: inline-flex; padding: 0.25rem 0.5rem; font-family: var(--font-mono); font-size: 0.625rem; font-weight: 600; }
.cyber-tag.buy { background: rgba(0, 240, 255, 0.1); color: var(--signal-buy); border: 1px solid rgba(0, 240, 255, 0.3); }
.cyber-tag.sell { background: rgba(255, 0, 170, 0.1); color: var(--signal-sell); border: 1px solid rgba(255, 0, 170, 0.3); }

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@media (max-width: 1400px) {
  .metrics-section { grid-template-columns: repeat(3, 1fr); }
  .dashboard-main, .dashboard-bottom { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .metrics-section { grid-template-columns: repeat(2, 1fr); }
  .header-content { flex-direction: column; gap: 1rem; align-items: flex-start; }
}
</style>
