<template>
  <div class="settings-view">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-subtitle">配置您的交易环境</p>
    </div>

    <div class="settings-grid">
      <div class="settings-nav">
        <button
          v-for="section in sections"
          :key="section.id"
          :class="['nav-item', { active: activeSection === section.id }]"
          @click="activeSection = section.id"
        >
          <el-icon><component :is="section.icon" /></el-icon>
          <span>{{ section.name }}</span>
        </button>
      </div>

      <div class="settings-content">
        <!-- 账户设置 -->
        <div v-if="activeSection === 'account'" class="settings-section">
          <h2>账户设置</h2>
          <div class="setting-item">
            <label>用户名称</label>
            <input type="text" value="John Doe" class="setting-input" />
          </div>
          <div class="setting-item">
            <label>邮箱</label>
            <input type="email" value="john@example.com" class="setting-input" />
          </div>
          <div class="setting-item">
            <label>手机号</label>
            <input type="tel" value="138****8888" class="setting-input" />
          </div>
        </div>

        <!-- 交易设置 -->
        <div v-if="activeSection === 'trading'" class="settings-section">
          <h2>交易设置</h2>
          <div class="setting-item">
            <label>默认委托类型</label>
            <select class="setting-select">
              <option>限价单</option>
              <option>市价单</option>
            </select>
          </div>
          <div class="setting-item">
            <label>默认数量</label>
            <input type="number" value="100" class="setting-input" />
          </div>
          <div class="setting-item checkbox">
            <input type="checkbox" id="confirm" checked />
            <label for="confirm">下单前确认</label>
          </div>
        </div>

        <!-- 通知设置 -->
        <div v-if="activeSection === 'notifications'" class="settings-section">
          <h2>通知设置</h2>
          <div class="setting-item checkbox">
            <input type="checkbox" id="order-notify" checked />
            <label for="order-notify">订单成交通知</label>
          </div>
          <div class="setting-item checkbox">
            <input type="checkbox" id="price-alert" checked />
            <label for="price-alert">价格预警通知</label>
          </div>
          <div class="setting-item checkbox">
            <input type="checkbox" id="risk-alert" checked />
            <label for="risk-alert">风险预警通知</label>
          </div>
        </div>

        <!-- 显示设置 -->
        <div v-if="activeSection === 'display'" class="settings-section">
          <h2>显示设置</h2>
          <div class="setting-item">
            <label>主题</label>
            <select class="setting-select">
              <option>暗黑</option>
              <option>浅色</option>
            </select>
          </div>
          <div class="setting-item">
            <label>语言</label>
            <select class="setting-select">
              <option>简体中文</option>
              <option>English</option>
            </select>
          </div>
          <div class="setting-item">
            <label>刷新频率</label>
            <select class="setting-select">
              <option>1秒</option>
              <option>3秒</option>
              <option>5秒</option>
            </select>
          </div>
        </div>

        <button class="save-btn" @click="saveSettings">保存设置</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { User, Money, Bell, Monitor } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const activeSection = ref('account')

const sections = [
  { id: 'account', name: '账户设置', icon: User },
  { id: 'trading', name: '交易设置', icon: Money },
  { id: 'notifications', name: '通知设置', icon: Bell },
  { id: 'display', name: '显示设置', icon: Monitor }
]

const saveSettings = () => {
  ElMessage.success('设置已保存')
}
</script>

<style scoped lang="scss">
.settings-view {
  max-width: 1000px;
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

.settings-grid {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: var(--space-6);
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);

  .nav-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
    }

    &.active {
      background: rgba(212, 175, 55, 0.15);
      border-color: var(--accent-gold);
      color: var(--accent-gold);
    }

    .el-icon {
      font-size: var(--text-lg);
    }
  }
}

.settings-content {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.settings-section {
  h2 {
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-5);
  }
}

.setting-item {
  margin-bottom: var(--space-4);

  &:last-child {
    margin-bottom: 0;
  }

  &.checkbox {
    display: flex;
    align-items: center;
    gap: var(--space-3);

    input[type="checkbox"] {
      width: 18px;
      height: 18px;
      accent-color: var(--accent-gold);
    }

    label {
      margin-bottom: 0;
    }
  }

  label {
    display: block;
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-bottom: var(--space-2);
  }

  .setting-input,
  .setting-select {
    width: 100%;
    padding: var(--space-3);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: var(--text-sm);

    &:focus {
      outline: none;
      border-color: var(--accent-gold);
    }
  }
}

.save-btn {
  margin-top: var(--space-6);
  padding: var(--space-3) var(--space-6);
  background: var(--accent-gold);
  border: none;
  border-radius: var(--radius-md);
  color: var(--bg-primary);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    box-shadow: var(--shadow-gold);
  }
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .settings-nav {
    flex-direction: row;
    overflow-x: auto;

    .nav-item span {
      white-space: nowrap;
    }
  }
}
</style>
