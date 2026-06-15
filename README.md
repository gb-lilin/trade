# 量化交易系统 V5.1

Vue3 前端 + Python（FastAPI）后端，对应架构图中的 **入口层 / 策略 / 信号 / 执行 / 监控 / 数据 / 风控 / 回测 / core** 模块。

## 目录结构

```
trade/
├── backend/          # Python 后端
│   ├── app/
│   │   ├── core/     # 指标与类型
│   │   ├── data/     # 数据层（腾讯、市场、环境、TuShare）
│   │   ├── signal/   # 情绪、因子、综合分
│   │   ├── strategy/ # screener_v5 + entry
│   │   ├── executor/ # 模拟盘
│   │   ├── monitor/  # 飞书、持仓监控
│   │   ├── risk/     # 校验与仓位公式
│   │   └── backtest/ # 回测引擎
│   └── scripts/      # scan.py、daily.py 等定时任务入口
└── frontend/         # Vue3 + Vite 控制台
```

## 快速开始

### 后端

```powershell
cd d:\Projects\trade\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：http://127.0.0.1:8000/docs

### 前端

```powershell
cd d:\Projects\trade\frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173（已通过 Vite 代理 `/api` 到后端）。

## 配置

在 `backend/.env` 中可选配置：

- `TUSHARE_TOKEN`：TuShare 增强因子与资金流
- `FEISHU_WEBHOOK`：盘后日报推送（`scripts/daily.py`）

## 定时任务示例（Windows 任务计划程序）

| 脚本 | 建议时间 | 说明 |
|------|----------|------|
| `scripts/scan.py` | 9:25 | 盘前双策略选股 |
| `scripts/daily.py` | 15:05 | 盘后汇总 + 飞书推送 |

## 前端页面

- **总览**：环境、情绪、市场宽度、选股 Top10
- **选股扫描**：V5  screener 全市场/自定义列表
- **模拟持仓**：纸面交易与 ATR 仓位风控
- **回测**：单标的权益曲线与指标
- **监控告警**：持仓止盈止损与卖出信号

## 说明

- 行情默认走腾讯接口，失败时自动降级为模拟 K 线，便于本地开发。
- 仓位公式：`最终仓位 = 基础 × 环境 × 信号 × ATR`，与架构图一致。
- 生产环境请补充真实 TuShare Token、完善 `scripts/` 下其余入口（`real_monitor.py` 等）并与任务调度对接。
