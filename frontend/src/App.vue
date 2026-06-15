<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

const links = [
  { to: '/', label: '总览' },
  { to: '/scan', label: '选股扫描' },
  { to: '/etf', label: 'ETF 推荐' },
  { to: '/portfolio', label: '模拟持仓' },
  { to: '/backtest', label: '回测' },
  { to: '/news', label: '财经新闻' },
  { to: '/monitor', label: '监控告警' },
]
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">QTS</span>
        <div>
          <div class="title">量化交易 V5.1</div>
          <div class="sub">双策略引擎</div>
        </div>
      </div>
      <nav>
        <RouterLink v-for="l in links" :key="l.to" :to="l.to">{{ l.label }}</RouterLink>
      </nav>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>
