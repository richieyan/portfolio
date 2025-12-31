## Plan: 前端联调最小集

目标：在 frontend/ 用 Next.js App Router 搭建最小可跑的界面，连通现有 FastAPI（prices/financials/valuations/analyses/portfolios/holdings/jobs），验证数据流与缓存刷新，满足 PRD 的基础视图（Data Console / 单标分析 / 投资组合面板）与 DeepSeek 报告展示。

### Steps
1. 初始化 Next.js 14 App Router 与 Tailwind/shadcn 基础骨架，配置 env 读取 TUSHARE_TOKEN/DEEPSEEK_API_KEY（frontend/.env.local，参考 README.md）。
2. 建立轻量 API 客户端与类型定义（frontend/lib/api.ts，贴合 backend/app/db/schemas.py 的字段）。
3. 搭建最小页面路由与布局（frontend/app/layout.tsx, app/page.tsx），包含导航到 Data Console、Stock、Portfolio。
4. Data Console: 接入 prices/valuations/financials 列表与 refresh jobs（frontend/app/console/page.tsx），展示 TTL/状态与刷新按钮，基础表格+loading/error。
5. Stock Analysis: 表单提交 analyses POST（probability +可选 DeepSeek report），展示概率、params_json、最近价格简图（frontend/app/stocks/[ts_code]/page.tsx）。
6. Portfolio Dashboard: 读取 portfolios/holdings，展示持仓表与估值分布占位图，提供增删改入口（frontend/app/portfolios/[id]/page.tsx）。

### Decisions
1. 组件基线：选择 B，生成 shadcn/ui 主题与组件基线。
2. DeepSeek 报告：选择 A，首版直接文本区域展示。
3. 图表库：选择 A，采用 Recharts。



