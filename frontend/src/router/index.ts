import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import ScanView from '../views/ScanView.vue'
import PortfolioView from '../views/PortfolioView.vue'
import BacktestView from '../views/BacktestView.vue'
import MonitorView from '../views/MonitorView.vue'
import NewsView from '../views/NewsView.vue'
import EtfView from '../views/EtfView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard },
    { path: '/scan', name: 'scan', component: ScanView },
    { path: '/etf', name: 'etf', component: EtfView },
    { path: '/portfolio', name: 'portfolio', component: PortfolioView },
    { path: '/backtest', name: 'backtest', component: BacktestView },
    { path: '/monitor', name: 'monitor', component: MonitorView },
    { path: '/news', name: 'news', component: NewsView },
  ],
})

export default router
