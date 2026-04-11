/**
 * 行情数据API
 */
import apiClient from './client'

export interface MarketIndex {
  code: string
  name: string
  price: number
  change: number
  changePct: number
}

export interface StockQuote {
  symbol: string
  name: string
  price: number
  change: number
  changePct: number
  volume: number
  high: number
  low: number
  open: number
  preClose: number
}

export interface TickData {
  symbol: string
  timestamp: string
  price: number
  volume: number
  bid_price?: number
  bid_volume?: number
  ask_price?: number
  ask_volume?: number
  change?: number
  change_pct?: number
  open?: number
  high?: number
  low?: number
  pre_close?: number
}

export interface KLineData {
  symbol: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  period: string
}

export interface StockInfo {
  symbol: string
  name: string
  code?: string
}

// 获取市场指数
export const getMarketIndices = () => {
  return apiClient.get('/market/symbols')
}

// 获取股票列表
export const getStockList = (limit = 100) => {
  return apiClient.get(`/market/stocks/list?limit=${limit}`)
}

// 搜索股票
export const searchStocks = (keyword: string, limit = 10) => {
  return apiClient.get(`/market/stocks/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`)
}

// 获取最新Tick数据
export const getLatestTick = (symbol: string) => {
  return apiClient.get(`/market/tick/${symbol}`)
}

// 获取K线历史数据
export const getKLineHistory = (symbol: string, period = 'daily', limit = 100) => {
  return apiClient.get(`/market/kline/${symbol}?period=${period}&limit=${limit}`)
}

// 获取市场快照
export const getMarketSnapshot = (symbol: string) => {
  return apiClient.get(`/market/snapshot/${symbol}`)
}

// 批量获取Tick数据
export const getBatchTicks = (symbols: string[]) => {
  const symbolStr = symbols.join(',')
  return apiClient.get(`/market/batch/ticks?symbols=${encodeURIComponent(symbolStr)}`)
}

// 获取数据服务状态
export const getDataServiceStatus = () => {
  return apiClient.get('/market/service/status')
}
