<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import NewsItem from '../components/NewsItem.vue'

const loading = ref(false)
const pushing = ref(false)
const data = ref<{ updated_at?: string; items: any[] }>({ items: [] })
const msg = ref('')

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
      对应架构 <code>ai_news_push</code>：RSS 采集 → AI/规则解读 → 页面展示与飞书推送
    </p>
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
