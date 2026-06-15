<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'
import { etfCategoryLabel, regimeLabel } from '../utils/labels'

const loading = ref(false)
const data = ref<{
  regime: string
  regime_hint: string
  environment_multiplier: number
  items: any[]
  universe_size: number
} | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await api.etfRecommend(12)
    data.value = res.data
  } finally {
    loading.value = false
  }
}

load()
</script>

<template>
  <div>
    <h1 class="page-title">ETF 推荐</h1>
    <div class="form-row">
      <button class="btn" :disabled="loading" @click="load">{{ loading ? '计算中…' : '刷新推荐' }}</button>
    </div>

    <p v-if="loading && !data" class="muted">加载中…</p>

    <template v-else-if="data">
      <div class="grid grid-3" style="margin-bottom: 1rem">
        <div class="card">
          <h3>市场环境</h3>
          <div class="metric">{{ regimeLabel(data.regime) }}</div>
          <div class="muted">环境系数 ×{{ data.environment_multiplier }}</div>
        </div>
        <div class="card">
          <h3>配置思路</h3>
          <p class="hint">{{ data.regime_hint }}</p>
        </div>
        <div class="card">
          <h3>ETF 池</h3>
          <div class="metric">{{ data.universe_size }}</div>
          <div class="muted">只常见场内 ETF</div>
        </div>
      </div>

      <div class="card">
        <h3>推荐列表（按综合得分排序）</h3>
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>类型</th>
              <th>现价</th>
              <th>涨跌%</th>
              <th>技术分</th>
              <th>环境加成</th>
              <th>综合分</th>
              <th>推荐理由</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data.items" :key="row.symbol">
              <td>{{ row.symbol }}</td>
              <td>{{ row.name }}</td>
              <td>{{ etfCategoryLabel(row.category) }}</td>
              <td>{{ row.price?.toFixed(3) ?? '—' }}</td>
              <td :class="row.change_pct >= 0 ? 'pos' : 'neg'">{{ row.change_pct }}%</td>
              <td>{{ row.composite_score }}</td>
              <td>{{ row.regime_bonus }}</td>
              <td><strong>{{ row.final_score }}</strong></td>
              <td class="reason">{{ row.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.hint {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-muted, #8b949e);
}
.reason {
  max-width: 220px;
  font-size: 0.85rem;
}
</style>
