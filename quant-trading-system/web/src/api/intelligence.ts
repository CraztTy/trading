/**
 * 智能分析 API
 */
import apiClient from './client'

export interface FundamentalRequest {
  code: string
  name?: string
  metrics?: Record<string, number>
}

export interface FundamentalResponse {
  symbol: string
  name?: string
  overall_score: number
  recommendation: string
  valuation: {
    grade: string
    is_undervalued: boolean
    is_overvalued: boolean
    upside_potential?: number
  }
  growth: {
    grade: string
    is_high_growth: boolean
    revenue_assessment?: string
  }
  profitability: {
    grade: string
    is_high_quality: boolean
  }
  health: {
    grade: string
    red_flags: string[]
    strengths: string[]
  }
  analysis_time: string
}

export interface ScreenRequest {
  pe_min?: number
  pe_max?: number
  pb_min?: number
  pb_max?: number
  roe_min?: number
  roa_min?: number
  gross_margin_min?: number
  revenue_growth_min?: number
  profit_growth_min?: number
  market_cap_min?: number
  market_cap_max?: number
  industries?: string[]
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export interface ScreenResult {
  symbol: string
  name: string
  industry?: string
  price?: number
  pe_ttm?: number
  pb?: number
  roe?: number
  market_cap?: number
}

export interface ScreenResponse {
  total_count: number
  filtered_count: number
  execution_time_ms: number
  stocks: ScreenResult[]
}

export interface MultiFactorRequest {
  stocks: Array<{
    symbol: string
    name?: string
    pe_ttm?: number
    pb?: number
    roe?: number
    revenue_growth?: number
    profit_growth?: number
    [key: string]: any
  }>
  model_type?: 'value' | 'growth' | 'quality' | 'balanced'
}

export interface MultiFactorResult {
  symbol: string
  name?: string
  value_score: number
  quality_score: number
  growth_score: number
  momentum_score: number
  risk_score: number
  total_score: number
  rank: number
  percentile: number
}

export interface MacroAnalysis {
  economic_cycle: {
    cycle: string
    confidence: number
    key_indicators: Record<string, string>
    implications: string
  }
  policy_direction: {
    monetary_policy: string
    key_rates: Record<string, string>
    market_impact: string
  }
  analysis_time: string
}

export interface IndustryAnalysis {
  industry_name: string
  report_type: string
  title: string
  summary: string
  key_points: string[]
  recommendations: string[]
  analysis_time: string
}

export const intelligenceApi = {
  // 基本面分析
  analyzeFundamental: (data: FundamentalRequest) =>
    apiClient.post<FundamentalResponse>('/intelligence/fundamental', data),

  // 批量基本面分析
  batchAnalyzeFundamental: (codes: string[], stocksData?: any[]) =>
    apiClient.post('/intelligence/fundamental/batch', { codes, stocks_data: stocksData }),

  // 智能选股
  screenStocks: (params: ScreenRequest) =>
    apiClient.post<ScreenResponse>('/intelligence/screen', params),

  // 预设选股策略
  presetScreening: (presetName: string, limit?: number) =>
    apiClient.get(`/intelligence/screen/presets/${presetName}`, { params: { limit } }),

  // 多因子评分
  multifactorScore: (data: MultiFactorRequest) =>
    apiClient.post<{ results: MultiFactorResult[]; model_type: string }>('/intelligence/multifactor', data),

  // 宏观分析
  getMacroAnalysis: () =>
    apiClient.get<MacroAnalysis>('/intelligence/macro'),

  // 行业分析
  analyzeIndustry: (industryName: string, reportType?: string) =>
    apiClient.post<IndustryAnalysis>('/intelligence/industry', {
      industry_name: industryName,
      report_type: reportType || '深度研究'
    })
}

export default intelligenceApi
