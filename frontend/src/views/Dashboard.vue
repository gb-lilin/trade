<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api/client'
import NewsItem from '../components/NewsItem.vue'
import { strategyLabel } from '../utils/labels'

const loading = ref(true)
const data = ref<any>(null)
const error = ref('')

onMounted(async () => {
  try {
    const res = await api.dashboard()
    data.value = res.data
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})

function regimeLabel(r: string) {
  const map: Record<string, string> = {
    bull: '偏多',
    bear: '偏空',
    neutral: '震荡',
    high_vol: '高波动',
  }
  return map[r] || r
}
</script>

<template>
  <div>
    <h1 class="page-title">系统总览</h1>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="error" class="neg">{{ error }}</p>
    <template v-else-if="data">
      <div class="grid grid-3">
        <div class="card">
          <h3>账户权益</h3>
          <div class="metric">{{ data.portfolio.equity.toLocaleString() }}</div>
          <div class="muted">现金 {{ data.portfolio.cash.toLocaleString() }}</div>
        </div>
        <div class="card">
          <h3>市场环境</h3>
          <div class="metric">{{ regimeLabel(data.regime.regime) }}</div>
          <div class="muted">环境系数 ×{{ data.regime.environment_multiplier }}</div>
        </div>
        <div class="card">
          <h3>情绪指数 V2</h3>
          <div class="metric">{{ data.emotion.emotion }}</div>
          <div class="muted">斜率 {{ data.emotion.slope }} · 分位 {{ data.emotion.quantile }}</div>
        </div>
      </div>

      <div class="grid" style="grid-template-columns: 1fr 1fr; margin-top: 1rem">
        <div class="card">
          <h3>市场宽度</h3>
          <table>
            <tbody>
              <tr><td>上涨家数</td><td>{{ data.market.breadth.advancers }}</td></tr>
              <tr><td>下跌家数</td><td>{{ data.market.breadth.decliners }}</td></tr>
              <tr><td>涨停</td><td>{{ data.market.breadth.limit_up }}</td></tr>
              <tr><td>超跌池</td><td>{{ data.market.breadth.oversold_count }}</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card">
          <h3>热门板块</h3>
          <table>
            <thead><tr><th>板块</th><th>涨跌%</th></tr></thead>
            <tbody>
              <tr v-for="s in data.market.hot_sectors" :key="s.name">
                <td>{{ s.name }}</td>
                <td :class="s.change_pct >= 0 ? 'pos' : 'neg'">{{ s.change_pct }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card" style="margin-top: 1rem">
        <div class="card-head">
          <h3>经济 / 财经新闻推送</h3>
          <RouterLink to="/news" class="link-more">查看全部 →</RouterLink>
        </div>
        <NewsItem
          v-for="n in data.news?.items || []"
          :key="n.id"
          :item="n"
          compact
        />
        <p v-if="!(data.news?.items || []).length" class="muted">暂无新闻，请到「财经新闻」页拉取</p>
      </div>

      <div class="card" style="margin-top: 1rem">
        <h3>今日选股 Top10（V5 双策略）</h3>
        <table>
          <thead>
            <tr><th>代码</th><th>策略</th><th>综合分</th></tr>
          </thead>
          <tbody>
            <tr v-for="p in data.picks" :key="p.symbol">
              <td>{{ p.symbol }}</td>
              <td>{{ strategyLabel(p.strategy) }}</td>
              <td>{{ p.composite_score }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.card-head h3 {
  margin: 0;
}
.link-more {
  font-size: 0.85rem;
  color: var(--accent);
  text-decoration: none;
}
</style>
