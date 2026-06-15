const STRATEGY_LABELS: Record<string, string> = {
  oversold_rebound: '超跌反弹',
  limit_up_dragon: '涨停/龙虎榜',
}

const REGIME_LABELS: Record<string, string> = {
  bull: '偏多',
  bear: '偏空',
  neutral: '震荡',
  high_vol: '高波动',
}

const ETF_CATEGORY_LABELS: Record<string, string> = {
  broad: '宽基',
  growth: '成长',
  sector: '行业',
  dividend: '红利',
  commodity: '商品',
  cross_border: '跨境',
  bond: '债券',
}

export function strategyLabel(code: string | undefined | null): string {
  if (!code) return '—'
  return STRATEGY_LABELS[code] ?? code
}

export function regimeLabel(code: string | undefined | null): string {
  if (!code) return '—'
  return REGIME_LABELS[code] ?? code
}

export function etfCategoryLabel(code: string | undefined | null): string {
  if (!code) return '—'
  return ETF_CATEGORY_LABELS[code] ?? code
}
