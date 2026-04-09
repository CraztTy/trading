<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
    </div>

    <div class="settings-layout">
      <!-- 左侧导航 -->
      <div class="settings-nav">
        <button
          v-for="section in settingSections"
          :key="section.id"
          class="nav-item"
          :class="{ active: activeSection === section.id }"
          @click="activeSection = section.id"
        >
          <span class="nav-icon">{{ section.icon }}</span>
          <span class="nav-label">{{ section.name }}</span>
        </button>
      </div>

      <!-- 右侧内容 -->
      <div class="settings-content">
        <!-- 通用设置 -->
        <div v-if="activeSection === 'general'" class="settings-section">
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">界面设置</h3>
            </div>
            <div class="panel-content">
              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">主题模式</span>
                  <span class="setting-desc">选择系统界面主题</span>
                </div>
                <div class="setting-control">
                  <select v-model="settings.theme" class="form-select">
                    <option value="dark">深色模式</option>
                    <option value="light">浅色模式</option>
                    <option value="auto">跟随系统</option>
                  </select>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">语言</span>
                  <span class="setting-desc">界面显示语言</span>
                </div>
                <div class="setting-control">
                  <select v-model="settings.language" class="form-select">
                    <option value="zh">简体中文</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">刷新频率</span>
                  <span class="setting-desc">数据自动刷新间隔</span>
                </div>
                <div class="setting-control">
                  <select v-model="settings.refreshInterval" class="form-select">
                    <option :value="5000">5秒</option>
                    <option :value="10000">10秒</option>
                    <option :value="30000">30秒</option>
                    <option :value="60000">1分钟</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">通知设置</h3>
            </div>
            <div class="panel-content">
              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">交易通知</span>
                  <span class="setting-desc">成交后推送通知</span>
                </div>
                <div class="setting-control">
                  <label class="toggle">
                    <input v-model="settings.notifications.trade" type="checkbox" />
                    <span class="toggle-slider"></span>
                  </label>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">风控告警</span>
                  <span class="setting-desc">风控触发时推送通知</span>
                </div>
                <div class="setting-control">
                  <label class="toggle">
                    <input v-model="settings.notifications.risk" type="checkbox" />
                    <span class="toggle-slider"></span>
                  </label>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">信号提醒</span>
                  <span class="setting-desc">策略信号生成时推送</span>
                </div>
                <div class="setting-control">
                  <label class="toggle">
                    <input v-model="settings.notifications.signal" type="checkbox" />
                    <span class="toggle-slider"></span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 交易设置 -->
        <div v-if="activeSection === 'trading'" class="settings-section">
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">交易参数</h3>
            </div>
            <div class="panel-content">
              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">默认初始资金</span>
                  <span class="setting-desc">回测和模拟交易的默认资金</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-prefix">
                    <span class="prefix">¥</span>
                    <input
                      v-model.number="settings.trading.initialCapital"
                      type="number"
                      class="form-input"
                      step="100000"
                    />
                  </div>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">默认回测周期</span>
                  <span class="setting-desc">回测数据的默认时间粒度</span>
                </div>
                <div class="setting-control">
                  <select v-model="settings.trading.defaultPeriod" class="form-select">
                    <option value="1d">日线</option>
                    <option value="1h">小时线</option>
                    <option value="15m">15分钟线</option>
                  </select>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">滑点设置</span>
                  <span class="setting-desc">模拟交易的滑点比例</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-suffix">
                    <input
                      v-model.number="settings.trading.slippage"
                      type="number"
                      class="form-input"
                      step="0.0001"
                      min="0"
                      max="0.01"
                    />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">佣金费率</span>
                  <span class="setting-desc">券商佣金比例</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-suffix">
                    <input
                      v-model.number="settings.trading.commission"
                      type="number"
                      class="form-input"
                      step="0.0001"
                      min="0"
                      max="0.01"
                    />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">风控参数</h3>
            </div>
            <div class="panel-content">
              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">单票仓位上限</span>
                  <span class="setting-desc">单只股票最大持仓比例</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-suffix">
                    <input
                      v-model.number="settings.risk.maxPositionPerStock"
                      type="number"
                      class="form-input"
                      step="0.01"
                      min="0"
                      max="1"
                    />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">总仓位上限</span>
                  <span class="setting-desc">账户总持仓比例上限</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-suffix">
                    <input
                      v-model.number="settings.risk.maxTotalPosition"
                      type="number"
                      class="form-input"
                      step="0.01"
                      min="0"
                      max="1"
                    />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">止损比例</span>
                  <span class="setting-desc">单笔交易止损线</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-suffix">
                    <input
                      v-model.number="settings.risk.stopLoss"
                      type="number"
                      class="form-input"
                      step="0.001"
                      min="0"
                      max="0.5"
                    />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-name">日亏损熔断</span>
                  <span class="setting-desc">单日最大可承受亏损</span>
                </div>
                <div class="setting-control">
                  <div class="input-with-suffix">
                    <input
                      v-model.number="settings.risk.maxDailyLoss"
                      type="number"
                      class="form-input"
                      step="0.001"
                      min="0"
                      max="0.5"
                    />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 保存按钮 -->
        <div class="settings-footer">
          <button class="btn btn-secondary" @click="resetSettings">重置</button>
          <button class="btn btn-primary" @click="saveSettings">
            <span class="btn-icon">💾</span>
            保存设置
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeSection = ref('general')

const settingSections = [
  { id: 'general', name: '通用设置', icon: '⚙️' },
  { id: 'trading', name: '交易设置', icon: '💹' },
  { id: 'data', name: '数据设置', icon: '📊' },
  { id: 'account', name: '账户设置', icon: '👤' }
]

const settings = ref({
  theme: 'dark',
  language: 'zh',
  refreshInterval: 30000,
  notifications: {
    trade: true,
    risk: true,
    signal: false
  },
  trading: {
    initialCapital: 1000000,
    defaultPeriod: '1d',
    slippage: 0.001,
    commission: 0.0003
  },
  risk: {
    maxPositionPerStock: 0.1,
    maxTotalPosition: 0.5,
    stopLoss: 0.02,
    maxDailyLoss: 0.02
  },
  data: {
    provider: 'akshare',
    tushareToken: '',
    emApiKey: '',
    cacheTTL: 900
  },
  security: {
    twoFactor: false,
    loginAlert: true
  }
})

function resetSettings() {
  if (confirm('确定要重置所有设置吗？')) {
    // 重置逻辑
  }
}

function saveSettings() {
  alert('设置已保存')
}
</script>

<style scoped>
.page-header {
  margin-bottom: 1.5rem;
}

.page-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
}

.settings-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 1.5rem;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.nav-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--bg-secondary);
  border-color: var(--accent-primary);
  color: var(--text-primary);
}

.nav-icon {
  font-size: 1.125rem;
}

.settings-content {
  min-height: 500px;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.panel-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-content {
  padding: 1rem 1.25rem;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.setting-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
}

.setting-desc {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.setting-control {
  display: flex;
  align-items: center;
}

.form-select,
.form-input {
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  color: var(--text-primary);
  font-size: 0.875rem;
  min-width: 150px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.input-with-prefix,
.input-with-suffix {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-prefix .prefix,
.input-with-suffix .suffix {
  position: absolute;
  padding: 0 0.75rem;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.input-with-prefix .prefix {
  left: 0;
}

.input-with-suffix .suffix {
  right: 0;
}

.input-with-prefix .form-input {
  padding-left: 1.75rem;
}

.input-with-suffix .form-input {
  padding-right: 2rem;
}

.toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-elevated);
  border-radius: 24px;
  transition: 0.3s;
}

.toggle-slider::before {
  position: absolute;
  content: '';
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: 0.3s;
}

.toggle input:checked + .toggle-slider {
  background: var(--accent-primary);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.btn-primary {
  background: var(--accent-primary);
  color: var(--bg-primary);
}

.btn-primary:hover {
  background: #fbbf24;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-primary);
}

@media (max-width: 768px) {
  .settings-layout {
    grid-template-columns: 1fr;
  }

  .settings-nav {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .nav-item {
    flex: 1;
    min-width: 120px;
    justify-content: center;
  }

  .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
}
</style>
