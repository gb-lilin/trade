<script setup lang="ts">
import { nextTick, ref } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api/client'

const symbol = ref('600519')
const loading = ref(false)
const stats = ref<any>(null)
const chartEl = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

async function run() {
  loading.value = true
  try {
    const res = await api.backtest(symbol.value, 120)
    stats.value = res.data
    await nextTick()
    if (chartEl.value) {
      chart?.dispose()
      chart = echarts.init(chartEl.value)
      chart.setOption({
        backgroundColor: 'transparent',
        textStyle: { color: '#8b9cb3' },
        grid: { left: 48, right: 16, top: 24, bottom: 32 },
        xAxis: { type: 'category', data: res.data.equity_curve.map((x: any) => x.date) },
        yAxis: { type: 'value', scale: true },
        series: [
          {
            type: 'line',
            data: res.data.equity_curve.map((x: any) => x.equity),
            smooth: true,
            lineStyle: { color: '#3b82f6' },
            areaStyle: { color: 'rgba(59,130,246,0.15)' },
          },
        ],
      })
    }
  } finally {
    loading.value = false
  }
}

run()
</script>

<template>
  <div>
    <h1 class="page-title">策略回测</h1>
    <div class="form-row">
      <input v-model="symbol" placeholder="股票代码" />
      <button class="btn" :disabled="loading" @click="run">运行回测</button>
    </div>
    <div v-if="stats" class="grid grid-3">
      <div class="card"><h3>总收益</h3><div class="metric" :class="stats.total_return_pct >= 0 ? 'pos' : 'neg'">{{ stats.total_return_pct }}%</div></div>
      <div class="card"><h3>最大回撤</h3><div class="metric neg">{{ stats.max_drawdown_pct }}%</div></div>
      <div class="card"><h3>Sharpe / 交易次数</h3><div class="metric">{{ stats.sharpe }} / {{ stats.trades }}</div></div>
    </div>
    <div class="card" style="margin-top: 1rem">
      <div ref="chartEl" class="chart" />
    </div>
  </div>
</template>
