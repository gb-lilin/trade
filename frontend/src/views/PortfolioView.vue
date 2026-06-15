<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const portfolio = ref<any>(null)
const symbol = ref('600519')
const side = ref('buy')
const weight = ref(0.1)
const msg = ref('')

async function load() {
  const res = await api.portfolio()
  portfolio.value = res.data
}

async function trade() {
  msg.value = ''
  const res = await api.paperTrade({ symbol: symbol.value, side: side.value, weight: weight.value })
  msg.value = res.data.ok ? `成交：${res.data.side} ${res.data.shares} 股` : res.data.message
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <h1 class="page-title">模拟持仓</h1>
    <div class="card" style="margin-bottom: 1rem">
      <div class="form-row">
        <input v-model="symbol" placeholder="股票代码" />
        <select v-model="side">
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
        <input v-model.number="weight" type="number" step="0.01" min="0.01" max="0.25" style="width: 100px" />
        <button class="btn" @click="trade">下单</button>
      </div>
      <p v-if="msg" class="muted">{{ msg }}</p>
    </div>
    <div v-if="portfolio" class="grid grid-3">
      <div class="card">
        <h3>权益</h3>
        <div class="metric">{{ portfolio.equity.toLocaleString() }}</div>
      </div>
      <div class="card">
        <h3>市值</h3>
        <div class="metric">{{ portfolio.market_value.toLocaleString() }}</div>
      </div>
      <div class="card">
        <h3>现金</h3>
        <div class="metric">{{ portfolio.cash.toLocaleString() }}</div>
      </div>
    </div>
    <div v-if="portfolio" class="card" style="margin-top: 1rem">
      <h3>持仓明细</h3>
      <table>
        <thead>
          <tr><th>代码</th><th>数量</th><th>成本</th><th>现价</th><th>盈亏%</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in portfolio.positions" :key="p.symbol">
            <td>{{ p.symbol }}</td>
            <td>{{ p.shares }}</td>
            <td>{{ p.avg_cost }}</td>
            <td>{{ p.current_price }}</td>
            <td :class="p.pnl_pct >= 0 ? 'pos' : 'neg'">{{ p.pnl_pct }}%</td>
          </tr>
          <tr v-if="!portfolio.positions.length">
            <td colspan="5" class="muted">暂无持仓</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
