
## 三、项目经历

智能客服多 Agent 系统
技术栈：　LangGraph +FastAPI ·+Spring Boot +Uniapp
基于真实外卖业务构建的端到端 AI 客服系统，覆盖完整链路，实现让 LLM 真正操作业务系统（查单、催单、取消、再来一单、菜单推荐、合规审查）。
多 Agent 协作架构：基于 LangGraph StateGraph 实现 Supervisor 编排模式，将任务分解给 4 个专业化 Agent（Supervisor / KnowledgeRAG / TicketHandler / ComplianceChecker），LLM 动态分析意图并条件路由，最终拼装回复。
知识库 RAG 问答：Query Rewrite 将口语化查询改写为检索词 → FAISS 向量检索（512+128 重叠分块、Top-3 召回）→ LLM 生成回答，覆盖菜单/菜品推荐、退款政策、下单流程等 FAQ；FAISS 不可用时自动降级为关键词匹配。
自研 MCP 工具协议层：参照 Anthropic MCP 规范，用装饰器模式实现工具注册/发现/调用框架，映射 9 个 MCP Tool → 15+ 个 Spring Boot 业务 API，让 LLM 从「回答问题」升级为「执行真实业务操作」。
三层记忆架构 + 降级：Working Memory（进程内存）/ Short-Term（Redis，30min）/ Long-Term（FAISS 磁盘持久化），Redis、FAISS 不可用时自动回退，降低运维复杂度。
合规审查双阶段流水线：规则引擎（正则+关键词，毫秒级）先快筛，仅命中风险才触发 LLM 深度审查，90% 正常回复走快路径，兼顾安全与 token 成本。



---

## 四、核心亮点（面试速览）

1. **不是 ChatBot，是 Agent 系统**——Supervisor 编排 + 独立工具集 + 合规兜底，架构可讲深度。
2. **LLM 驱动真实业务**——自研 MCP 协议桥接 LLM 与 Spring Boot，权限隔离在工具层兜底。
3. **跨语言零侵入鉴权**——JWT 透明穿透，认证归 Java、推理归 Python。
4. **自愈式记忆与降级**——每层存储都有 fallback，稳定性和可运维性见功力。
5. **工程化可观测**——装饰器一行接入 OpenTelemetry，全链路 Span 追踪定位多 Agent 瓶颈。
6. **人工接管闭环（HITL）**——AI 兜不住自动升级人工，状态机管理 + WebSocket 双端实时通道，断线消息不丢，体现真实客服业务闭环。
7. **聊天记录持久化**——对话写穿透 MySQL，Redis 过期后回读回填，热数据缓存、冷数据落库，故障自动降级进程内存。

---



# 苍穹外卖 · 智能客服多 Agent 系统 — 技术架构文档

> 生成日期：2026-07-07  
> 适用于：苍穹食堂（sky-take-out）外卖系统 + Python 多 Agent 智能客服

## 一、系统总览

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           苍穹外卖 完整系统                                   │
├───────────────┬───────────────┬───────────────────┬──────────────────────────┤
│  Spring Boot  │  Python       │  Uniapp H5        │  Vue Admin               │
│  外卖后端      │  AI客服 Agent  │  消费者端           │  管理后台                 │
│  :8080        │  :8000        │  :8082            │  :8088                   │
└───────────────┴───────────────┴───────────────────┴──────────────────────────┘
```

四个服务通过 HTTP 协议通信，JWT token 贯穿认证链。

---

## 二、架构分层

### 2.1 请求链路（消费者聊天场景）

```
  用户点击 💬 AI客服
      │
      ├─► Uniapp H5 (chat.vue)
      │      │ 调用 chatApi.js → POST /api/chat
      │      │ Header: authentication = JWT
      │      │
      │      ▼
      ├─► FastAPI (api/main.py :8000)
      │      │ 路由 /api/chat → chat()
      │      │ 鉴权: token → BackendClient → Spring Boot
      │      │
      │      ▼
      ├─► Supervisor Graph (LangGraph StateGraph)
      │      │
      │      ├─ ① supervisor_route ── LLM 分析意图
      │      │       │
      │      │       ├── knowledge_rag ── 知识库问答
      │      │       ├── ticket_handler ── 订单查询/操作
      │      │       └── compliance_checker ── 敏感词检测
      │      │
      │      ├─ ② sub-agent process ── 执行业务逻辑
      │      │
      │      ├─ ③ compliance_check ── 合规审查
      │      │
      │      └─ ④ synthesize ── 拼装最终回复
      │
      ▼
  用户看到回复
```

### 2.2 请求链路（管理后台场景）

管理员通过 Swagger UI 或管理后台直接调用 `/api/chat`，token 通过 `token` header 传入，享有全部管理权限。

---

## 三、核心模块详解

### 3.1 Supervisor 编排引擎

**文件**: `agents/supervisor.py`

| 组件 | 功能 |
|------|------|
| `AgentState` | LangGraph 全局状态：messages, intent, sub_results, auth_token 等 |
| `SupervisorNode.route_decision()` | 用 LLM 分析用户意图，输出路由目标 |
| `SupervisorNode.synthesize_response()` | 合并子 Agent 结果，生成最终回复 |
| `create_supervisor_graph()` | 构建完整的 StateGraph，注册所有节点和边 |

**路由规则**（由 LLM 驱动，Prompt 指导）：

| 条件 | 路由目标 |
|------|---------|
| 查询自己的订单 | `ticket_handler` |
| 菜单/菜品/推荐/FAQ | `knowledge_rag` |
| 取消/催单/再来一单 | `ticket_handler` |
| 敏感/违规内容 | `compliance_checker` |

**图结构**：
```
SET_START → supervisor_route
                ├→ knowledge_rag ──┐
                ├→ ticket_handler ─┤
                └→ compliance_check ┤
                        ▲          │
                        └──────────┘
                            │
                    synthesize → END
```

---

### 3.2 IntentRouter — 意图识别（备用）

**文件**: `agents/intent_router.py`

- 五级意图分类：consultation / complaint / transaction / account / compliance
- JSON 结构化输出，含置信度和实体提取
- 当前为备用方案，Supervisor 内置了 LLM 路由

---

### 3.3 KnowledgeRAG — 知识库问答

**文件**: `agents/knowledge_rag.py`

| 步骤 | 实现 |
|------|------|
| Query 改写 | LLM 将口语化问题转为检索词 |
| 向量检索 | FAISS 索引 + hash 模拟嵌入（生产替代：OpenAI Embedding） |
| 回答生成 | LLM 基于 Top-3 检索文档生成回答 |

**预置知识**（在 `api/main.py` lifespan 中注入）：
- 菜单分类、退款政策、下单流程、店铺信息

---

### 3.4 TicketHandler — 工单/订单处理

**文件**: `agents/ticket_handler.py`

| 方法 | 功能 |
|------|------|
| `analyze_request()` | LLM 解析用户消息 → 提取 action/order_id/phone/reason |
| `execute_action()` | 根据 action 调用 MCP 工具 → BackendClient → Spring Boot API |

**管理员工具** (5个)：`order_query`, `order_action`, `menu_query`, `business_data`, `shop_status`

**消费者工具** (4个)：`user_order_query`, `user_order_action`, `user_menu_query`, `user_shop_info`

**权限隔离**：通过 `auth_type` 字段区分 `admin` / `user`，消费者调用 `user_*` 工具集。

---

### 3.5 ComplianceChecker — 合规审查

**文件**: `agents/compliance_checker.py`

两阶段审查：

| 阶段 | 方式 | 检测内容 |
|------|------|---------|
| 规则引擎 | 正则 + 关键词 | 虚假宣传用语、PII 脱敏 |
| LLM 深度审查 | LLM 判断 | 越权承诺、误导性陈述、歧视等内容 |

PII 脱敏：手机号 `13812345678` → `138****5678`

---

### 3.6 MCP 工具协议层

**文件**: `mcp/mcp_server.py`, `mcp/backend_tools.py`, `mcp/user_backend_tools.py`, `mcp/backend_client.py`

| 文件 | 职责 |
|------|------|
| `mcp_server.py` | MCP 工具注册/发现/调用框架（JSON-RPC 2.0） |
| `backend_tools.py` | 注册 4 个管理员工具 → Spring Boot `/admin/*` API |
| `user_backend_tools.py` | 注册 4 个消费者工具 → Spring Boot `/user/*` API |
| `backend_client.py` | 统一 HTTP 客户端：Result<T> 解包、JWT 透传、错误处理 |

**Spring Boot API 映射**：

| MCP 工具 | HTTP Method | Spring Boot 端点 |
|----------|-------------|------------------|
| order_query | GET | `/admin/order/conditionSearch`, `/admin/order/details/{id}` |
| order_action | PUT | `/admin/order/confirm`, `/admin/order/rejection`, `/admin/order/cancel` 等 |
| menu_query | GET | `/admin/dish/list`, `/admin/setmeal/page`, `/admin/category/list` |
| business_data | GET | `/admin/workspace/businessData`, `/admin/report/top10` |
| shop_status | GET/PUT | `/admin/shop/status`, `/admin/shop/{status}` |
| user_order_query | GET | `/user/order/historyOrders`, `/user/order/orderDetail/{id}` |
| user_order_action | PUT/POST | `/user/order/cancel/{id}`, `/user/order/reminder/{id}`, `/user/order/repetition/{id}` |
| user_menu_query | GET | `/user/dish/list`, `/user/category/list`, `/user/setmeal/list` |
| user_shop_info | GET | `/user/shop/status`, `/user/shop/getMerchantInfo` |

---

### 3.7 记忆系统（分层 + 持久化归档）

| 层级 | 文件 | 存储 | TTL | 用途 |
|------|------|------|-----|------|
| Working Memory | `memory/working_memory.py` | 进程内存 | 单次请求 | Agent 中间推理状态 |
| Short-Term Memory | `memory/short_term.py` | Redis（回退内存） | 30min | 对话上下文热缓存 |
| 持久化归档 | `memory/mysql_store.py` | MySQL | 持久 | 聊天记录落盘，Redis 过期后回读回填 |
| Long-Term Memory | `memory/long_term.py` | FAISS 磁盘 | 持久 | 知识库文档索引（静态知识，非用户历史） |

---

### 3.8 可观测性

**文件**: `tracing/otel_config.py`

- OpenTelemetry 集成，每个 Agent 方法通过 `@trace_agent_call` 装饰器自动创建 Span
- 支持导出到 Jaeger (OTLP gRPC :4317) 或控制台
- `AgentMetrics` 类收集调用次数、平均耗时、错误率

---

## 四、数据流与认证

### 4.1 JWT 认证链

```
                     ┌─────────────┐
  H5 消费者           │  JWT 认证    │              ┌──────────────┐
  ─────────────────►│  token      │─────────────►│ Spring Boot  │
                     │  header     │   /user/*    │ :8080        │
                     └─────────────┘              └──────────────┘

                     ┌─────────────┐
 管理后台              │  JWT 认证    │              ┌──────────────┐
  ─────────────────►│  token      │─────────────►│ Spring Boot  │
                     │  header     │   /admin/*   │ :8080        │
                     └─────────────┘              └──────────────┘
```

1. H5 前端在 `App.vue` 启动时调用 `POST /user/user/login` 获取 JWT token
2. 用户聊天时，token 通过 `authentication` header 传到 FastAPI
3. FastAPI 将 token 透传给 Spring Boot 后端 API（`token` / `authentication` header）

### 4.2 LLM Provider

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key | - |
| `OPENAI_API_KEY` | OpenAI API Key（备选） | - |
| `DASHSCOPE_BASE_URL` | LLM API 地址 | `dashscope.aliyuncs.com/compatible-mode/v1` |
| `OPENAI_BASE_URL` | OpenAI 地址（备选） | - |
| `MODEL_NAME` | 模型名称 | `qwen3.7-plus` |

支持任意 OpenAI 兼容接口（DeepSeek、豆包、硅基流动等），只需修改环境变量。

---

## 五、部署拓扑

```
docker-compose.yml 定义的服务：

  ┌──────────┐   ┌──────────────┐   ┌───────────┐   ┌────────┐
  │  Redis   │   │ python-agent │   │ java-agent│   │ Jaeger │
  │  :6379   │   │    :8000     │   │   :8080   │   │ :16686 │
  └──────────┘   └──────────────┘   └───────────┘   └────────┘
       │                │                  │              │
       └────────────────┴──────────────────┴──────────────┘
                    共享网络 (bridge)

前端项目独立运行（非 Docker）：
  - 消费者 H5: npm run serve → :8082
  - 管理后台:  npm run serve → :8088
```

---

## 六、关键技术知识点

### 6.1 LangGraph StateGraph

- **StateGraph**: 有向图编排框架，每个节点是纯函数 `state → state`
- **Checkpointing**: 通过 `MemorySaver` 支持对话中断与恢复
- **条件路由**: `add_conditional_edges` 根据 state 中的 intent 动态选择下一个节点
- **状态定义**: `AgentState(TypedDict)`，通过 `Annotated[list, add_messages]` 实现消息累加

### 6.2 MCP (Model Context Protocol)

- **工具注册**: `@server.register(name, description, input_schema)` 声明式注册
- **工具发现**: Agent 通过 `GET /api/tools` 查询可用工具
- **工具调用**: Agent 通过 `POST /api/tools/call` 调用，JSON-RPC 2.0 协议
- **标准化**: 遵循 Anthropic MCP 规范，支持 inputSchema 声明和标准错误码

### 6.3 RAG (Retrieval-Augmented Generation)

- **Query Rewrite**: 口语化查询 → 检索优化查询（提高召回率）
- **向量检索**: FAISS IndexFlatIP（内积相似度）
- **分块策略**: 512 token 固定窗口 + 128 token 重叠（防止语义断裂）
- **回退机制**: FAISS 不可用时降级为关键词匹配

### 6.4 合规审查

- **规则快检**: 正则 + 关键词，零延迟
- **LLM 深度检**: 仅触发于规则检出的风险项，节省成本
- **PII 脱敏**: 手机号/身份证/银行卡/邮箱 → 部分掩码

### 6.5 分层记忆架构（三层 + MySQL 持久化归档）

| 记忆层 | 类比 | 实现 |
|--------|------|------|
| Working Memory | CPU 寄存器 | 进程内 dict，零延迟 |
| Short-Term Memory | RAM | Redis List，TTL 30min，含进程内 dict 回退 |
| 持久化归档 | 硬盘 | MySQL 写穿透落盘 + 回读回填（存用户聊天历史） |
| Long-Term Memory | 外置知识库 | FAISS 向量索引，磁盘持久化（存知识库文档） |

> 注意：Long-Term Memory（FAISS）存**知识库文档索引**；MySQL 存**用户聊天历史**。两者用途不同，面试时务必区分。

### 6.6 权限模型

| 用户类型 | 标识 | 可用工具前缀 | 权限范围 |
|---------|------|-------------|---------|
| admin | `auth_type="admin"` | 无前缀 | 全部订单/菜单/营业数据 |
| user | `auth_type="user"` | `user_*` | 仅自己的订单/公共菜单/店铺信息 |

### 6.7 前端集成要点

- **Uniapp H5** 作为消费者入口，Vue 组件化架构
- **Vuex** 管理全局状态：token、shopInfo、购物车
- **AI客服入口**：首页右下角悬浮按钮 💬 → `pages/chat/chat`
- **快速操作**：预设 4 个快捷问题按钮（查订单/美食推荐/退款咨询/营业时间）
- **API 调用**：`chatApi.js` → `POST /api/chat`，JWT 通过 `authentication` header 透传

---

## 七、常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| AI客服返回 500 | LLM API Key 欠费或无效 | 检查 `.env` 中 API Key，更换可用 key |
| 订单查询失败 | Spring Boot 未启动或 JWT 过期 | 确认 :8080 运行，重新登录获取 token |
| 知识库回答空洞 | 知识文档导入不完整 | 在 `api/main.py` lifespan 中补充 `long_term_memory.add_document()` |
| Redis 连接失败 | Redis 未启动 | 不影响使用，系统自动回退到内存存储 |
| chat 接口 503 | Supervisor graph 未初始化 | 等待 lifespan 启动完成 |

---

## 八、技术栈一览

| 层级 | 技术 | 说明 |
|------|------|------|
| **LLM 推理** | LangChain + LangGraph, OpenAI-compatible API | Supervisor 编排 + 3 个专用子 Agent |
| **Agent 后端** | Python 3.12, FastAPI, Uvicorn | 异步 REST API + SSE 流式响应 |
| **工具协议** | 自研 MCP Server (JSON-RPC 2.0) | 9 个 MCP Tool → 15+ Spring Boot API 映射 |
| **向量检索** | FAISS, NumPy | 知识库 RAG，含关键词回退 |
| **记忆系统** | Redis (短期), FAISS 磁盘 (长期), 进程内存 (工作) | 三层架构，Redis 不可用时自动降级 |
| **可观测性** | OpenTelemetry, Jaeger | 全链路 Span 追踪，Agent 级性能指标 |
| **外卖后端** | Java 8, Spring Boot 2.7, MyBatis, Druid, Knife4j | RESTful API，JWT 认证 |
| **消费者前端** | Uniapp (Vue 2), Vuex, SCSS | 跨平台 H5 + 微信小程序 |
| **管理后台** | Vue 2, TypeScript, Element UI, ECharts | 订单管理、数据看板 |
| **基础设施** | Docker Compose, Maven, npm, Redis | 一键部署，服务编排 |

---

## 九、简历亮点与难点

### 9.1 核心亮点

#### ① 多 Agent 协作架构，非简单 ChatBot

传统客服机器人是"一个问题 → LLM → 回答"的单体模式。本系统采用 **Supervisor 编排模式**，将任务分解给 4 个专业化 Agent：

| Agent | 职责 | 为什么需要独立 |
|-------|------|---------------|
| Supervisor | 意图分析、路由决策、结果拼装 | 集中调度，解耦业务逻辑 |
| KnowledgeRAG | 知识库问答 | 需要独立的 Query Rewrite + 向量检索流程 |
| TicketHandler | 订单查询/操作 | 需要对接后端 API，涉及权限判断 |
| ComplianceChecker | 合规审查 | 所有回复必经审查，独立保障安全 |

**面试可讲**："我基于 LangGraph 实现了一个 Supervisor 模式的多 Agent 系统。Supervisor 通过 LLM 动态分析意图并路由给对应子 Agent，每个子 Agent 有独立的工具集和处理流程，最终所有回复经过合规 Agent 审查后才返回用户。"

#### ② 自研 MCP 工具协议，LLM 驱动真实业务操作

系统没有停留在"回答问题"，而是让 LLM **真正操作业务系统**——查询订单、接单拒单、查询营收数据。

**面试可讲**："我参照 Anthropic 的 MCP 标准，用装饰器模式实现了一套工具注册/发现/调用框架。LLM 做决策选工具，Python 做可靠的 HTTP 调用。工具层还做了权限隔离——消费者只能用 user_* 工具查自己的订单，管理员才能用全部管理功能。这样即使 LLM 产生了错误的工具调用意图，权限层也能兜底。"

**权限隔离的实现细节**：

    先看 Spring Boot 源码的真实情况：

    Step 1. JWT 签发 — 里面没有 role 字段

      UserController.java (用户登录):   claims = { "userId": 4 }
      EmployeeController.java (管理员): claims = { "empId": 1 }
      JwtClaimsConstant.java 定义的字段只有: EMP_ID, USER_ID, PHONE, USERNAME, NAME

    Step 2. 权限判断 — URL 路径模式，不是 role 鉴权

      WebMvcConfiguration.java:
        jwtTokenAdminInterceptor -> 拦截所有 /admin/**
        jwtTokenUserInterceptor  -> 拦截所有 /user/**

      逻辑：能解析出 empId -> 有权访问 /admin/*，能解析出 userId -> 有权访问 /user/*
      管理员和用户被建模为两套独立的后端子模块，这个是学生项目的简化设计。
      生产系统通常会用一个 role 字段统一管控。

    Step 3. FastAPI Agent 层对接 — 根据 Header 名字分流

      api/main.py:
        "token" header          -> auth_type = "admin"
        "authentication" header -> auth_type = "user"
      ticket_handler.py 中根据 auth_type 走向不同 if/else 分支。

    **结论：JWT 里没有 role。权限隔离 = URL 路径拦截器 + 两套独立 JWT。**
    后续可升级为统一 RBAC——一个 role 字段，单一密钥，统一拦截器。

**面试可讲**："AI 客服作为中间服务，权限隔离依赖两层。展示层在 FastAPI 根据 Header 名字分流——消费者看不到管理端工具。兜底层在 Spring Boot——/admin/** 和 /user/** 各用独立 JWT 拦截器校验。即使 AI 层分流错了，下游也不会把数据互串。后续方向是升级为统一 RBAC，在 JWT 里加 role 字段，由一个拦截器根据 role 判断权限。"

#### ③ JWT 透明穿透 — 异构系统间零侵入鉴权

Python Agent 不需要解析 JWT，不需要知道用户身份，不需要存储密钥——它只是把 H5 前端发来的 token 原封不动传给 Java 后端。**单一职责：认证归 Java，推理归 Python。**

**面试可讲**："跨语言微服务场景下，我在 Python Agent 中设计了一个 `BackendClient` 层实现 JWT 透传。Agent 不做任何 JWT 解析，只是从请求 header 取出 token → 在调用后端 API 时设回去。Java 端正常验签。这样 Python 服务零安全负担，适配任何签发方。"

#### ④ 三层记忆架构 + 优雅降级

| 层级 | 存储 | 降级策略 |
|------|------|---------|
| Working Memory | 进程内存 | 无需降级，请求即生命 |
| Short-Term Memory | Redis | Redis 不可用 → 进程内 dict 回退 |
| Long-Term Memory | FAISS 磁盘 | FAISS 不可用 → 关键词匹配回退 |

**面试可讲**："系统的记忆模块每一层都有 fallback 机制。Redis 挂了不影响对话连续性，FAISS 没装也能走关键词检索。这种'自愈'设计降低了运维复杂度。"

#### ⑤ 合规审查双阶段流水线

规则引擎（正则+关键词，零延迟）先做快速筛查，仅当检出风险项时才触发 LLM 深度审查。**既保证了安全性，又控制了 LLM 调用成本。**

**面试可讲**："合规审查我做了一个两阶段流水线。第一阶段是纯正则+关键词的规则引擎，毫秒级完成。只有规则引擎检出可疑内容时，才走第二阶段的 LLM 深度审查。这样 90% 的正常回复只走快路径，大幅降低 token 消耗。"

#### ⑥ 全链路可观测性

**问题背景**：一次用户请求要经过 Supervisor → 子 Agent → 合规审查，涉及 LLM 调用 + HTTP 调用 + 规则引擎。如果某个环节慢或者报错，日志散落在不同模块里很难定位。需要一个工具把一次请求的完整调用链串起来。

##### 6.1 架构概览

```
                    ┌─────────────────────┐
                    │   Python Agent 进程   │
                    │                     │
  @trace_agent_call │   supervisor  [Span] │──┐
  @trace_agent_call │   ticket      [Span] │  │  BatchSpanProcessor
  @trace_agent_call │   rag         [Span] │  │   (异步批量发送)
  @trace_agent_call │   compliance  [Span] │  │       │
                    │                     │  │       ▼
                    └─────────────────────┘  │  OTLP gRPC :4317
                                              │       │
                                              │       ▼
                                              │  ┌──────────┐
                                              └─►│  Jaeger  │
                                                  │  :16686  │
                                                  └──────────┘
```

##### 6.2 装饰器源码逐行解读

```python
# otel_config.py — 核心只有 50 行

def trace_agent_call(agent_name: str):        # ← 装饰器工厂，传入 Agent 名
    """为每个 Agent 方法自动创建 Span"""

    def decorator(func):                       # ← 真正的装饰器，接收被包装的函数
        @functools.wraps(func)                 # ← 保留原函数的签名和名称
        async def wrapper(*args, **kwargs):     # ← 替换原函数的包装函数

            tracer = get_tracer()              # ← 获取全局 Tracer 实例
            if tracer is None:                 # ← 如果 OTEL 没装，直接调原函数
                return await func(*args, **kwargs)   #    零副作用

            span_name = f"agent.{agent_name}.{func.__name__}"
            # 例如: "agent.supervisor.route_decision"

            with tracer.start_as_current_span(span_name) as span:
                # start_as_current_span 做两件事：
                # ① 创建一个 Span
                # ② 把这个 Span 设为"当前活跃 Span"（context propagation）
                #    如果外层已经有 Span，新 Span 自动成为子 Span

                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.method", func.__name__)

                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("agent.duration_ms", duration_ms)
                    span.set_attribute("agent.success", True)
                    return result

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("agent.duration_ms", duration_ms)
                    span.set_attribute("agent.success", False)
                    span.set_attribute("agent.error", str(e))
                    span.record_exception(e)   # ← 记录完整堆栈，Jaeger 可查看
                    raise                     # ← 继续向外抛，不吞异常

        return wrapper
    return decorator
```

##### 6.3 Span 父子链是如何建立的

关键在于 `start_as_current_span` 的 context propagation 机制——OpenTelemetry 在 Python 线程/协程上下文中维护了当前 Span 的引用。调用链如下：

```
用户请求 → /api/chat
  │
  ├─ supervisor.route_decision()          ← 没有外层 Span，这是根 Span
  │     │  @trace_agent_call("supervisor")
  │     │  tracer.start_as_current_span("agent.supervisor.route_decision")
  │     │  → 创建 Span#1，设为当前
  │     │
  │     ├─ 内部调用 llm.ainvoke()
  │     │
  │     └─ Span#1 结束（with 块退出）
  │
  ├─ ticket_handler.process()             ← 同样没有嵌套，新的根 Span
  │     │  @trace_agent_call("ticket_handler_process")
  │     │  tracer.start_as_current_span("agent.ticket_handler.process")
  │     │  → 创建 Span#2
  │     │
  │     ├─ analyze_request()              ← 被 process() 调用
  │     │     @trace_agent_call("ticket_analyze")
  │     │     tracer.start_as_current_span("agent.ticket_analyze")
  │     │     → 检测到 Span#2 是当前 Span → Span#3 自动设为 Span#2 的子 Span
  │     │
  │     └─ execute_action()               ← 也被 process() 调用
  │           @trace_agent_call("ticket_execute")
  │           → Span#4，也是 Span#2 的子 Span
  │
  └─ compliance_check.process()           ← 根 Span#5
```

Jaeger 展示的效果：

```
  Service: smart-cs-multi-agent
  ┌───────────────────────────────────────────────────────────────┐
  │ Trace: /api/chat                                               │
  ├───────────────────────────────────────────────────────────────┤
  │ agent.supervisor.route_decision   ━━━━━━━ 2.3s                 │
  │ agent.ticket_handler.process      ━━━━━━ 3.1s                  │
  │   agent.ticket_analyze            ━━━ 1.8s    ← 子 Span，缩进   │
  │   agent.ticket_execute            ━━ 0.4s     ← 子 Span，缩进   │
  │ agent.compliance_check.process    ━ 0.02s                      │
  └───────────────────────────────────────────────────────────────┘
```

##### 6.4 数据是怎么到 Jaeger 的

```
init_tracer() 在 FastAPI 启动时执行：

  resource = Resource.create({"service.name": "smart-cs-multi-agent"})
  provider = TracerProvider(resource=resource)

  if otlp_endpoint:   # .env 中 OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
      exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
  else:
      exporter = ConsoleSpanExporter()   # 没配 Jaeger 就输出到控制台

  provider.add_span_processor(BatchSpanProcessor(exporter))
  # BatchSpanProcessor: 不是每个 Span 立即发送，而是攒一批（默认 512 个或每 5 秒）
  # 避免高并发时每个 Span 单独走网络的开销

  trace.set_tracer_provider(provider)
  _tracer = trace.get_tracer("smart-cs-multi-agent")
```

##### 6.5 AgentMetrics — 内存中的补充指标

除了 Span 追踪，`AgentMetrics` 类提供在进程内的实时聚合：

```python
class AgentMetrics:
    def record_call(self, agent_name, duration_ms, success):
        self._call_counts[agent_name] += 1
        self._total_duration[agent_name] += duration_ms
        if not success:
            self._error_counts[agent_name] += 1

    def get_summary(self):  # 通过 GET /api/metrics 暴露
        return {
            "supervisor": {
                "total_calls": 42,
                "avg_duration_ms": 2300,
                "error_rate": 0.02
            },
            "ticket_handler": { ... },
            ...
        }
```

##### 6.6 被装饰的 15 个方法一览

| Agent | 方法 | Span 名 |
|-------|------|---------|
| Supervisor | `route_decision()` | `agent.supervisor.route_decision` |
| Supervisor | `synthesize_response()` | `agent.supervisor.synthesize_response` |
| TicketHandler | `analyze_request()` | `agent.ticket_analyze` |
| TicketHandler | `execute_action()` | `agent.ticket_execute` |
| TicketHandler | `process()` | `agent.ticket_handler.process` |
| KnowledgeRAG | `rewrite_query()` | `agent.rag_query_rewrite` |
| KnowledgeRAG | `retrieve_documents()` | `agent.rag_retrieve` |
| KnowledgeRAG | `generate_answer()` | `agent.rag_generate` |
| KnowledgeRAG | `process()` | `agent.knowledge_rag.process` |
| Compliance | `rule_check()` | `agent.compliance_rule_check` |
| Compliance | `llm_check()` | `agent.compliance_llm_check` |
| Compliance | `full_check()` | `agent.compliance_full_check` |
| Compliance | `process()` | `agent.compliance.process` |
| IntentRouter | `classify()` | `agent.intent_router` |
| IntentRouter | `process()` | `agent.intent_router.process` |

**面试可讲**："多 Agent 系统的调试痛点在于一次请求跨越多个模块，日志分散。我用 OpenTelemetry 的装饰器模式解决了这个问题——写了一个 `@trace_agent_call` 装饰器，用 50 行代码给 15 个 Agent 方法自动创建 Span。关键是利用了 `start_as_current_span` 的上下文传播机制：内层方法被外层方法调用时，自动建立父子 Span 关系，不需要手动传 traceId。最终通过 OTLP gRPC 批量导出到 Jaeger，可以在一个 waterfall 视图里看到 Supervisor 花了 2 秒、RAG 检索花了 50ms、合规审查花了 20ms——每个环节的瓶颈一目了然。"


---

#### ⑦ 人工接管闭环（Human-in-the-Loop）

**问题背景**：AI 客服不是万能的——用户明确要求人工、或 AI 兜不住复杂诉求时，不能死磕 LLM。需要一套把会话"升级给真人客服"的完整闭环。

**实现**（`agents/human_handoff.py` + `agents/ws_manager.py`）：
- **状态机**管理升级会话全流程：`queued`（排队）→ `active`（管理员接管）→ `resolved`（解决）
- Supervisor 图中作为独立节点 `human_handoff`，LLM 检测到用户要求人工时路由进入
- 管理后台可实时接管（accept）、回复（agent_reply）、解决（resolve）
- `last_delivered_index` 记录"哪些人工回复已投递给用户"，保证**不丢不重**
- 暴露一整套 API：`/api/human-queue`、`{id}/accept`、`{id}/reply`、`{id}/user-poll`

**WebSocket 双端实时通道**：每条升级会话维护 **user + admin 两条 WS 连接**，消息双向透传。一方断线时消息入 `deque` 缓冲，重连后自动 `flush` 回放——**人工接管场景零消息丢失**。这里用 WS 而非 SSE 是因为人工接管需要**双向交互**（用户和管理员都要主动发消息），而 SSE 是单向推送。

**面试可讲**："我做了一个完整的人工接管闭环。当用户要求人工客服时，会话通过状态机升级到人工队列，管理后台用 WebSocket 实时接管并回复。关键设计是每条会话维护用户和管理员双端连接，配合断线缓冲 + 重连回放，保证消息不丢。这体现了 AI 客服不只是'死磕 LLM'，而是有真实的业务兜底闭环。"

---

#### ⑧ 聊天记录持久化（写穿透 + 缓存回填）

**问题背景**：短期记忆存 Redis，但 Redis 有 TTL（30min）且可能被淘汰，过期后多轮对话上下文就丢了。需要一层落盘兜底。

**实现**（`memory/mysql_store.py`，与 `short_term.py` 配合）：
- **写穿透**：每写入一条对话消息，同步写入 MySQL `chat_history` 表
- **回读回填**：Redis 短期记忆过期/为空时，从 MySQL 读回历史，**并回填 Redis**（热数据缓存、冷数据落库）
- **aiomysql 异步连接池**，懒初始化，MySQL 不可用时静默降级，不影响主链路
- 表带 `session_id` 索引 + `(session_id, ts)` 复合索引，支持按会话顺序查询

**⚠️ 记忆分层修正**：长期记忆（FAISS）存的是**知识库文档索引**；MySQL 存的是**用户聊天历史**。两者是**完全不同的东西**，面试时务必区分清楚——长期记忆 = 静态知识库，用户历史 = MySQL 落盘 + Redis 热缓存。

**面试可讲**："短期记忆除了 Redis，我还做了 MySQL 持久化兜底。写入走写穿透落盘，Redis 过期后从 MySQL 回读并回填，形成'热数据缓存、冷数据落库'的分层。这样即使 Redis 重启，用户的历史对话也不会丢。"

---

#### ⑨ 上下文成本控制（token 预算裁剪）

**实现**（`memory/short_term.py` 的 `get_context_window(max_tokens=4000)`）：从最近的对话往回收，按字符粗估 token，超出上限即截断，只把符合预算的上下文喂给 LLM。

**面试可讲**："我给喂给 LLM 的上下文做了 token 预算控制——从最近的消息往回收，按字符估算 token，超过上限就截断。避免历史无限增长撑爆上下文窗口、也控制 token 成本。"

---

### 9.2 多 Agent 延迟问题与优化方案

#### 问题诊断：一次用户消息要几次 LLM 调用？

当前图结构是严格串行的：**Supervisor → 子 Agent → 合规审查 → 拼装**。以两个典型场景为例：

**场景 A："我的订单到哪了？"**

```
supervisor_route     ── 1 次 LLM ── 2~3 秒 ──→ 输出 "ticket_handler"
       │
ticket_handler       ── 1 次 LLM ── 2~3 秒 ──→ 解析意图、提取 order_id
       │
execute_action       ── 0 次 LLM ── <0.5 秒 ─→ HTTP 调用 Spring Boot API
       │
compliance_check     ── 0 次 LLM ── <1ms  ───→ 规则引擎通过，跳过 LLM 深度检
       │
synthesize           ── 0 次 LLM ── <1ms  ───→ 字符串拼接
```

**总计：2 次 LLM 调用，约 4~6 秒。**

**场景 B："有什么好吃的推荐？"**

```
supervisor_route     ── 1 次 LLM ── 2~3 秒 ──→ "knowledge_rag"
       │
rag query_rewrite    ── 1 次 LLM ── 2~3 秒 ──→ 改写为检索词
       │
rag retrieve         ── 0 次 LLM ── <50ms ───→ FAISS/关键词检索
       │
rag generate_answer  ── 1 次 LLM ── 2~3 秒 ──→ 基于文档生成回答
       │
compliance_check     ── 0 次 LLM ── <1ms  ───→ 规则引擎通过
       │
synthesize           ── 0 次 LLM ── <1ms  ───→ 字符串拼接
```

**总计：3 次 LLM 调用，约 6~9 秒。**

**根本原因**：Supervisor 的"先判断意图，再让子 Agent 处理"设计引入了不必要的串行 LLM 调用。每次 LLM 调用都是网络往返 + 模型推理，占延迟的大头。

---

#### 优化方案（按投入产出比排序）

##### 🥇 方案一：规则路由替代 Supervisor LLM 调用（立即可做，2→0 次 LLM）

Supervisor 的 route_decision 每次要调一次 LLM 来决定路由到哪个子 Agent，但实际上外卖客服场景的意图非常集中（订单查询 + 菜单咨询占了 90%+）。用关键词 + 正则匹配替代 LLM 路由，延迟从 2-3 秒降到 <1ms。

```python
# 当前实现（2-3秒）：
# supervisor.py: route_decision() → llm.ainvoke() → "ticket_handler"

# 优化后（<1ms）：
ROUTE_RULES = [
    (r"(我的|我的订单|订单.*在哪|订单.*到哪|查.*订单|订单.*状态|催单|取消订单|再来一单)", "ticket_handler"),
    (r"(推荐|好吃|菜单|有什么|菜品|套餐|怎么.*下单|退款|营业时间|几点.*关门)", "knowledge_rag"),
    (r"(投诉|举报|骂|退款.*不|太差|垃圾)", "compliance_checker"),
]

def route_by_rules(user_message: str) -> str:
    for pattern, target in ROUTE_RULES:
        if re.search(pattern, user_message):
            return target
    return "knowledge_rag"  # 默认走知识库

# 仅当规则匹配失败时，才回退到 LLM 路由（<5% 的情况）
```

**效果**：场景 A 从 2 次 LLM → **1 次 LLM**，场景 B 从 3 次 LLM → **2 次 LLM**。延迟减半。

---

##### 🥈 方案二：SSE 流式响应（改变感知延迟）

当前是全部处理完才返回一个 JSON。改成 SSE (Server-Sent Events) 流式返回：

```
用户: "我的订单到哪了"
  t=0.0s  →  SSE: {"type": "status", "text": "正在分析您的意图..."}
  t=0.5s  →  SSE: {"type": "status", "text": "正在查询您的订单..."}
  t=2.5s  →  SSE: {"type": "content", "text": "您有 2 笔"}
  t=2.8s  →  SSE: {"type": "content", "text": "进行中的订单："}
  t=3.0s  →  SSE: {"type": "content", "text": "订单 #123 ..."}
  t=4.0s  →  SSE: {"type": "done"}
```

**效果**：虽然 wall time 不变，但用户在第 0.5 秒就看到反馈，感知延迟从 6 秒降到 ~2.5 秒。H5 前端只需把 `chatApi.js` 从 `POST /api/chat` 改为对接 `POST /api/chat/stream`（SSE 端点）。

---

##### 🥉 方案三：合并 RAG 的 Query Rewrite + Generate Answer（场景 B 专属，3→2 次 LLM）

当前 knowledge_rag 先调一次 LLM 改写 query，再调一次 LLM 生成回答。两次调用可以合并：

```python
# 当前：2 次 LLM
# query → rewrite_query(llm) → rewritten → retrieve → generate_answer(llm) → answer

# 优化：1 次 LLM
# query → retrieve(query) → docs → generate_answer(llm, query, docs) → answer
#                                    ↑ 直接在 prompt 里让 LLM 理解原始 query + docs
```

**效果**：不损失质量（LLM 完全能同时处理口语化 query + 检索文档），场景 B 从 3 次 LLM → **2 次 LLM**。

---

##### 方案四：模型分层（配合方案一使用）

| 调用 | 推荐模型 | 说明 |
|------|---------|------|
| 路由决策 | 规则引擎（正则+关键词）或 qwen-turbo | 分类任务不需要大模型 |
| 意图解析&内容生成 | qwen-plus / gpt-4o | 核心推理任务 |
| 合规深度审查 | qwen-turbo | 二分类（通过/不通过），小模型即可 |

---

#### 优化效果总览

| 场景 | 优化前 | 方案一 | 方案一+二 | 方案一+二+三 |
|------|--------|--------|-----------|-------------|
| "我的订单到哪了" | 4~6s (2 LLM) | **2~3s** (1 LLM + 流式) | **感知 1.5s** | 同左 |
| "有什么好吃的" | 6~9s (3 LLM) | **4~6s** (2 LLM + 流式) | **感知 2.5s** | **3~4s** (1 LLM + 流式) |
| 代码改动量 | - | 30 行 | +40 行 | +20 行 |

**面试应对**："多 Agent 串行确实是延迟瓶颈。我的优化思路是三层：第一，用规则引擎替代 LLM 做意图路由，把不必要的 LLM 调用砍掉；第二，加 SSE 流式响应改变用户感知——即使 wall time 不变，用户在第 0.5 秒就看到'正在查询'的反馈；第三，合并同类型 LLM 调用（比如 RAG 的改写+生成合并为一次）。三管齐下可以把感知延迟降到 2 秒以内，且不牺牲回答质量。"

---

### 9.2 难点攻克

| 难点 | 挑战 | 解决方案 |
|------|------|---------|
| **LLM 输出不可靠** | LLM 可能输出非法 JSON、不存在的工具名、错误参数类型 | Supervisor 层做意图归一化（非预期值 → 默认路由），TicketHandler 做正则兜底提取订单号，所有 JSON 解析都有 try/except |
| **工具调用权限控制** | 同一个 `POST /api/chat` 接口，管理员和消费者看到的工具集不同 | 通过 `auth_type` 字段 + `execute_action()` 中的 if/else 分支实现工具集隔离，消费者调用管理工具时直接返回拒绝消息 |
| **Python ↔ Java 异构通信** | Spring Boot 返回 `Result<T>` 结构，Python 需要解包 `{code, msg, data}` | `BackendClient._unwrap_result()` 统一解包 + 错误码转换，401/超时/连接失败各有专用异常类型 |
| **Uniapp H5 桌面端适配** | `rpx` 单位在 1920px 屏幕上把元素放大 5 倍 | 通过 `document.documentElement.style.fontSize` 锁定 + MutationObserver 监听，将页面限制为 480px 移动视口 |
| **前端布局多轮迭代** | Uniapp 的 `<scroll-view>` 组件不支持 CSS `flex: 1` 高度继承 | 改用 `position: absolute; top:0; bottom:0` 显式定位撑满，而非依赖 flex 链 |
| **PII 信息保护** | Agent 回复中可能包含用户手机号、地址等敏感信息 | ComplianceChecker 在规则引擎阶段做正则脱敏（`138****5678`），不依赖 LLM |

---



