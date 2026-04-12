<template>
  <el-drawer
    v-model="visible"
    :title="isEdit ? '编辑策略' : '新建策略'"
    size="60%"
    :close-on-click-modal="false"
    class="strategy-editor-drawer"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      class="strategy-form"
    >
      <!-- 基本信息 -->
      <div class="section-title">基本信息</div>
      <el-form-item label="策略名称" prop="name">
        <el-input v-model="form.name" placeholder="输入策略名称" />
      </el-form-item>

      <el-form-item label="策略类型" prop="strategy_type">
        <el-select v-model="form.strategy_type" placeholder="选择类型" class="type-select">
          <el-option label="技术分析" value="technical" />
          <el-option label="基本面" value="fundamental" />
          <el-option label="量化" value="quant" />
          <el-option label="机器学习" value="ml" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="描述策略的逻辑和特点"
        />
      </el-form-item>

      <el-form-item label="交易标的" prop="symbols">
        <el-select
          v-model="form.symbols"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入股票代码，如 000001.SZ"
          class="symbols-select"
        >
          <el-option
            v-for="symbol in commonSymbols"
            :key="symbol"
            :label="symbol"
            :value="symbol"
          />
        </el-select>
      </el-form-item>

      <!-- 策略代码 -->
      <div class="section-title">策略代码</div>
      <el-form-item label="Python代码" prop="code" class="code-form-item">
        <div class="code-editor-container">
          <el-input
            v-model="form.code"
            type="textarea"
            :rows="20"
            class="code-editor"
            placeholder="# 在此编写策略代码
from src.strategy.base import StrategyBase, Signal, SignalType

class MyStrategy(StrategyBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化参数
        self.fast_period = self.params.get('fast_period', 5)
        self.slow_period = self.params.get('slow_period', 20)

    def on_bar(self, bar):
        '''处理K线数据'''
        # 实现策略逻辑
        pass

    def on_signal(self, signal):
        '''处理交易信号'''
        pass"
          />
        </div>
      </el-form-item>

      <!-- 参数配置 -->
      <div class="section-title">参数配置</div>
      <div class="params-section">
        <div
          v-for="(param, name) in form.parameters_schema"
          :key="name"
          class="param-item"
        >
          <el-card shadow="never" class="param-card">
            <template #header>
              <div class="param-header">
                <span class="param-name">{{ name }}</span>
                <el-button type="danger" link @click="removeParam(name)">
                  <el-icon><Delete /></el-icon>删除
                </el-button>
              </div>
            </template>

            <div class="param-form">
              <el-form-item label="参数类型" class="compact-form-item">
                <el-select v-model="param.type" size="small" class="param-type-select">
                  <el-option label="整数" value="int" />
                  <el-option label="浮点数" value="float" />
                  <el-option label="布尔值" value="bool" />
                  <el-option label="字符串" value="string" />
                  <el-option label="选项" value="choice" />
                </el-select>
              </el-form-item>

              <el-form-item label="默认值" class="compact-form-item">
                <el-input
                  v-if="param.type === 'bool'"
                  v-model="form.default_parameters[name]"
                  size="small"
                  placeholder="true 或 false"
                />
                <el-input
                  v-else
                  v-model="form.default_parameters[name]"
                  size="small"
                />
              </el-form-item>

              <!-- 根据类型显示不同配置 -->
              <template v-if="['int', 'float'].includes(param.type)">
                <el-form-item label="最小值" class="compact-form-item">
                  <el-input-number
                    v-model="param.min"
                    size="small"
                    :precision="param.type === 'float' ? 4 : 0"
                  />
                </el-form-item>
                <el-form-item label="最大值" class="compact-form-item">
                  <el-input-number
                    v-model="param.max"
                    size="small"
                    :precision="param.type === 'float' ? 4 : 0"
                  />
                </el-form-item>
              </template>

              <template v-if="param.type === 'choice'">
                <el-form-item label="选项" class="compact-form-item">
                  <el-input
                    v-model="param.choices"
                    size="small"
                    placeholder="用逗号分隔选项，如: option1,option2,option3"
                  />
                </el-form-item>
              </template>

              <el-form-item label="描述" class="compact-form-item">
                <el-input
                  v-model="param.description"
                  size="small"
                  placeholder="参数说明"
                />
              </el-form-item>
            </div>
          </el-card>
        </div>

        <el-button type="primary" link @click="showAddParamDialog">
          <el-icon><Plus /></el-icon>添加参数
        </el-button>
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <el-button type="primary" :loading="saving" @click="submit">
          保存
        </el-button>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="success" :loading="saving" @click="saveAndRun">
          保存并运行回测
        </el-button>
      </div>
    </el-form>

    <!-- 添加参数对话框 -->
    <el-dialog
      v-model="paramDialogVisible"
      title="添加参数"
      width="400px"
      append-to-body
    >
      <el-form :model="newParam" label-width="80px">
        <el-form-item label="参数名" required>
          <el-input v-model="newParam.name" placeholder="如: fast_period" />
        </el-form-item>
        <el-form-item label="参数类型">
          <el-select v-model="newParam.type" placeholder="选择类型">
            <el-option label="整数" value="int" />
            <el-option label="浮点数" value="float" />
            <el-option label="布尔值" value="bool" />
            <el-option label="字符串" value="string" />
            <el-option label="选项" value="choice" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认值">
          <el-input v-model="newParam.defaultValue" placeholder="默认值" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paramDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddParam">确定</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, ElForm } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { strategyApi, type Strategy } from '@/api/strategy'

type FormInstance = InstanceType<typeof ElForm>

interface Props {
  modelValue: boolean
  strategy?: Strategy
}

const props = defineProps<Props>()
const emit = defineEmits<['update:modelValue', 'saved', 'runBacktest']>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEdit = computed(() => !!props.strategy)
const formRef = ref<FormInstance>()
const saving = ref(false)

const commonSymbols = ['000001.SZ', '000002.SZ', '600000.SH', '600519.SH', '000858.SZ']

const form = reactive({
  name: '',
  description: '',
  strategy_type: 'custom',
  code: '',
  symbols: [] as string[],
  parameters_schema: {} as Record<string, any>,
  default_parameters: {} as Record<string, any>
})

const rules = {
  name: [{ required: true, message: '请输入策略名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入策略代码', trigger: 'blur' }],
  strategy_type: [{ required: true, message: '请选择策略类型', trigger: 'change' }]
}

// 参数对话框
const paramDialogVisible = ref(false)
const newParam = reactive({
  name: '',
  type: 'int',
  defaultValue: ''
})

watch(
  () => props.strategy,
  (val) => {
    if (val) {
      form.name = val.name
      form.description = val.description || ''
      form.strategy_type = val.strategy_type
      form.code = '' // 代码需要单独获取
      form.symbols = [...(val.symbols || [])]
      form.parameters_schema = { ...(val.parameters_schema || {}) }
      form.default_parameters = { ...(val.default_parameters || {}) }
    } else {
      resetForm()
    }
  },
  { immediate: true }
)

const resetForm = (): void => {
  form.name = ''
  form.description = ''
  form.strategy_type = 'custom'
  form.code = ''
  form.symbols = []
  form.parameters_schema = {}
  form.default_parameters = {}
}

const showAddParamDialog = (): void => {
  newParam.name = ''
  newParam.type = 'int'
  newParam.defaultValue = ''
  paramDialogVisible.value = true
}

const confirmAddParam = (): void => {
  if (!newParam.name.trim()) {
    ElMessage.warning('请输入参数名')
    return
  }

  const name = newParam.name.trim()
  if (form.parameters_schema[name]) {
    ElMessage.warning('参数名已存在')
    return
  }

  form.parameters_schema[name] = {
    type: newParam.type,
    description: ''
  }

  // 设置默认值
  let defaultValue: any = newParam.defaultValue
  if (newParam.type === 'int' || newParam.type === 'float') {
    defaultValue = parseFloat(newParam.defaultValue) || 0
  } else if (newParam.type === 'bool') {
    defaultValue = newParam.defaultValue.toLowerCase() === 'true'
  }

  form.default_parameters[name] = defaultValue
  paramDialogVisible.value = false
}

const removeParam = (name: string): void => {
  delete form.parameters_schema[name]
  delete form.default_parameters[name]
}

const submit = async (): Promise<boolean> => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return false

  saving.value = true
  try {
    if (isEdit.value && props.strategy) {
      await strategyApi.updateStrategy(props.strategy.strategy_id, form)
      ElMessage.success('策略更新成功')
    } else {
      await strategyApi.createStrategy(form)
      ElMessage.success('策略创建成功')
    }
    emit('saved')
    visible.value = false
    return true
  } catch (error) {
    ElMessage.error('保存失败')
    return false
  } finally {
    saving.value = false
  }
}

const saveAndRun = async (): Promise<void> => {
  const success = await submit()
  if (success) {
    emit('runBacktest')
  }
}
</script>

<style scoped lang="scss">
.strategy-editor-drawer {
  :deep(.el-drawer__header) {
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
    margin-bottom: 0;
    padding: var(--space-4) var(--space-5);

    .el-drawer__title {
      font-size: var(--text-lg);
      font-weight: 600;
      color: var(--text-primary);
    }
  }

  :deep(.el-drawer__body) {
    background: var(--bg-primary);
    padding: var(--space-4);
  }
}

.strategy-form {
  max-width: 100%;
}

.section-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: var(--space-4) 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-primary);

  &:first-child {
    margin-top: 0;
  }
}

.type-select {
  width: 200px;
}

.symbols-select {
  width: 100%;
}

.code-form-item {
  :deep(.el-form-item__content) {
    width: 100%;
  }
}

.code-editor-container {
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  overflow: hidden;
  width: 100%;
}

.code-editor {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: none;
    padding: var(--space-3);

    &::placeholder {
      color: var(--text-muted);
    }
  }
}

.params-section {
  margin-bottom: var(--space-5);
}

.param-item {
  margin-bottom: var(--space-3);
}

.param-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);

  :deep(.el-card__header) {
    padding: var(--space-3) var(--space-4);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-primary);
  }

  :deep(.el-card__body) {
    padding: var(--space-3) var(--space-4);
  }
}

.param-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-name {
  font-weight: 600;
  color: var(--accent-gold);
  font-family: var(--font-mono);
}

.param-form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.compact-form-item {
  margin-bottom: var(--space-2);

  :deep(.el-form-item__label) {
    font-size: var(--text-sm);
    padding-right: var(--space-2);
  }
}

.param-type-select {
  width: 100%;
}

.form-actions {
  display: flex;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-primary);
  margin-top: var(--space-4);
}
</style>
