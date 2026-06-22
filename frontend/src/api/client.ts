import axios from 'axios'

const client = axios.create({ baseURL: '/api', timeout: 30000 })

export const api = {
  health: () => client.get('/health'),
  dashboard: (refresh = false) =>
    client.get('/dashboard', { params: refresh ? { refresh: true } : {} }),
  scan: (symbols?: string) => client.get('/scan', { params: symbols ? { symbols } : {} }),
  etfRecommend: (limit = 10) => client.get('/etf/recommend', { params: { limit } }),
  portfolio: () => client.get('/portfolio'),
  paperTrade: (body: { symbol: string; side: string; weight?: number }) =>
    client.post('/paper/trade', body),
  backtest: (symbol: string, limit = 120) => client.post('/backtest', { symbol, limit }),
  monitorAlerts: () => client.get('/monitor/alerts'),
  riskParams: () => client.get('/risk/params'),
  getRiskSettings: () => client.get('/risk/settings'),
  updateRiskSettings: (body: Record<string, unknown>) => client.put('/risk/settings', body),
  setSymbolRiskSettings: (symbol: string, rules: Record<string, unknown>) =>
    client.put(`/risk/settings/symbol/${symbol}`, { rules }),
  clearSymbolRiskSettings: (symbol: string) => client.delete(`/risk/settings/symbol/${symbol}`),
  news: (refresh = false, limit = 30) =>
    client.get('/news', { params: { limit, refresh } }),
  newsRefresh: () => client.post('/news/refresh'),
  newsPush: (maxItems = 8) => client.post('/news/push', null, { params: { max_items: maxItems } }),
  newsPushRefresh: (maxItems = 8) =>
    client.post('/news/push-refresh', null, { params: { max_items: maxItems } }),
}

export type DashboardData = Awaited<ReturnType<typeof api.dashboard>>['data']
