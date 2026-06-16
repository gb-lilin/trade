<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  item: {
    title: string
    summary?: string
    ai_brief?: string
    source?: string
    sources?: string[]
    consensus?: number
    is_recent?: boolean
    macro_policy?: boolean
    published_at?: string
    category?: string
    sentiment?: string
    url?: string
    pushed_at?: string | null
  }
  compact?: boolean
}>()

const catLabel: Record<string, string> = {
  macro: '宏观',
  policy: '政策',
  market: '市场',
  industry: '行业',
}

const timeText = computed(() => {
  const t = props.item.published_at
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
})
</script>

<template>
  <article class="news-item" :class="{ compact }">
    <div class="news-meta">
      <span class="tag cat">{{ catLabel[item.category || ''] || '资讯' }}</span>
      <span class="tag" :class="item.sentiment">{{ item.sentiment === 'positive' ? '偏多' : item.sentiment === 'negative' ? '偏空' : '中性' }}</span>
      <span v-if="item.pushed_at" class="tag pushed">已推送</span>
      <span v-if="item.is_recent" class="tag recent">24h 内</span>
      <span v-else-if="item.macro_policy" class="tag policy">宏观政策</span>
      <span v-if="(item.consensus || 0) >= 2" class="tag consensus">多方 {{ item.consensus }} 源</span>
      <span class="muted">{{ item.source }} · {{ timeText }}</span>
    </div>
    <h4 class="news-title">
      <a v-if="item.url" :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
      <span v-else>{{ item.title }}</span>
    </h4>
    <p v-if="!compact && (item.ai_brief || item.summary)" class="news-brief">
      {{ item.ai_brief || item.summary }}
    </p>
  </article>
</template>

<style scoped>
.news-item {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}
.news-item:last-child {
  border-bottom: none;
}
.news-item.compact .news-brief {
  display: none;
}
.news-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
  align-items: center;
  margin-bottom: 0.35rem;
  font-size: 0.75rem;
}
.tag {
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
}
.tag.cat {
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
}
.tag.positive {
  background: rgba(34, 197, 94, 0.15);
  color: #86efac;
}
.tag.negative {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}
.tag.neutral {
  background: rgba(148, 163, 184, 0.15);
  color: #cbd5e1;
}
.tag.pushed {
  background: rgba(234, 179, 8, 0.15);
  color: #fde047;
}
.tag.consensus {
  background: rgba(20, 184, 166, 0.18);
  color: #5eead4;
}
.tag.recent {
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
}
.tag.policy {
  background: rgba(168, 85, 247, 0.18);
  color: #d8b4fe;
}
.news-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.4;
}
.news-title a {
  color: var(--text);
  text-decoration: none;
}
.news-title a:hover {
  color: var(--accent);
}
.news-brief {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  color: var(--muted);
  line-height: 1.5;
}
</style>
