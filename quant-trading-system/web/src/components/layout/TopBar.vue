<template>
  <header class="top-bar">
    <!-- 左侧：Logo和系统状态 -->
    <div class="left-section">
      <div class="logo" @click="$router.push('/')">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="logo-text">
          <span class="logo-name">QUANT</span>
          <span class="logo-suffix">PRO</span>
        </div>
      </div>

      <div class="system-status">
        <div class="status-indicator">
          <span class="pulse-dot" :class="{ offline: !marketStore.wsConnected }"></span>
          <span class="status-text">{{ marketStore.wsConnected ? '交易中' : '连接中...' }}</span>
        </div>
        <div class="connection-quality">
          <span class="quality-label">延迟</span>
          <span class="quality-value" :class="latencyClass">{{ latency }}ms</span>
        </div>
      </div>
    </div>

    <!-- 中间：市场行情滚动条 -->
    <div class="market-ticker">
      <div class="ticker-track">
        <div
          v-for="item in marketStore.marketIndices"
          :key="item.code"
          class="ticker-item"
        >
          <span class="ticker-symbol">{{ item.code }}</span>
          <span class="ticker-price" :class="getPriceClass(item.change)">
            {{ formatPrice(item.price) }}
          </span>
          <span class="ticker-change" :class="getPriceClass(item.change)">
            {{ formatChange(item.changePct) }}%
          </span>
          <svg
            class="ticker-trend"
            :class="getPriceClass(item.change)"
            viewBox="0 0 24 24"
            width="14"
            height="14"
          >
            <path
              v-if="item.change >= 0"
              d="M7 14l5-5 5 5"
              stroke="currentColor"
              stroke-width="2"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              v-else
              d="M7 10l5 5 5-5"
              stroke="currentColor"
              stroke-width="2"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </div>

        <!-- 分隔线 -->
        <div class="ticker-divider"></div>

        <!-- 北向资金 -->
        <div class="ticker-item north-flow">
          <span class="ticker-symbol">北向资金</span>
          <span class="ticker-price" :class="marketStore.northboundFlow >= 0 ? 'text-up' : 'text-down'">
            {{ formatAmount(marketStore.northboundFlow) }}
          </span>
        </div>

        <!-- 人民币汇率 -->
        <div class="ticker-item">
          <span class="ticker-symbol">离岸人民币</span>
          <span class="ticker-price">7.2450</span>
          <span class="ticker-change text-down">-0.08%</span>
        </div>
      </div>
    </div>

    <!-- 右侧：用户操作 -->
    <div class="right-section">
      <!-- 快速搜索 -->
      <div class="quick-search">
        <el-icon class="search-icon"><Search /></el-icon>
        <input
          type="text"
          placeholder="搜索股票 / 基金 / 代码..."
          class="search-input"
        />
        <span class="search-shortcut">⌘K</span>
      </div>

      <!-- 通知 -->
      <div class="action-btn" :class="{ 'has-badge': notificationCount > 0 }">
        <el-icon><Bell /></el-icon>
        <span v-if="notificationCount > 0" class="badge-count">{{ notificationCount }}</span>
      </div>

      <!-- 设置 -->
      <div class="action-btn" @click="$router.push('/settings')">
        <el-icon><Setting /></el-icon>
      </div>

      <!-- 用户菜单 -->
      <el-dropdown trigger="click" placement="bottom-end" @command="handleUserCommand">
        <div class="user-menu">
          <div class="user-avatar">
            <span class="avatar-text">{{ userInitials }}</span>
          </div>
          <div class="user-info">
            <span class="user-name">{{ authStore.nickname }}</span>
            <span class="user-role">{{ userRole }}</span>
          </div>
          <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu class="user-dropdown">
            <div class="dropdown-header">
              <span class="dropdown-name">{{ authStore.nickname }}</span>
              <span class="dropdown-email">{{ authStore.user?.email }}</span>
            </div>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              <span>个人中心</span>
            </el-dropdown-item>
            <el-dropdown-item command="account">
              <el-icon><Wallet /></el-icon>
              <span>账户管理</span>
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </el-dropdown-item>
            <div class="dropdown-divider"></div>
            <el-dropdown-item command="logout" class="logout-item">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Bell, Setting, ArrowDown, User, Wallet, SwitchButton } from '@element-plus/icons-vue'
import { useMarketStore } from '@/stores/market'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const marketStore = useMarketStore()
const authStore = useAuthStore()

const notificationCount = ref(3)
const latency = ref(23)

// 计算用户头像缩写
const userInitials = computed(() => {
  const name = authStore.nickname || authStore.username || 'U'
  return name.slice(0, 2).toUpperCase()
})

// 用户角色
const userRole = computed(() => {
  if (authStore.user?.is_superuser) return '管理员'
  return '专业版'
})

const latencyClass = computed(() => {
  if (latency.value < 50) return 'excellent'
  if (latency.value < 100) return 'good'
  return 'poor'
})

const formatPrice = (price: number) => {
  return price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatChange = (change: number) => {
  const sign = change >= 0 ? '+' : ''
  return `${sign}${change.toFixed(2)}`
}

const formatAmount = (amount: number) => {
  if (Math.abs(amount) >= 100000000) {
    return `${(amount / 100000000).toFixed(2)}亿`
  }
  return `${(amount / 10000).toFixed(2)}万`
}

const getPriceClass = (change: number) => {
  if (change > 0) return 'text-up'
  if (change < 0) return 'text-down'
  return 'text-neutral'
}

// 用户菜单命令处理
const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/settings')
      break
    case 'account':
      router.push('/settings')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '退出确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        await authStore.logout()
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}
</script>

<style scoped lang="scss">
.top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: linear-gradient(180deg,
    rgba(17, 17, 24, 0.98) 0%,
    rgba(17, 17, 24, 0.95) 100%
  );
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  z-index: 1000;
}

// 左侧区域
.left-section {
  display: flex;
  align-items: center;
  gap: var(--space-8);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;

  .logo-icon {
    width: 40px;
    height: 40px;
    background: var(--gradient-gold);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--bg-primary);
    box-shadow: var(--shadow-gold);

    svg {
      width: 24px;
      height: 24px;
    }
  }

  .logo-text {
    display: flex;
    align-items: baseline;
    gap: 4px;

    .logo-name {
      font-family: var(--font-display);
      font-size: var(--text-xl);
      font-weight: 700;
      letter-spacing: 2px;
      color: var(--text-primary);
    }

    .logo-suffix {
      font-family: var(--font-mono);
      font-size: var(--text-sm);
      font-weight: 600;
      color: var(--accent-gold);
      letter-spacing: 1px;
    }
  }
}

.system-status {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  padding-left: var(--space-5);
  border-left: 1px solid var(--border-primary);

  .status-indicator {
    display: flex;
    align-items: center;
    gap: var(--space-2);

    .pulse-dot {
      width: 8px;
      height: 8px;
      background: var(--accent-green);
      border-radius: 50%;
      animation: pulse 2s ease-in-out infinite;

      &.offline {
        background: var(--text-muted);
        animation: none;
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.9); }
    }

    .status-text {
      font-size: var(--text-xs);
      font-weight: 500;
      color: var(--accent-green);
      letter-spacing: 0.5px;
    }
  }

  .connection-quality {
    display: flex;
    align-items: center;
    gap: var(--space-2);

    .quality-label {
      font-size: var(--text-xs);
      color: var(--text-muted);
    }

    .quality-value {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      font-weight: 600;
      padding: 2px 6px;
      border-radius: var(--radius-sm);

      &.excellent {
        color: var(--accent-green);
        background: rgba(0, 208, 132, 0.15);
      }

      &.good {
        color: var(--accent-gold);
        background: rgba(212, 175, 55, 0.15);
      }

      &.poor {
        color: var(--accent-red);
        background: rgba(255, 71, 87, 0.15);
      }
    }
  }
}

// 市场行情滚动条
.market-ticker {
  flex: 1;
  max-width: 600px;
  margin: 0 var(--space-8);
  overflow: hidden;
  mask-image: linear-gradient(90deg, transparent 0%, black 5%, black 95%, transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, black 5%, black 95%, transparent 100%);
}

.ticker-track {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  animation: ticker 30s linear infinite;

  &:hover {
    animation-play-state: paused;
  }
}

@keyframes ticker {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
  flex-shrink: 0;

  .ticker-symbol {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--text-muted);
    letter-spacing: 0.5px;
  }

  .ticker-price {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .ticker-change {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 500;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }

  .ticker-trend {
    flex-shrink: 0;
  }

  &.north-flow {
    padding: 0 var(--space-3);
    border-left: 1px solid var(--border-primary);
    border-right: 1px solid var(--border-primary);
  }
}

.ticker-divider {
  width: 1px;
  height: 20px;
  background: var(--border-secondary);
  flex-shrink: 0;
}

// 右侧区域
.right-section {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.quick-search {
  position: relative;
  display: flex;
  align-items: center;

  .search-icon {
    position: absolute;
    left: var(--space-3);
    color: var(--text-muted);
    font-size: var(--text-base);
  }

  .search-input {
    width: 280px;
    height: 38px;
    padding: 0 var(--space-3) 0 36px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    transition: all var(--transition-fast);

    &::placeholder {
      color: var(--text-muted);
    }

    &:focus {
      outline: none;
      border-color: var(--accent-gold);
      box-shadow: 0 0 0 3px var(--accent-gold-glow);
    }
  }

  .search-shortcut {
    position: absolute;
    right: var(--space-3);
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    padding: 2px 6px;
    background: var(--bg-hover);
    border-radius: var(--radius-sm);
  }
}

.action-btn {
  position: relative;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);

  .el-icon {
    font-size: var(--text-lg);
  }

  &:hover {
    border-color: var(--accent-gold);
    color: var(--accent-gold);
  }

  &.has-badge {
    .badge-count {
      position: absolute;
      top: -4px;
      right: -4px;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      background: var(--accent-red);
      color: white;
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 600;
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

.user-menu {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--accent-gold);
  }

  .user-avatar {
    width: 32px;
    height: 32px;
    background: var(--gradient-gold);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;

    .avatar-text {
      font-family: var(--font-display);
      font-size: var(--text-sm);
      font-weight: 700;
      color: var(--bg-primary);
    }
  }

  .user-info {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .user-name {
      font-size: var(--text-sm);
      font-weight: 600;
      color: var(--text-primary);
    }

    .user-role {
      font-size: 10px;
      color: var(--accent-gold);
      font-weight: 500;
    }
  }

  .dropdown-arrow {
    font-size: var(--text-xs);
    color: var(--text-muted);
    transition: transform var(--transition-fast);
  }

  &:hover .dropdown-arrow {
    transform: rotate(180deg);
  }
}

// 用户下拉菜单
.user-dropdown {
  padding: var(--space-2);
  min-width: 200px;

  .dropdown-header {
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border-primary);
    margin-bottom: var(--space-2);

    .dropdown-name {
      display: block;
      font-size: var(--text-sm);
      font-weight: 600;
      color: var(--text-primary);
    }

    .dropdown-email {
      display: block;
      font-size: var(--text-xs);
      color: var(--text-muted);
      margin-top: 2px;
    }
  }

  .dropdown-divider {
    height: 1px;
    background: var(--border-primary);
    margin: var(--space-2) 0;
  }

  .el-dropdown-menu__item {
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-sm);
    margin-bottom: 2px;

    .el-icon {
      margin-right: var(--space-3);
      font-size: var(--text-base);
    }

    span {
      font-size: var(--text-sm);
    }

    &.logout-item {
      color: var(--accent-red) !important;

      .el-icon {
        color: var(--accent-red);
      }

      &:hover {
        background: rgba(255, 71, 87, 0.1) !important;
      }
    }
  }
}

// 响应式
@media (max-width: 1280px) {
  .market-ticker {
    display: none;
  }

  .quick-search {
    .search-input {
      width: 200px;
    }
    .search-shortcut {
      display: none;
    }
  }
}

@media (max-width: 1024px) {
  .system-status {
    display: none;
  }

  .user-info {
    display: none !important;
  }
}

@media (max-width: 768px) {
  .quick-search {
    display: none;
  }
}
</style>
