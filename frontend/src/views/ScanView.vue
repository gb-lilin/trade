<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'
import { strategyLabel } from '../utils/labels'

const loading = ref(false)
const items = ref<any[]>([])
const symbols = ref('')

async function runScan() {
  loading.value = true
  try {
    const res = await api.scan(symbols.value || undefined)
    items.value = res.data.items
  } finally {
    loading.value = false
  }
}

runScan()
</script>

<template>
  <div>
    <h1 class="page-title">选股扫描</h1>
    <div class="form-row">
      <input v-model="symbols" placeholder="可选：600519,000858（逗号分隔）" style="min-width: 280px" />
      <button class="btn" :disabled="loading" @click="runScan">{{ loading ? '扫描中…' : '重新扫描' }}</button>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr><th>代码</th><th>名称</th><th>策略</th><th>综合分</th><th>RSI因子</th><th>超跌</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.symbol">
            <td>{{ row.symbol }}</td>
            <td>{{ row.name || row.symbol }}</td>
            <td>{{ strategyLabel(row.strategy) }}</td>
            <td>{{ row.composite_score }}</td>
            <td>{{ (row.factors.rsi_14 ?? 0).toFixed(3) }}</td>
            <td>{{ (row.factors.oversold_score ?? 0).toFixed(3) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
