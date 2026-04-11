<template>
  <div class="login-page">
    <!-- 背景效果 -->
    <div class="login-bg">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="grid-overlay"></div>
    </div>

    <!-- 左侧品牌区 -->
    <div class="brand-section">
      <div class="brand-content">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 48 48" fill="none">
              <path d="M24 4L4 14v20l20 10 20-10V14L24 4z" stroke="currentColor" stroke-width="2" fill="none"/>
              <path d="M24 4v20l-10 5M24 24l10 5" stroke="currentColor" stroke-width="2"/>
              <circle cx="24" cy="24" r="3" fill="currentColor"/>
            </svg>
          </div>
          <span class="logo-text">QuantPro</span>
        </div>
        <h1 class="brand-title">专业量化交易平台</h1>
        <p class="brand-desc">
          智能策略 · 实时风控 · 数据驱动<br>
          为企业级量化交易提供全方位解决方案
        </p>
        <div class="feature-list">
          <div class="feature-item">
            <el-icon class="feature-icon"><TrendCharts /></el-icon>
            <span>多策略并行回测</span>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><DataAnalysis /></el-icon>
            <span>实时行情监控</span>
          </div>
          <div class="feature-item">
            <el-icon class="feature-icon"><LockIcon /></el-icon>
            <span>金融级风控体系</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="form-section">
      <div class="form-card">
        <div class="form-header">
          <h2 class="form-title">{{ isRegister ? '创建账户' : '欢迎回来' }}</h2>
          <p class="form-subtitle">{{ isRegister ? '已有账户?' : '还没有账户?' }}
            <a href="#" @click.prevent="toggleMode" class="toggle-link">
              {{ isRegister ? '立即登录' : '立即注册' }}
            </a>
          </p>
        </div>

        <!-- 登录表单 -->
        <el-form
          v-if="!isRegister"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="auth-form"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="用户名或邮箱"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <div class="form-options">
            <el-checkbox v-model="rememberMe">记住我</el-checkbox>
            <a href="#" class="forgot-link" @click.prevent="handleForgot">忘记密码?</a>
          </div>
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="authStore.loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form>

        <!-- 注册表单 -->
        <el-form
          v-else
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="auth-form"
          @keyup.enter="handleRegister"
        >
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="用户名 (3-32位字母数字)"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>
          <el-form-item prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="邮箱地址"
              size="large"
              :prefix-icon="Message"
            />
          </el-form-item>
          <el-form-item prop="nickname">
            <el-input
              v-model="registerForm.nickname"
              placeholder="昵称 (可选)"
              size="large"
              :prefix-icon="Avatar"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="密码 (至少8位，含大小写字母和数字)"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="确认密码"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="authStore.loading"
            @click="handleRegister"
          >
            创建账户
          </el-button>
        </el-form>

        <!-- 分隔线 -->
        <div class="divider">
          <span>安全认证</span>
        </div>

        <div class="security-note">
          <el-icon><Lock /></el-icon>
          <span>金融级数据加密保护 · JWT安全认证</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message, Avatar, TrendCharts, DataAnalysis, Lock as LockIcon } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 登录/注册模式切换
const isRegister = ref(false)
const rememberMe = ref(false)

const toggleMode = () => {
  isRegister.value = !isRegister.value
}

// 登录表单
const loginFormRef = ref<FormInstance>()
const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

// 注册表单
const registerFormRef = ref<FormInstance>()
const registerForm = reactive({
  username: '',
  email: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

const validatePass2 = (_rule: any, value: string, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '长度在3-32个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9]+$/, message: '只能包含字母和数字', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '长度在8-128个字符', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, message: '必须包含大小写字母和数字', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validatePass2, trigger: 'blur' }
  ]
}

// 登录处理
const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      const success = await authStore.login({
        username: loginForm.username,
        password: loginForm.password
      })
      if (success) {
        router.push('/')
      }
    }
  })
}

// 注册处理
const handleRegister = async () => {
  if (!registerFormRef.value) return

  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      const success = await authStore.register({
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
        nickname: registerForm.nickname || undefined
      })
      if (success) {
        isRegister.value = false
      }
    }
  })
}

const handleForgot = () => {
  // TODO: 实现忘记密码功能
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

// 背景效果
.login-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;

  .gradient-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.15;

    &.orb-1 {
      width: 600px;
      height: 600px;
      background: var(--accent-gold);
      top: -200px;
      right: -100px;
    }

    &.orb-2 {
      width: 500px;
      height: 500px;
      background: var(--accent-cyan);
      bottom: -150px;
      left: 30%;
    }
  }

  .grid-overlay {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(212, 175, 55, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(212, 175, 55, 0.03) 1px, transparent 1px);
    background-size: 50px 50px;
  }
}

// 品牌区
.brand-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  position: relative;
  z-index: 1;

  @media (max-width: 1024px) {
    display: none;
  }
}

.brand-content {
  max-width: 480px;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-8);
}

.logo-icon {
  width: 48px;
  height: 48px;
  color: var(--accent-gold);

  svg {
    width: 100%;
    height: 100%;
  }
}

.logo-text {
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-dark));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-title {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--space-4);
  line-height: 1.2;
}

.brand-desc {
  font-size: 1.125rem;
  color: var(--text-secondary);
  margin-bottom: var(--space-8);
  line-height: 1.8;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--text-secondary);
  font-size: 1rem;

  .feature-icon {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent-gold);
    font-size: 1.25rem;
  }
}

// 表单区
.form-section {
  flex: 0 0 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  position: relative;
  z-index: 1;

  @media (max-width: 1024px) {
    flex: 1;
  }

  @media (max-width: 640px) {
    padding: var(--space-4);
  }
}

.form-card {
  width: 100%;
  max-width: 420px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-2xl);
  padding: var(--space-8);
  box-shadow: var(--shadow-xl);
}

.form-header {
  text-align: center;
  margin-bottom: var(--space-6);
}

.form-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.form-subtitle {
  color: var(--text-secondary);
  font-size: 0.9375rem;
}

.toggle-link {
  color: var(--accent-gold);
  text-decoration: none;
  font-weight: 500;
  margin-left: var(--space-1);

  &:hover {
    text-decoration: underline;
  }
}

// 表单样式
.auth-form {
  :deep(.el-input__wrapper) {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    box-shadow: none;
    padding: 4px 16px;

    &.is-focus {
      border-color: var(--accent-gold);
      box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.1);
    }

    .el-input__inner {
      color: var(--text-primary);
      height: 44px;

      &::placeholder {
        color: var(--text-muted);
      }
    }

    .el-input__icon {
      color: var(--text-muted);
    }
  }
}

.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: var(--space-4) 0;

  :deep(.el-checkbox__label) {
    color: var(--text-secondary);
  }

  :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
    color: var(--accent-gold);
  }

  :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
    background-color: var(--accent-gold);
    border-color: var(--accent-gold);
  }
}

.forgot-link {
  color: var(--text-muted);
  font-size: 0.875rem;
  text-decoration: none;

  &:hover {
    color: var(--accent-gold);
  }
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 1rem;
  font-weight: 600;
  background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-dark));
  border: none;
  border-radius: var(--radius-lg);
  margin-top: var(--space-4);

  &:hover {
    background: linear-gradient(135deg, var(--accent-gold-light), var(--accent-gold));
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(212, 175, 55, 0.25);
  }
}

// 分隔线
.divider {
  display: flex;
  align-items: center;
  margin: var(--space-6) 0;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-primary);
  }

  span {
    padding: 0 var(--space-4);
    color: var(--text-muted);
    font-size: 0.875rem;
  }
}

.security-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--text-muted);
  font-size: 0.875rem;

  .el-icon {
    color: var(--accent-green);
  }
}
</style>
