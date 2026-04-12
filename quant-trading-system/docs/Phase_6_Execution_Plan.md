# Phase 6 智能分析执行计划

## 现状分析

**已有基础 (完成度 75%)**:
- ✅ 基本面分析引擎 (`analyzer.py`) - 695行完整实现
  - 估值分析 (PE/PB/PEG)
  - 成长性分析 (营收/利润增长)
  - 盈利能力分析 (ROE/毛利率)
  - 财务健康分析 (流动比率/负债率)
  - 综合评分和投资建议

- ✅ 股票筛选器 (`screener.py`) - 477行完整实现
  - 基本面筛选 (PE/PB/ROE/增长率)
  - 市值筛选 (大盘/中盘/小盘)
  - 行业板块筛选
  - 技术面筛选 (价格/成交量)
  - 预设策略 (价值/成长/红利/蓝筹)

- ✅ 多因子模型 (`factors.py`) - 488行完整实现
  - 价值/质量/成长/动量/风险/规模因子
  - Z-Score标准化
  - 多模型构建器 (价值/成长/质量/平衡)

- ✅ 前端选股视图 (`ScreenerView.vue`) - 731行
  - 界面已完善，使用静态数据

- ⚠️ API 端点 (`intelligence.py`) - 只有 mock 数据

## 任务分解

### Task 1: 完善智能分析 API (3h)
**文件**: `src/api/v1/endpoints/intelligence.py` [MODIFY]

将现有的 mock API 改为使用真实引擎：
- `/fundamental` - 使用 `FundamentalAnalyzer`
- `/screen` - 使用 `StockScreener` + `MultiFactorModel`
- `/industry` - 行业分析
- `/macro` - 宏观分析（保持 mock）

### Task 2: 创建前端 API 客户端 (1h)
**文件**: `web/src/api/intelligence.ts` [NEW]

### Task 3: 更新前端选股视图 (2h)
**文件**: `web/src/views/ScreenerView.vue` [MODIFY]
- 连接真实 API
- 添加加载状态
- 错误处理

### Task 4: 编写集成测试 (2h)
**文件**: `tests/integration/test_intelligence.py` [NEW]

## 交付标准

- [ ] 基本面分析返回真实评分
- [ ] 智能选股支持多条件筛选
- [ ] 多因子评分可用
- [ ] 前端连接真实数据

## 技术要点

### API 响应格式
```python
{
  "symbol": "600519.SH",
  "overall_score": 85.5,
  "recommendation": "BUY",
  "valuation": {"grade": "B", "is_undervalued": true},
  "growth": {"grade": "A", "is_high_growth": true},
  "profitability": {"grade": "A", "is_high_quality": true},
  "health": {"grade": "B", "red_flags": [], "strengths": [...]}
}
```

### 筛选器 DSL
```python
# 价值股
screener.pe_ratio(max_val=15).pb_ratio(max_val=2).roe(min_val=0.1)

# 成长股
screener.revenue_growth(min_val=0.2).profit_growth(min_val=0.2)

# 小盘成长
screener.small_cap().revenue_growth(min_val=0.3)
```
