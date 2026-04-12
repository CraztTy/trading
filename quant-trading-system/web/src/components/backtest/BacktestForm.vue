<template>
  <div class="backtest-form">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      class="form-container"
    >
      <!-- 股票代码选择 -->
      <el-form-item label="股票代码" prop="symbols">
        <el-select-v2
          v-model="form.symbols"
          :options="symbolOptions"
          placeholder="选择股票（可多选）"
          multiple
          clearable
          filterable
          :loading="loadingSymbols"
          style="width: 100%"
        />
        <div class="form-tip">选择要回测的股票，支持多选</div>
      </el-form-item>

      <!-- 时间范围选择 -->
      <el-form-item label="回测区间" prop="dateRange">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          :disabled-date="disabledDate"
          style="width: 100%"
        />
        <div class="form-tip">建议回测区间不少于6个月</div>
      </el-form-item>

      <!-- 策略选择 -->
      <el-form-item label="选择策略" prop="strategy_id">
        <el-select
          v-model="form.strategy_id"
          placeholder="选择策略"
          style="width: 100%"
          @change="onStrategyChange"
        >
          <el-option
            v-for="s in strategies"
            :key="s.id"
            :label="s.name"
            :value="s.id"
          >
            <div class="strategy-option">
              <span class="strategy-name">{{ s.name }}</span>
              <span class="strategy-desc">{{ s.description }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 初始资金 -->
      <el-form-item label="初始资金" prop="initial_capital">
        <el-input-number
          v-model="form.initial_capital"
          :min="10000"
          :max="100000000"
          :step="10000"
          style="width: 100%"
          :formatter="(val: number) => `¥${val.toLocaleString()}`"
          :parser="(val: string) => Number(val.replace(/[^\d]/g, ''))"
        />
      </el-form-item>

      <!-- 策略参数动态表单 -->
      <template v-if="selectedStrategy && selectedStrategy.params.length > 0">
        <el-divider class="param-divider">
          <span class="divider-text">策略参数</span>
        </el-divider>

        <el-form-item
          v-for="param in selectedStrategy.params"
          :key="param.name"
          :label="param.label"
          :prop="`params.${param.name}`"
        >
          <!-- 数字类型 -->
          <el-input-number
            v-if="param.type === 'number'"
            v-model="form.params[param.name]"
            :min="param.min"
            :max="param.max"
            :step="getStep(param)"
            style="width: 100%"
          />

          <!-- 选择类型 -->
          <el-select
            v-else-if="param.type === 'select'"
            v-model="form.params[param.name]"
            style="width: 100%"
          >
            <el-option
              v-for="opt in param.options"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>

          <!-- 字符串类型 -->
          <el-input
            v-else-if="param.type === 'string'"
            v-model="form.params[param.name]"
            style="width: 100%"
          />

          <!-- 布尔类型 -->
          <el-switch
            v-else-if="param.type === 'boolean'"
            v-model="form.params[param.name]"
          />
        </el-form-item>
      </template>

      <!-- 操作按钮 -->
      <el-form-item class="form-actions">
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="submit"
        >
          <el-icon class="btn-icon"><VideoPlay /></el-icon>
          开始回测
        </el-button>
        <el-button size="large" @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import {
  createBacktestTask,
  type Strategy,
  type StrategyParam
} from '@/api/backtest'

const emit = defineEmits<{
  success: [taskId: string]
}>()

// 表单引用
const formRef = ref<FormInstance>()

// 加载状态
const loadingSymbols = ref(false)
const submitting = ref(false)
const loadingStrategies = ref(false)

// 股票选项
const symbolOptions = ref<{ value: string; label: string }[]>([])

// 策略列表
const strategies = ref<Strategy[]>([])

// 日期范围
const dateRange = ref<[string, string] | null>(null)

// 表单数据
const form = reactive({
  symbols: [] as string[],
  start_date: '',
  end_date: '',
  strategy_id: '',
  initial_capital: 100000,
  params: {} as Record<string, any>
})

// 表单验证规则
const rules: FormRules = {
  symbols: [
    { required: true, message: '请至少选择一只股票', trigger: 'change', type: 'array', min: 1 }
  ],
  dateRange: [
    { required: true, message: '请选择回测区间', trigger: 'change', type: 'array' }
  ],
  strategy_id: [
    { required: true, message: '请选择策略', trigger: 'change' }
  ],
  initial_capital: [
    { required: true, message: '请设置初始资金', trigger: 'blur' },
    { type: 'number', min: 10000, message: '初始资金至少为10,000', trigger: 'blur' }
  ]
}

// 当前选中的策略
const selectedStrategy = computed(() => {
  return strategies.value.find(s => s.id === form.strategy_id)
})

// 是否可以提交
const canSubmit = computed(() => {
  return form.symbols.length > 0 &&
         dateRange.value &&
         dateRange.value[0] &&
         dateRange.value[1] &&
         form.strategy_id &&
         form.initial_capital >= 10000
})

// 监听日期范围变化
watch(dateRange, (val) => {
  if (val && val[0] && val[1]) {
    form.start_date = val[0]
    form.end_date = val[1]
  } else {
    form.start_date = ''
    form.end_date = ''
  }
})

// 禁用未来日期
const disabledDate = (time: Date) => {
  return time.getTime() > Date.now()
}

// 获取步长
const getStep = (param: StrategyParam): number => {
  if (param.min !== undefined && param.max !== undefined) {
    const range = param.max - param.min
    if (range <= 1) return 0.01
    if (range <= 10) return 0.1
    if (range <= 100) return 1
  }
  return 1
}

// 策略变更处理
const onStrategyChange = () => {
  // 重置策略参数
  form.params = {}

  // 设置默认值
  if (selectedStrategy.value) {
    selectedStrategy.value.params.forEach(param => {
      form.params[param.name] = param.default ?? getDefaultValue(param)
    })
  }
}

// 获取默认值
const getDefaultValue = (param: StrategyParam): any => {
  switch (param.type) {
    case 'number':
      return param.min ?? 0
    case 'select':
      return param.options?.[0]?.value ?? ''
    case 'string':
      return ''
    case 'boolean':
      return false
    default:
      return null
  }
}

// 加载股票列表
const loadSymbols = async () => {
  loadingSymbols.value = true
  try {
    // 模拟股票数据，实际应从API获取
    const mockSymbols = [
      { value: '000001.SZ', label: '000001.SZ 平安银行' },
      { value: '000002.SZ', label: '000002.SZ 万科A' },
      { value: '000858.SZ', label: '000858.SZ 五粮液' },
      { value: '002415.SZ', label: '002415.SZ 海康威视' },
      { value: '002594.SZ', label: '002594.SZ 比亚迪' },
      { value: '300750.SZ', label: '300750.SZ 宁德时代' },
      { value: '600000.SH', label: '600000.SH 浦发银行' },
      { value: '600009.SH', label: '600009.SH 上海机场' },
      { value: '600036.SH', label: '600036.SH 招商银行' },
      { value: '600276.SH', label: '600276.SH 恒瑞医药' },
      { value: '600519.SH', label: '600519.SH 贵州茅台' },
      { value: '600900.SH', label: '600900.SH 长江电力' },
      { value: '601012.SH', label: '601012.SH 隆基绿能' },
      { value: '601318.SH', label: '601318.SH 中国平安' },
      { value: '601398.SH', label: '601398.SH 工商银行' },
      { value: '601888.SH', label: '601888.SH 中国中免' },
      { value: '603288.SH', label: '603288.SH 海天味业' },
      { value: '603501.SH', label: '603501.SH 韦尔股份' }
    ]
    symbolOptions.value = mockSymbols
  } catch (error) {
    ElMessage.error('加载股票列表失败')
  } finally {
    loadingSymbols.value = false
  }
}

// 加载策略列表
const loadStrategies = async () => {
  loadingStrategies.value = true
  try {
    // 模拟策略数据，实际应从API获取
    strategies.value = [
      {
        id: 'dual_ma',
        name: '双均线策略',
        description: '基于5日和20日均线的金叉死叉交易信号',
        params: [
          { name: 'short_period', label: '短期均线', type: 'number', min: 3, max: 20, default: 5 },
          { name: 'long_period', label: '长期均线', type: 'number', min: 10, max: 60, default: 20 }
        ]
      },
      {
        id: 'macd',
        name: 'MACD动量策略',
        description: '利用MACD指标的动量效应进行趋势跟踪',
        params: [
          { name: 'fast_period', label: '快线周期', type: 'number', min: 5, max: 20, default: 12 },
          { name: 'slow_period', label: '慢线周期', type: 'number', min: 15, max: 40, default: 26 },
          { name: 'signal_period', label: '信号周期', type: 'number', min: 5, max: 15, default: 9 }
        ]
      },
      {
        id: 'rsi',
        name: 'RSI超买超卖策略',
        description: '基于RSI指标的超买超卖信号进行交易',
        params: [
          { name: 'rsi_period', label: 'RSI周期', type: 'number', min: 5, max: 30, default: 14 },
          { name: 'overbought', label: '超买阈值', type: 'number', min: 60, max: 90, default: 70 },
          { name: 'oversold', label: '超卖阈值', type: 'number', min: 10, max: 40, default: 30 }
        ]
      },
      {
        id: 'bollinger',
        name: '布林带策略',
        description: '基于布林带上下轨的突破和回归策略',
        params: [
          { name: 'bb_period', label: '布林带周期', type: 'number', min: 10, max: 30, default: 20 },
          { name: 'bb_std', label: '标准差倍数', type: 'number', min: 1, max: 3, default: 2 }
        ]
      },
      {
        id: 'value',
        name: '价值投资策略',
        description: '基于PE、PB估值指标的低估值选股策略',
        params: [
          { name: 'pe_threshold', label: 'PE阈值', type: 'number', min: 5, max: 50, default: 20 },
          { name: 'pb_threshold', label: 'PB阈值', type: 'number', min: 0.5, max: 5, default: 2 },
          { name: 'rebalance_days', label: '调仓周期(天)', type: 'number', min: 5, max: 90, default: 30 }
        ]
      }
    ]
  } catch (error) {
    ElMessage.error('加载策略列表失败')
  } finally {
    loadingStrategies.value = false
  }
}

// 提交表单
const submit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 确认提示
  const confirm = await ElMessageBox.confirm(
    `即将对 ${form.symbols.length} 只股票进行回测，时间区间：${form.start_date} 至 ${form.end_date}，初始资金：¥${form.initial_capital.toLocaleString()}`,
    '确认开始回测',
    {
      confirmButtonText: '开始回测',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).catch(() => false)

  if (!confirm) return

  submitting.value = true
  try {
    const response = await createBacktestTask({
      symbols: form.symbols,
      start_date: form.start_date,
      end_date: form.end_date,
      strategy_id: form.strategy_id,
      initial_capital: form.initial_capital,
      params: form.params
    }) as unknown as { task_id: string }

    ElMessage.success('回测任务已创建')
    emit('success', response.task_id)
    reset()
  } catch (error) {
    ElMessage.error('创建回测任务失败')
  } finally {
    submitting.value = false
  }
}

// 重置表单
const reset = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  dateRange.value = null
  form.params = {}
}

// 组件挂载时加载数据
onMounted(() => {
  loadSymbols()
  loadStrategies()
})
</script>

<style scoped lang="scss">
.backtest-form {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--space-6);
}

.form-container {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.form-tip {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

.strategy-option {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .strategy-name {
    font-weight: 600;
    color: var(--text-primary);
  }

  .strategy-desc {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

.param-divider {
  margin: var(--space-5) 0;

  :deep(.el-divider__text) {
    background: var(--bg-tertiary);
    padding: var(--space-2) var(--space-4);
    border-radius: var(--radius-md);
  }

  .divider-text {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--accent-gold);
  }
}

.form-actions {
  margin-top: var(--space-6);
  margin-bottom: 0;

  :deep(.el-form-item__content) {
    justify-content: center;
    gap: var(--space-4);
  }
}

.btn-icon {
  margin-right: var(--space-1);
}

:deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-date-editor) {
  width: 100%;
}
</style>
