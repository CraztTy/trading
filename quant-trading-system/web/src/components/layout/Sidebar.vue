<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <!-- 折叠按钮 -->
    <button class="collapse-btn" @click="toggleCollapse">
      <el-icon><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
    </button>

    <!-- 主导航 -->
    <nav class="nav-sections">
      <div
        v-for="section in menuSections"
        :key="section.title"
        class="nav-section"
      >
        <div class="section-header">
          <div class="section-line"></div>
          <span class="section-title">{{ section.title }}</span>
          <div class="section-line"></div>
        </div>

        <div class="nav-items">
          <router-link
            v-for="item in section.items"
            :key="item.path"
            :to="item.path"
            :class="['nav-item', { active: route.path === item.path }]"
          >
            <div class="item-icon">
              <component :is="item.icon" />
              <span v-if="item.badge" class="item-badge">{{ item.badge }}</span>
            </div>

            <div class="item-content">
              <span class="item-label">{{ item.name }}</span>
              <span v-if="item.subtitle" class="item-subtitle">{{ item.subtitle }}</span>
            </div>

            <div class="item-arrow" v-if="!isCollapsed">
              <el-icon><ArrowRight /></el-icon>
            </div>
          </router-link>
        </div>
      </div>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <div class="portfolio-summary">
        <div class="summary-header">
          <span class="summary-label">总资产</span>
          <el-icon><View /></el-icon>
        </div>
        <div class="summary-value">¥{{ isCollapsed ? '128' : '1,284,520.80' }}</div>
        <div class="summary-change text-up">
          <span>+2.45%</span>
          <span v-if="!isCollapsed" class="change-amount">+¥30,680</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Grid,
  TrendCharts,
  Money,
  Box,
  Histogram,
  Aim,
  Document,
  FirstAidKit,
  Setting,
  Fold,
  Expand,
  ArrowRight,
  View
} from '@element-plus/icons-vue'
import type { Component } from 'vue'

const route = useRoute()
const isCollapsed = ref(false)

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

interface MenuItem {
  name: string
  path: string
  icon: Component
  badge?: string
  subtitle?: string
}

interface MenuSection {
  title: string
  items: MenuItem[]
}

const menuSections: MenuSection[] = [
  {
    title: '核心',
    items: [
      { name: '仪表盘', path: '/', icon: Grid },
      { name: '行情中心', path: '/market', icon: TrendCharts },
      { name: '交易下单', path: '/trade', icon: Money, badge: 'Pro' },
      { name: '持仓管理', path: '/positions', icon: Box },
    ]
  },
  {
    title: '分析',
    items: [
      { name: '策略回测', path: '/strategy', icon: Histogram },
      { name: '智能选股', path: '/screener', icon: Aim, subtitle: 'AI驱动' },
      { name: '研究报告', path: '/reports', icon: Document },
    ]
  },
  {
    title: '系统',
    items: [
      { name: '风险控制', path: '/risk', icon: FirstAidKit },
      { name: '系统设置', path: '/settings', icon: Setting },
    ]
  }
]
</script>

<style scoped lang="scss">
.sidebar {
  position: fixed;
  left: 0;
  top: 64px;
  bottom: 0;
  width: 260px;
  background: linear-gradient(180deg,
    rgba(17, 17, 24, 0.98) 0%,
    rgba(10, 10, 15, 0.98) 100%
  );
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-primary);
  z-index: 100;
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base);

  &.collapsed {
    width: 72px;

    .section-header {
      .section-title {
        display: none;
      }
    }

    .nav-item {
      padding: var(--space-3);
      justify-content: center;

      .item-content,
      .item-arrow {
        display: none;
      }
    }

    .portfolio-summary {
      padding: var(--space-3);

      .summary-header,
      .summary-change {
        display: none;
      }
    }
  }
}

.collapse-btn {
  position: absolute;
  top: var(--space-4);
  right: -12px;
  width: 24px;
  height: 24px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-secondary);
  border-radius: 50%;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all var(--transition-fast);

  .el-icon {
    font-size: var(--text-xs);
  }

  &:hover {
    border-color: var(--accent-gold);
    color: var(--accent-gold);
  }
}

.nav-sections {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6) var(--space-4);
}

.nav-section {
  margin-bottom: var(--space-6);

  &:last-child {
    margin-bottom: 0;
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: 0 var(--space-2);

  .section-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      var(--border-secondary) 50%,
      transparent 100%
    );
  }

  .section-title {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 2px;
  }
}

.nav-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 0;
    background: var(--gradient-gold);
    border-radius: 0 2px 2px 0;
    transition: height var(--transition-fast);
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);

    .item-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }

  &.active {
    background: linear-gradient(90deg,
      rgba(212, 175, 55, 0.1) 0%,
      transparent 100%
    );
    color: var(--accent-gold);

    &::before {
      height: 20px;
    }

    .item-icon {
      color: var(--accent-gold);
    }
  }
}

.item-icon {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  flex-shrink: 0;

  .nav-item:hover & {
    border-color: var(--border-secondary);
  }

  .nav-item.active & {
    background: rgba(212, 175, 55, 0.1);
    border-color: var(--accent-gold);
    box-shadow: var(--shadow-gold);
  }
}

.item-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  padding: 1px 4px;
  background: var(--accent-gold);
  color: var(--bg-primary);
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 700;
  border-radius: 3px;
  letter-spacing: 0.5px;
}

.item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.item-label {
  font-size: var(--text-sm);
  font-weight: 500;
}

.item-subtitle {
  font-size: 10px;
  color: var(--accent-cyan);
  font-weight: 500;
}

.item-arrow {
  opacity: 0;
  transform: translateX(-4px);
  color: var(--text-muted);
  transition: all var(--transition-fast);

  .el-icon {
    font-size: var(--text-xs);
  }
}

// 底部资产摘要
.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--border-primary);
}

.portfolio-summary {
  background: linear-gradient(145deg,
    rgba(26, 26, 36, 0.8) 0%,
    rgba(17, 17, 24, 0.8) 100%
  );
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--border-secondary);
  }
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);

  .summary-label {
    font-size: var(--text-xs);
    color: var(--text-muted);
    font-weight: 500;
  }

  .el-icon {
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;

    &:hover {
      color: var(--text-primary);
    }
  }
}

.summary-value {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.summary-change {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;

  .change-amount {
    color: var(--text-muted);
    font-weight: 400;
  }
}
</style>
