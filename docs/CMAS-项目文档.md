# CMAS — 洁净室空气质量监控系统

> Cleanroom Monitoring & Air-control System  
> 版本: v3 Bright · 最后更新: 2026-08-12

---

## 一、项目概述

CMAS 是一套面向洁净室（医院病房、实验室、制药车间等）的**空气质量实时监控与智能告警平台**。系统通过传感器采集温湿度、CO₂、洁净空气量（CADR）、滤网压力等指标，提供：

- **实时监控大屏** — 仪表盘、楼层平面图、房间详情
- **智能告警** — 阈值判断 + 毛刺过滤 + 冷却机制
- **AI Agent** — 自然语言查询 + 日报自动生成
- **多渠道通知** — 企业微信 / 飞书 / 邮件推送

### 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端框架 | Python FastAPI | 异步 HTTP + WebSocket |
| 数据库 | SQLite + SQLAlchemy 2.0 | 零配置起步，可迁 PostgreSQL/TimescaleDB |
| AI/LLM | DeepSeek API | OpenAI 兼容接口，Function Calling |
| 前端 | 原生 HTML/CSS/JS | Arco Design 风格，无框架依赖 |
| 虚拟环境 | uv | 快速 Python 包管理 |

---

## 二、项目结构

```
前端UI/前端c1.0/
├── backend/                          # Python 后端
│   ├── .env                          # 配置文件（不入 git）
│   ├── .env.example                  # 配置模板
│   ├── requirements.txt              # Python 依赖
│   ├── run.py                        # 启动入口
│   ├── cmas.db                       # SQLite 数据库（自动生成）
│   └── app/
│       ├── main.py                   # FastAPI 入口 + lifespan
│       ├── config.py                 # 统一配置（读 .env）
│       ├── database.py               # SQLAlchemy async engine
│       ├── seed.py                   # 种子数据（15 房间 + 告警规则）
│       ├── simulator.py              # 传感器数据模拟器
│       ├── models/                   # ORM 模型
│       │   ├── room.py               # 房间表
│       │   ├── reading.py            # 传感器读数表（时序）
│       │   ├── alert_rule.py         # 告警规则表
│       │   ├── alert_event.py        # 告警事件表
│       │   └── notification.py       # 通知渠道/订阅/日志表
│       ├── schemas/                  # Pydantic 请求/响应模型
│       ├── routers/                  # API 路由
│       │   ├── rooms.py              # /api/rooms
│       │   ├── readings.py           # /api/readings
│       │   ├── stats.py              # /api/stats
│       │   ├── alerts.py             # /api/alerts
│       │   ├── ws.py                 # WebSocket /ws
│       │   ├── agent.py              # /api/agent (AI)
│       │   └── notifications.py      # /api/channels + /api/subscriptions
│       ├── services/                 # 业务逻辑
│       │   ├── room_service.py       # 房间查询 + 快照
│       │   ├── reading_service.py    # 读数查询 + 时序
│       │   ├── stats_service.py      # 统计计算 + 状态判定
│       │   ├── alert_engine.py       # 告警引擎（阈值+毛刺+冷却）
│       │   └── notification_dispatcher.py  # 通知分发
│       ├── agent/                    # AI Agent 模块
│       │   ├── llm_client.py         # DeepSeek API 封装
│       │   ├── tools.py              # 5 个工具函数
│       │   ├── prompts.py            # System Prompt
│       │   └── report.py             # 日报生成
│       └── channels/                 # 通知渠道
│           ├── base.py               # 抽象基类
│           ├── wecom_bot.py          # 企业微信机器人
│           ├── feishu_bot.py         # 飞书机器人
│           └── email_channel.py      # 邮件 SMTP
│
├── frontend/                         # 前端页面
│   ├── index.html                    # 监控总览（仪表盘）
│   ├── floor-plan.html               # 楼层平面图
│   ├── room-detail.html              # 房间详情
│   ├── alerts.html                   # 告警中心
│   ├── admin.html                    # Agent 管理后台
│   ├── css/                          # 样式
│   │   ├── tokens.css                # 设计 Token（颜色/间距/圆角）
│   │   ├── core.css                  # 核心布局 + 重置
│   │   ├── components.css            # 组件样式
│   │   └── pages.css                 # 页面样式
│   └── js/                           # 脚本
│       ├── main.js                   # 基础（菜单/动画）
│       ├── data.js                   # 静态 Mock 数据（fallback）
│       ├── api.js                    # API 客户端 + WebSocket
│       ├── charts.js                 # 图表渲染（SVG）
│       ├── orbital.js                # 轨道球可视化
│       ├── table-filter.js           # 表格搜索/筛选
│       ├── floor-plan.js             # 楼层平面图 SVG
│       ├── flip-cards.js             # 翻转卡片
│       ├── dashboard-bind.js         # 仪表盘 API 绑定
│       ├── room-detail-bind.js       # 房间详情 API 绑定
│       ├── floor-plan-bind.js        # 楼层图 API 绑定
│       └── alerts-bind.js            # 告警看板 API 绑定
│
└── docs/                             # 项目文档
    └── CMAS-项目文档.md
```

---

## 三、核心业务流程

### 3.1 数据采集 → 存储

```
传感器（或模拟器）
    │  每 5 秒生成 15 房间 × 5 指标 = 75 条读数
    ▼
POST /api/readings/batch
    │  写入 sensor_readings 表
    ▼
WebSocket /ws 广播房间快照 → 前端实时刷新
```

**模拟器行为**（`simulator.py`）：
- 基于基准值 + 高斯噪声生成正常读数
- 随机选取 2-4 个房间产生异常值（超出阈值 5-30%）
- 异常持续 3-10 分钟后自动恢复
- 生产环境关闭模拟器，接入真实 MQTT

### 3.2 告警判定流程

```
传感器读数到达
    │
    ▼
告警引擎 evaluate_reading()
    │
    ├── 值在正常范围？
    │   ├── 是 → 清除异常状态，自动恢复旧告警
    │   └── 否 → 记录首次异常时间
    │
    ├── 异常持续 ≥ duration_seconds（默认 30s）？
    │   └── 否 → 不触发（毛刺过滤，如开门瞬间）
    │
    ├── 距上次告警 ≥ cooldown_seconds（默认 300s）？
    │   └── 否 → 冷却期，不重复推送
    │
    └── 是 → 🔥 创建 AlertEvent，触发通知分发
```

### 3.3 通知分发流程

```
告警触发 / 日报到点
    │
    ▼
匹配订阅规则（AlertSubscription）
    │  条件: enabled=true + event_types 包含当前事件类型
    │       + room_id 在白名单（或空=全部）
    │       + severity ≥ min_severity
    │
    ├── 找到匹配订阅 → 获取关联的 Channel 列表
    │       │
    │       ├── 企业微信 → POST webhook (Markdown)
    │       ├── 飞书 → POST webhook (卡片消息)
    │       └── 邮件 → SMTP (HTML)
    │       │
    │       └── 写入 notification_logs
    │
    └── 无匹配 → 静默（不推送）
```

### 3.4 AI Agent 工作流程

```
用户输入（自然语言）
    │  "现在有哪些房间异常？"
    ▼
POST /api/agent/chat
    │
    ▼
DeepSeek API（第一次调用）
    │  System Prompt + 用户消息 + 5 个 Tool 定义
    │  返回: tool_calls → query_anomaly_rooms
    ▼
执行工具函数 query_anomaly_rooms()
    │  查询数据库 → 返回 JSON
    ▼
DeepSeek API（第二次调用）
    │  工具返回的 JSON + 原对话
    │  返回: 自然语言回答
    ▼
返回前端渲染
    "当前有 4 个房间异常: Department 201 温度 19.0°C..."
```

**5 个工具函数**（`tools.py`）：

| 工具 | 功能 | 数据来源 |
|---|---|---|
| `query_rooms` | 所有房间实时数据 | sensor_readings 最新值 |
| `query_stats` | 仪表盘统计 | 状态计算 |
| `query_alerts` | 告警历史 | alert_events 表 |
| `query_room_trend` | 单房间时序趋势 | sensor_readings 时序查询 |
| `query_anomaly_rooms` | 异常房间列表 | 当前超标房间 |

### 3.5 日报生成流程

```
触发方式:
  ① 每天 08:00 自动（asyncio sleep 循环）
  ② POST /api/agent/report?send=true（手动 + 推送）
  ③ POST /api/agent/report（手动预览）

生成步骤:
  1. 调用工具函数采集实时数据
  2. 拼装 Prompt（统计 + 异常 + 告警历史）
  3. DeepSeek 生成 Markdown 日报
  4. 若 send=true → 匹配订阅 → 分发到渠道
```

---

## 四、数据库模型

### ER 图

```
Room (房间)                    AlertRule (告警规则)
  │  1:N                        │  room_id 可空=全局
  ├── SensorReading (时序)      │  metric + threshold
  ├── AlertEvent (告警事件)     │  duration + cooldown
  └── (无直接关系)               │
                                 │
NotificationChannel (渠道)       AlertSubscription (订阅)
  │  M:N                        │  M:N → channels
  └── SubscriptionChannel       │  room_ids + severity + event_types
                                 │
NotificationLog (推送日志)       │
  └── sub_id + ch_id + result   │
```

### 核心表

| 表 | 行数（示例） | 说明 |
|---|---|---|
| `rooms` | 15 | 房间基础信息 |
| `sensor_readings` | ~50,000+ | 时序数据，每 5 秒 75 条 |
| `alert_rules` | 5 | 全局默认规则（5 项指标各一） |
| `alert_events` | 动态 | 触发的告警事件 |
| `notification_channels` | 1-5 | 推送渠道配置 |
| `alert_subscriptions` | 1-5 | 订阅规则 |
| `notification_logs` | 递增 | 每次推送的记录 |

---

## 五、API 参考

### 房间
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/rooms` | 房间列表（?search=&anomaly=） |
| GET | `/api/rooms/{id}` | 房间详情 |
| GET | `/api/rooms/{id}/metrics` | 所有指标 + 阈值状态 |
| GET | `/api/rooms/{id}/readings/{metric}` | 时序数据（?hours=12&points=12） |

### 读数
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/readings` | 单条写入 |
| POST | `/api/readings/batch` | 批量写入 |

### 统计
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/stats/overview` | 仪表盘统计卡片 |
| GET | `/api/stats/alerts` | 告警看板数据 |

### 告警
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/alerts` | 告警事件列表 |
| GET | `/api/alerts/rules` | 告警规则列表 |
| POST | `/api/alerts/rules` | 创建告警规则 |

### Agent
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/agent/chat` | AI 自然语言查询 |
| POST | `/api/agent/report` | 生成日报（?send=true 推送） |

### 通知
| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/api/channels` | 渠道 CRUD |
| POST | `/api/channels/{id}/test` | 测试渠道连通性 |
| DELETE | `/api/channels/{id}` | 删除渠道 |
| GET/POST | `/api/subscriptions` | 订阅 CRUD |
| DELETE | `/api/subscriptions/{id}` | 删除订阅 |

### 实时
| 方法 | 路径 | 说明 |
|---|---|---|
| WS | `/ws` | WebSocket，每秒推送房间快照 + 统计 |

### 其他
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/seed` | 手动重新初始化种子数据 |

---

## 六、部署与运行

### 环境要求

- Python 3.12+
- uv（Python 包管理器）

### 快速启动

```powershell
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（首次）
uv venv

# 3. 安装依赖
uv pip install -r requirements.txt

# 4. 配置 .env
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（可选，用于 AI Agent）

# 5. 启动
.venv\Scripts\python run.py
```

### 访问地址

| 页面 | URL |
|---|---|
| 监控总览 | http://localhost:8000/ |
| 楼层平面图 | http://localhost:8000/floor-plan.html |
| 房间详情 | http://localhost:8000/room-detail.html?id=203 |
| 告警中心 | http://localhost:8000/alerts.html |
| Agent 管理 | http://localhost:8000/admin.html |
| API 文档 | http://localhost:8000/docs |

### 配置参考（.env）

```ini
# 数据库
DATABASE_URL=sqlite+aiosqlite:///cmas.db

# 模拟器（生产环境设为 false）
SIMULATOR_ENABLED=true
SIMULATOR_INTERVAL_SECONDS=5

# DeepSeek LLM（Agent 对话 + 日报生成）
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 日报推送时间
REPORT_SCHEDULE_HOUR=8
```

---

## 七、前端页面说明

### 监控总览 `index.html`
- 统计卡片：优良区域 / 需关注区域 / 非自动通风（实时数字）
- 轨道球可视化：15 个房间节点，颜色表示状态（绿/橙/红）
- 房间列表表格：支持搜索 + 按异常类型筛选
- WebSocket 每 5 秒自动更新

### 楼层平面图 `floor-plan.html`
- SVG 3 行 × 5 列 = 15 个房间
- 状态圆点（绿 OK / 橙 Warn / 红异常+波纹动画）
- 点击房间右侧弹出实时指标面板

### 房间详情 `room-detail.html`
- Narrative Hero 区域（房间名 + 最大异常值）
- 4 张翻转卡片（温湿度/CO₂/CADR），正面当前值，背面 12 点趋势图
- 设备状态表（5 项指标 + 滤网压力）
- URL 参数 `?id=203` 指定房间

### 告警中心 `alerts.html`
- 看板三列：异常提醒 / 非自动通风 / 正常区域
- 异常卡片显示房间、指标、超标幅度、时间

### Agent 管理 `admin.html`
- AI 对话：自然语言查询空气质量
- 日报：预览 / 生成并推送
- 渠道配置：企业微信 / 飞书 / 邮件
- 订阅配置：告警/日报 → 渠道绑定

---

## 八、扩展规划

| 优先级 | 功能 | 说明 |
|---|---|---|
| P1 | MQTT 真实传感器接入 | 替换模拟器，对接硬件 |
| P1 | 用户认证 | JWT 登录 + 权限控制 |
| P2 | 数据库迁移 | SQLite → PostgreSQL + TimescaleDB |
| P2 | 历史数据看板 | 周/月趋势 + 同比环比 |
| P2 | Docker 部署 | Dockerfile + docker-compose |
| P3 | 根因分析 Agent | 多指标关联分析 |
| P3 | 趋势预判 | 基于时序外推提前预警 |

---

## 九、项目简历

> 以下为「项目经历」章节，按主流招聘平台（BOSS 直聘 / 拉勾）简历写法整理，突出**亮点**与**难点**，可直接摘录到个人简历的「项目经历」栏。

### 项目描述

**CMAS — 洁净室空气质量监控系统**（独立全栈开发，2026.06 — 至今）

面向医院病房、实验室、制药车间等洁净室的空气质量实时监控与智能告警平台。以 5 秒为周期采集 15 个房间、5 项环境指标（温湿度 / CO₂ / CADR / 滤网压力），通过告警引擎实时识别异常并多渠道推送，接入 DeepSeek 大模型实现自然语言查询与日报自动生成。

- 技术栈：Python / FastAPI / SQLAlchemy 2.0 / SQLite / DeepSeek API / WebSocket / 原生 HTML/CSS/JS

### 项目亮点

- **AI Agent 自然语言交互**：基于 DeepSeek Function Calling 实现「模型决策 → 工具执行 → 自然语言回复」两轮调用链，封装 5 个数据查询工具，用户可用「现在有哪些房间异常？」直接对话查询，并支持每日 08:00 自动生成 Markdown 日报。
- **告警引擎三级判定模型**：阈值判断 + 毛刺过滤 + 冷却机制，有效过滤瞬时波动与重复推送，显著降低误报率。
- **秒级实时数据流**：每 5 秒 75 条读数批量写入，WebSocket 每秒广播房间快照，大屏实时刷新无卡顿。
- **可扩展通知体系**：抽象 Channel 基类统一企业微信 / 飞书 / 邮件三渠道接口，订阅规则支持按事件类型、房间、严重级别灵活匹配。
- **零依赖前端可视化**：原生 JS + SVG 手写轨道球、楼层平面图、翻转卡片、时序趋势图，无框架依赖，Arco Design 风格统一。

### 项目难点与解决方案

| 难点 | 问题描述 | 解决方案 |
|---|---|---|
| **误报控制** | 开门等瞬时动作使读数短暂超标，直接告警会淹没真实告警 | 三级判定：异常持续 ≥ 30s 才触发（毛刺过滤）+ 同指标 300s 冷却去重 |
| **LLM 输出不可控** | 大模型自由文本无法直接对接数据库查询，结果不稳定 | 用 Function Calling 约束为结构化工具调用，两轮调用链返回受控 JSON |
| **实时性与数据量矛盾** | 每 5 秒 75 条时序数据，前端高频刷新压力大 | WebSocket 只广播「快照」而非原始流 + 时序查询降采样（points 参数） |
| **多渠道格式不统一** | 企业微信（Markdown）/ 飞书（卡片）/ 邮件（HTML）格式各异 | 抽象 Channel 基类统一接口，订阅规则路由到具体渠道实现 |
| **前端无框架可视化** | 无图表库支撑，需要手写实时可视化组件 | 原生 SVG 封装轨道球 / 楼层图 / 趋势图，状态色 + 动画驱动实时刷新 |

### 项目成果

- 覆盖 15 房间 × 5 指标实时监控，告警支持毛刺过滤 + 冷却去重。
- 打通企业微信 / 飞书 / 邮件三条通知链路，异常秒级触达。
- 前端 5 个页面纯原生实现，无框架依赖。
- 独立完成全栈，具备需求分析 → 架构设计 → 落地交付的完整能力。
