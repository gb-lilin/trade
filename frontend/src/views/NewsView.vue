<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import NewsItem from '../components/NewsItem.vue'

const loading = ref(false)
const pushing = ref(false)
const data = ref<{ updated_at?: string; items: any[]; fetch_stats?: any; filter?: any }>({ items: [] })
const msg = ref('')

const filterHint = computed(() => {
  const f = data.value.filter
  if (!f?.rule) return ''
  const kept = f.kept != null ? `，展示 ${f.kept} 条` : ''
  const note = data.value.fetch_stats?.filter_note ? `（${data.value.fetch_stats.filter_note}）` : ''
  return `筛选规则：${f.rule}${kept}${note}`
})

const sourceHint = computed(() => {
  const st = data.value.fetch_stats
  if (!st?.ok?.length) return ''
  const failed = st.failed?.length ? `；${st.failed.length} 个源暂不可用` : ''
  return `本次成功接入：${st.ok.join('、')}${failed}`
})

async function load(refresh = false) {
  loading.value = true
  msg.value = ''
  try {
    const res = await api.news(refresh)
    data.value = res.data
  } catch (e: any) {
    msg.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function pushFeishu(refreshFirst: boolean) {
  pushing.value = true
  msg.value = ''
  try {
    const res = refreshFirst ? await api.newsPushRefresh() : await api.newsPush()
    msg.value = res.data.pushed_to_feishu
      ? '已推送到飞书'
      : '未配置 FEISHU_WEBHOOK，仅更新本地列表（可在 .env 配置 Webhook）'
    await load(false)
  } finally {
    pushing.value = false
  }
}

onMounted(() => load(false))
</script>

<template>
  <div>
    <h1 class="page-title">经济 / 财经新闻</h1>
    <p class="muted" style="margin-top: -0.5rem; margin-bottom: 1rem">
      多源采集 → 仅保留 <strong>24 小时内</strong>快讯，或<strong>宏观/政策</strong>要闻 → 多方印证与飞书推送
    </p>
    <p v-if="filterHint" class="muted">{{ filterHint }}</p>
    <p v-if="sourceHint" class="muted">{{ sourceHint }}</p>
    <div class="form-row">
      <button class="btn" :disabled="loading" @click="load(true)">{{ loading ? '刷新中…' : '拉取最新' }}</button>
      <button class="btn secondary" :disabled="pushing" @click="pushFeishu(false)">推送飞书（当前列表）</button>
      <button class="btn secondary" :disabled="pushing" @click="pushFeishu(true)">拉取并推送</button>
    </div>
    <p v-if="msg" class="muted">{{ msg }}</p>
    <p v-if="data.updated_at" class="muted">更新时间：{{ data.updated_at.replace('T', ' ').slice(0, 19) }}</p>

    <div class="card" style="margin-top: 1rem">
      <NewsItem v-for="item in data.items" :key="item.id" :item="item" />
      <p v-if="!data.items.length && !loading" class="muted">暂无新闻，请点击「拉取最新」</p>
    </div>
  </div>
</template>

<style scoped>
.btn.secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}
code {
  font-size: 0.85em;
}
</style>
