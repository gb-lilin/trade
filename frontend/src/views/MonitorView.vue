<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api/client'

const loading = ref(true)
const saving = ref(false)
const msg = ref('')
const data = ref<any>(null)

const globalForm = reactive({
  max_position_pct: 25,
  max_total_exposure: 95,
  stop_loss_pct: 8,
  take_profit_pct: 15,
  sell_score_threshold: 0.42,
  enable_stop_loss: true,
  enable_take_profit: true,
  enable_sell_signal: true,
})

const symbolForms = reactive<Record<string, any>>({})

const alertTypeLabel: Record<string, string> = {
  stop_loss: '止损',
  take_profit: '止盈',
  sell_signal: '卖出信号',
}

async function load() {
  loading.value = true
  msg.value = ''
  try {
    const res = await api.monitorAlerts()
    data.value = res.data
    applySettings(res.data.risk_settings)
    initSymbolForms(res.data.position_rules || [])
  } finally {
    loading.value = false
  }
}

function applySettings(s: any) {
  if (!s) return
  globalForm.max_position_pct = Math.round(s.max_position_pct * 1000) / 10
  globalForm.max_total_exposure = Math.round(s.max_total_exposure * 1000) / 10
  const m = s.default_monitor || {}
  globalForm.stop_loss_pct = m.stop_loss_pct ?? 8
  globalForm.take_profit_pct = m.take_profit_pct ?? 15
  globalForm.sell_score_threshold = m.sell_score_threshold ?? 0.42
  globalForm.enable_stop_loss = m.enable_stop_loss ?? true
  globalForm.enable_take_profit = m.enable_take_profit ?? true
  globalForm.enable_sell_signal = m.enable_sell_signal ?? true
}

function initSymbolForms(rules: any[]) {
  for (const row of rules) {
    const sym = row.symbol
    if (!symbolForms[sym]) {
      symbolForms[sym] = {
        useCustom: row.has_override,
        stop_loss_pct: row.rules.stop_loss_pct,
        take_profit_pct: row.rules.take_profit_pct,
        sell_score_threshold: row.rules.sell_score_threshold,
        enable_stop_loss: row.rules.enable_stop_loss,
        enable_take_profit: row.rules.enable_take_profit,
        enable_sell_signal: row.rules.enable_sell_signal,
      }
    }
  }
}

const positions = computed(() => data.value?.position_rules || [])

async function saveGlobal() {
  saving.value = true
  msg.value = ''
  try {
    await api.updateRiskSettings({
      max_position_pct: globalForm.max_position_pct / 100,
      max_total_exposure: globalForm.max_total_exposure / 100,
      default_monitor: {
        stop_loss_pct: globalForm.stop_loss_pct,
        take_profit_pct: globalForm.take_profit_pct,
        sell_score_threshold: globalForm.sell_score_threshold,
        enable_stop_loss: globalForm.enable_stop_loss,
        enable_take_profit: globalForm.enable_take_profit,
        enable_sell_signal: globalForm.enable_sell_signal,
      },
    })
    msg.value = '全局风控与默认监控阈值已保存'
    await load()
  } catch (e: any) {
    msg.value = e.response?.data?.detail || e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function saveSymbol(symbol: string) {
  const f = symbolForms[symbol]
  if (!f) return
  saving.value = true
  msg.value = ''
  try {
    if (!f.useCustom) {
      await api.clearSymbolRiskSettings(symbol)
      msg.value = `${symbol} 已恢复为全局默认阈值`
    } else {
      await api.setSymbolRiskSettings(symbol, {
        stop_loss_pct: f.stop_loss_pct,
        take_profit_pct: f.take_profit_pct,
        sell_score_threshold: f.sell_score_threshold,
        enable_stop_loss: f.enable_stop_loss,
        enable_take_profit: f.enable_take_profit,
        enable_sell_signal: f.enable_sell_signal,
      })
      msg.value = `${symbol} 专属阈值已保存`
    }
    await load()
  } catch (e: any) {
    msg.value = e.response?.data?.detail || e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h1 class="page-title">监控与风控</h1>
    <p class="muted intro">可为全部持仓设置默认告警阈值；也可为单只股票单独覆盖（止损 / 止盈 / 卖出综合分）。</p>

    <p v-if="loading" class="muted">加载中…</p>
    <template v-else-if="data">
      <div class="grid grid-3">
        <div class="card">
          <h3>情绪指数</h3>
          <div class="metric">{{ data.emotion.emotion }}</div>
        </div>
        <div class="card">
          <h3>单票仓位上限</h3>
          <div class="metric">{{ globalForm.max_position_pct }}%</div>
        </div>
        <div class="card">
          <h3>总仓位上限</h3>
          <div class="metric">{{ globalForm.max_total_exposure }}%</div>
        </div>
      </div>

      <div class="card settings-card">
        <h3>全局风控与监控阈值（默认）</h3>
        <div class="form-grid">
          <label>
            <span>单票仓位上限 (%)</span>
            <input v-model.number="globalForm.max_position_pct" type="number" min="1" max="100" step="1" />
          </label>
          <label>
            <span>总仓位上限 (%)</span>
            <input v-model.number="globalForm.max_total_exposure" type="number" min="1" max="100" step="1" />
          </label>
          <label>
            <span>止损线 (浮亏 %)</span>
            <input v-model.number="globalForm.stop_loss_pct" type="number" min="0" max="80" step="0.5" />
          </label>
          <label>
            <span>止盈线 (浮盈 %)</span>
            <input v-model.number="globalForm.take_profit_pct" type="number" min="0" max="500" step="0.5" />
          </label>
          <label>
            <span>卖出信号 (综合分 ≤)</span>
            <input v-model.number="globalForm.sell_score_threshold" type="number" min="0" max="1" step="0.01" />
          </label>
        </div>
        <div class="checks">
          <label><input v-model="globalForm.enable_stop_loss" type="checkbox" /> 启用止损告警</label>
          <label><input v-model="globalForm.enable_take_profit" type="checkbox" /> 启用止盈告警</label>
          <label><input v-model="globalForm.enable_sell_signal" type="checkbox" /> 启用卖出信号告警</label>
        </div>
        <button class="btn" :disabled="saving" @click="saveGlobal">保存全局设置</button>
      </div>

      <div class="card" style="margin-top: 1rem">
        <h3>按持仓自定义阈值</h3>
        <p v-if="!positions.length" class="muted">当前无持仓，请先在「模拟持仓」建仓后再配置。</p>
        <div v-for="row in positions" :key="row.symbol" class="symbol-block">
          <template v-if="symbolForms[row.symbol]">
          <div class="symbol-head">
            <strong>{{ row.symbol }}</strong>
            <span class="muted">盈亏 {{ row.pnl_pct }}%</span>
            <span v-if="row.score != null" class="muted">综合分 {{ row.score }}</span>
            <label class="custom-toggle">
              <input v-model="symbolForms[row.symbol].useCustom" type="checkbox" />
              使用专属阈值
            </label>
          </div>
          <div v-if="symbolForms[row.symbol]?.useCustom" class="form-grid compact">
            <label>
              <span>止损 %</span>
              <input v-model.number="symbolForms[row.symbol].stop_loss_pct" type="number" step="0.5" />
            </label>
            <label>
              <span>止盈 %</span>
              <input v-model.number="symbolForms[row.symbol].take_profit_pct" type="number" step="0.5" />
            </label>
            <label>
              <span>卖出分 ≤</span>
              <input v-model.number="symbolForms[row.symbol].sell_score_threshold" type="number" step="0.01" />
            </label>
          </div>
          <button
            class="btn btn-sm"
            :disabled="saving"
            @click="saveSymbol(row.symbol)"
          >
            {{ symbolForms[row.symbol]?.useCustom ? '保存该股设置' : '恢复默认' }}
          </button>
          </template>
        </div>
      </div>

      <div class="card" style="margin-top: 1rem">
        <h3>持仓告警</h3>
        <div v-for="(a, i) in data.alerts" :key="i" class="alert">
          {{ a.symbol }} · {{ alertTypeLabel[a.type] || a.type }} · {{ a.reason }}
        </div>
        <p v-if="!data.alerts.length" class="muted">当前无告警</p>
      </div>

      <p v-if="msg" class="msg">{{ msg }}</p>
    </template>
  </div>
</template>

<style scoped>
.intro {
  margin: -0.25rem 0 1rem;
  font-size: 0.9rem;
}
.settings-card h3,
.card h3 {
  margin-top: 0;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem 1rem;
  margin-bottom: 0.75rem;
}
.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--muted);
}
.form-grid input[type='number'] {
  width: 100%;
}
.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
}
.symbol-block {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}
.symbol-block:last-child {
  border-bottom: none;
}
.symbol-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
.custom-toggle {
  margin-left: auto;
  font-size: 0.85rem;
}
.form-grid.compact {
  margin-bottom: 0.5rem;
}
.btn-sm {
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
}
.msg {
  margin-top: 1rem;
  color: var(--accent);
  font-size: 0.9rem;
}
</style>
