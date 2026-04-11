# AKShare 数据源功能指南

## 概述

AKShare 是一个开源的 Python 金融数据接口库，基于 Python 的爬虫技术，提供免费的 A 股、港股、基金、期货等金融数据。

## 已接入功能

### 1. 实时行情数据 ✅

**接口**: `stock_zh_a_spot_em()`

**数据字段**:
| 字段 | 说明 |
|------|------|
| 代码 | 股票代码 (如: 000001) |
| 名称 | 股票名称 |
| 最新价 | 当前成交价 |
| 涨跌幅 | 相对昨收的涨跌百分比 |
| 涨跌额 | 涨跌金额 |
| 成交量 | 成交手数 |
| 成交额 | 成交金额 |
| 振幅 | 当日振幅 |
| 最高 | 当日最高价 |
| 最低 | 当日最低价 |
| 今开 | 今日开盘价 |
| 昨收 | 昨日收盘价 |
| 量比 | 量比 |
| 换手率 | 换手率 |
| 市盈率-动态 | 动态市盈率 |
| 市净率 | 市净率 |
| 总市值 | 总市值 |
| 流通市值 | 流通市值 |
| 涨速 | 价格变动速度 |
| 5分钟涨跌 | 近5分钟涨跌 |
| 60日涨跌幅 | 60日涨跌幅 |
| 年初至今涨跌幅 | 年度涨跌幅 |
| 买一-买五 | 5档买盘价格和数量 |
| 卖一-卖五 | 5档卖盘价格和数量 |

**覆盖范围**: 所有 A 股股票（约 5000+ 只）

**更新频率**: 实时（交易时间内3秒延迟）

### 2. 历史K线数据 ✅

**接口**: `stock_zh_a_hist()`

**支持周期**:
- `daily` - 日线
- `weekly` - 周线
- `monthly` - 月线

**数据字段**:
| 字段 | 说明 |
|------|------|
| 日期 | 交易日 |
| 开盘 | 开盘价 |
| 收盘 | 收盘价 |
| 最高 | 最高价 |
| 最低 | 最低价 |
| 成交量 | 成交手数 |
| 成交额 | 成交金额 |
| 振幅 | 当日振幅 |
| 涨跌幅 | 涨跌幅百分比 |
| 涨跌额 | 涨跌金额 |
| 换手率 | 换手率 |

**历史长度**: 可获取上市以来的全部历史数据

**复权方式**: 支持前复权、后复权、不复权

### 3. A股股票列表 ✅

**接口**: `stock_zh_a_spot_em()`

**数据内容**:
- 全部A股代码和名称
- 上海主板、科创板
- 深圳主板、中小板、创业板

---

## 可扩展功能（未接入）

### 实时数据类

#### 1. 分时数据
```python
# 获取分时数据
ak.stock_zh_a_hist_min_em(symbol="000001")
```
- 1分钟K线
- 5分钟K线
- 15分钟K线
- 30分钟K线
- 60分钟K线

#### 2. 分笔成交数据
```python
# 获取分笔成交
ak.stock_zh_a_spot_em()  # 可扩展获取逐笔成交
```

### 基本面数据类

#### 1. 财务报表
```python
# 资产负债表
ak.stock_financial_report_sina(stock="000001", symbol="资产负债表")

# 利润表
ak.stock_financial_report_sina(stock="000001", symbol="利润表")

# 现金流量表
ak.stock_financial_report_sina(stock="000001", symbol="现金流量表")
```

#### 2. 财务指标
```python
# 主要财务指标
ak.stock_financial_analysis_indicator(symbol="000001")
```

#### 3. 股票基本信息
```python
# 个股信息
ak.stock_individual_info_em(symbol="000001")
```

### 市场数据类

#### 1. 大盘指数
```python
# 上证指数
ak.index_zh_a_hist(symbol="000001", period="daily")

# 深证成指
ak.index_zh_a_hist(symbol="399001", period="daily")

# 创业板指
ak.index_zh_a_hist(symbol="399006", period="daily")

# 科创板指
ak.index_zh_a_hist(symbol="000688", period="daily")
```

#### 2. 板块/行业数据
```python
# 行业板块
ak.stock_board_industry_name_em()
ak.stock_board_industry_hist_em(symbol="银行", period="daily")

# 概念板块
ak.stock_board_concept_name_em()
ak.stock_board_concept_hist_em(symbol="锂电池", period="daily")
```

#### 3. 资金流向
```python
# 个股资金流向
ak.stock_individual_fund_flow(stock="000001")

# 行业资金流向
ak.stock_sector_fund_flow_rank()
```

### 特色数据类

#### 1. 龙虎榜数据
```python
# 每日龙虎榜
ak.stock_lhb_detail_daily_sina()
```

#### 2. 融资融券
```python
# 融资数据
ak.stock_margin_detail_szse(date="20240101")
```

#### 3. 港股数据
```python
# 港股实时行情
ak.stock_hk_spot_em()

# 港股历史数据
ak.stock_hk_hist(symbol="00700", period="daily")
```

#### 4. 美股数据
```python
# 中概股
ak.stock_us_spot_em()
```

#### 5. 期货数据
```python
# 商品期货
ak.futures_zh_realtime(symbol="ZN0")
```

#### 6. 基金数据
```python
# ETF数据
ak.fund_etf_hist_em(symbol="510300", period="daily")

# 场外基金
ak.fund_em_open_fund_info(fund="000001")
```

#### 7. 债券数据
```python
# 可转债
ak.bond_zh_hs_cov_spot()
```

#### 8. 宏观经济数据
```python
# 央行存款准备金率
ak.macro_china_reserve_requirement_ratio()

# GDP数据
ak.macro_china_gdp()

# CPI数据
ak.macro_china_cpi()

# PMI数据
ak.macro_china_pmi()
```

#### 9. 新闻公告数据
```python
# 个股新闻
ak.stock_news_em(symbol="000001")

# 公司公告
ak.stock_notice_report()
```

#### 10. 投资者关系数据
```python
# 股东户数
ak.stock_gdfx_free_holding_detail_em()

# 十大流通股东
ak.stock_gdfx_top_ten_free_holder()
```

---

## 数据质量说明

### 优点
1. **免费开源** - 无需付费
2. **数据全面** - 覆盖A股全部标的
3. **更新及时** - 实时行情（3-5秒延迟）
4. **历史悠久** - 可获取上市以来的全部历史数据
5. **接口丰富** - 500+ 个数据接口

### 限制
1. **请求频率** - 需要控制请求频率（建议3秒以上间隔）
2. **网络依赖** - 数据源来自东方财富等网站，受网络影响
3. **非官方** - 非交易所官方数据，仅用于研究参考
4. **稳定性** - 数据源网站改版可能导致接口失效

---

## 使用建议

### 开发环境
- 使用模拟数据（MockProvider）进行开发测试
- 减少对AKShare的实际调用

### 生产环境
1. **缓存策略** - 使用Redis缓存热点数据
2. **降级机制** - AKShare不可用时自动降级到备用数据源
3. **限流控制** - 严格控制请求频率
4. **数据校验** - 对返回数据进行有效性校验

### 数据采集建议
| 数据类型 | 更新频率 | 建议方案 |
|---------|---------|---------|
| 实时行情 | 3-5秒 | WebSocket推送 + 本地缓存 |
| 分时数据 | 1分钟 | 定时任务采集 |
| 日K线 | 每日收盘后 | 盘后批量更新 |
| 财务数据 | 季度 | 定期全量更新 |
| 基础信息 | 每日 | 每日凌晨更新 |

---

## 参考资料

- AKShare 官方文档: https://www.akshare.xyz/
- GitHub: https://github.com/akfamily/akshare
- PyPI: https://pypi.org/project/akshare/
