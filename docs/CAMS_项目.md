# CAMS — 简历项目描述与面试知识点拓展

---

## 一、简历项目描述（精简版）

**空气技研管理平台（CAMS）**

面向洁净室（半导体 / 医院 / 制药 / 实验室等）的空调风机（AHU）设备管理与控制平台，本人负责 AHU/VAV 空调控制、传感器数据监测两个核心模块。对接 HON9000 工业规范，通过 Modbus TCP 打通软件到 PLC 硬件的完整控制闭环，基于传感器时序数据实现运维查询与智能告警。
技术栈：Vue 3 + Spring Boot + MySQL + Redis + RabbitMQ + InfluxDB + Docker + Python FastAPI。

- **设备控制指令链路设计**：设计 HON9000 工业参数到 Modbus 寄存器的转换映射，按 autoOn/autoOff/filter 三种运行模式构建点位动作矩阵，用户在页面修改参数后自动换算并下发至 PLC，支持写入后回读校验

- **多线程并发控制 + 快照回滚**：CompletableFuture + 自定义线程池实现多设备并发，响应 O(n)→O(max)；写前全量快照，中途失败逆序回滚已写点位；REQUIRES_NEW 事务隔离保证单台失败不影响其余

- **实时推送**：Redis Pub/Sub → StateChangeListener → STOMP WebSocket 桥接，状态变更 < 300ms 触达前端，SockJS 降级 + 断线重连

- **RabbitMQ 异步解耦**：请求秒返 taskId，Consumer 异步执行；Direct Exchange 按 AHU/VAV 独立路由；死信队列处理超时异常 + 钉钉告警；Redis SETNX 幂等防重

- **传感器数据监测**：面向洁净室（医院病房、实验室、制药车间等）的空气质量实时监控与智能告警，采集温湿度、CO₂、洁净空气量（CADR）、滤网压力等指标；传感器数据定时同步至 InfluxDB 时序库，指令下发 ACK 状态机追踪，Continuous Query 自动降采样 + Retention Policy 分层存储

- **AI 智能助手**：Function Calling 封装数据查询工具链，实现自然语言查询 + 日报自动生成；规划 RAG 接入企业知识库（使用说明/维修步骤/检测指标），升级为垂直领域运维助手

---

### 对应技术实现与链路拆解

#### ① 设备控制指令链路设计（业务-硬件指令适配与下发）

**业务场景**：半导体洁净室的 AHU 空调机组（风阀 ×5 + 新风机 ×1）需要通过 PLC 精确控制。运营人员在管理后台设置运行模式和参数，系统自动换算并下发到硬件执行。

**完整链路**：

1. **运营人员操作前端页面** → 选择建筑 → 选择设备（如 AHU-01）→ 选择运行模式（autoOn/autoOff/filter）→ 填写参数（风量 m³/h、开度 %）→ 点击"确认下发"
2. **前端 POST `/api/admin/buildings/{id}/control`** → 请求体包含 `equipmentId`、`equipmentType`（AHU/VAV）、`airflowControlMode` 以及各参数（如 `minOaAirflowSetpoint: 1000` 表示最小新风量 1000m³/h）
3. **`EquipmentControlServiceImpl.control()` 接收请求** → 校验建筑存在且状态为 active
4. **`DeviceControlProcessor.processOne()` 逐设备处理** → ① 校验设备已注册且类型匹配 → ② 参数白名单校验（autoOn 模式只允许调 `minOaAirflowSetpoint`，filter 模式允许调 5 个字段，只读字段 `oaAirVelocity` 只查不改）→ ③ 更新 `equipment_states.state_data` JSON 列（记录当前 HON9000 参数值）→ ④ 写 `modification_logs`（记录谁在什么时间改了哪个字段从什么值变成什么值）
5. **检查 `devices.modbus_device_id` 是否绑定了 Modbus 硬件** → 如果非空，调用 `ModbusConversionService.convertAndExecute()` 下发到 PLC
6. **`computeTargets()` 按模式计算目标值**：
   - autoOff：全关，6 个开关线圈写 OFF，6 个开度寄存器写 0%
   - autoOn：全开，SA 送风阀 = 100%，OA 进风阀 = 按 `minOaAirflowSetpoint / max_airflow × 100` 换算，新风 = 100%，其余 100%
   - filter（手动模式）：逐字段按映射表换算。如 `saFanSpeedSetpoint: 50` → SA 开度直写 50%；`fixedOaAirflowSetpoint: 800` → 800/2000×100 = 40%；`eaAirflowSetpoint: 700` → 700/2000×100/2 = 18%（双路均分给 Room1 和 Room2）
7. **j2mod 逐帧写入 PLC** → `writeCoil(slaveId, addr, on/off)` 发 FC=05 写单个线圈 → `writeRegister(slaveId, addr, value)` 发 FC=06 写单个寄存器 → 每次写入等 PLC 回显确认（帧回显 = 写入成功）
8. **写入后立即回读同寄存器地址** → `readPointValue()` 读回实际值，与目标值比对。回读成功以真实值为准返回前端；回读失败不影响主流程，仅记录日志
9. **写入结果记录 `modbus_command_logs`** → 记录设备、点位、功能码、寄存器地址、写入值、回读值、成功/失败状态

> **关键文件**：`EquipmentControlServiceImpl`、`DeviceControlProcessor`（校验+事务）、`ModbusConversionService`（换算引擎）、`ModbusTcpClient`（PLC 通信）

---

#### ② 多线程并发控制 + 快照回滚

**业务场景**：运维人员需要对一个建筑下的多台设备（如 AHU-01 ×2、VAV-101 ×1）同时下发控制指令。串行处理每台 300ms，3 台就要 900ms，用户体验差。更关键的是——如果 3 台中第 3 台失败，前面 2 台已经改了，整体状态不一致。

**完整链路**：

1. **`EquipmentControlServiceImpl.control()` 接到请求** → 主线程先校验建筑，这一步不需要并发
2. **循环请求中的每台设备，创建 `CompletableFuture`** → `supplyAsync(() -> processor.processOne(...), executor)` 提交到自定义线程池
3. **线程池 `deviceControlExecutor` 工作流程**：
   - 核心线程 16 个（CPU 核数 × 2，I/O 密集型公式）→ 空闲时不回收
   - 最大线程 32 个（CPU × 4）→ 突发流量弹性扩容
   - 有界队列 200 → 防止无界队列 OOM
   - 拒绝策略 CallerRunsPolicy → 队列满时由主线程自己跑，天然限流
4. **`DeviceControlProcessor.processOne()` 独立事务执行** → `@Transactional(propagation = REQUIRES_NEW)` 挂起主线程事务，每台设备开全新独立事务 → 一台成功就提交一台，单台失败只回滚自己。**拆成独立 Bean 的原因**：Spring AOP 代理——本类内部 `this.method()` 不走代理，`@Transactional` 无效
5. **批量写入时快照回滚（`batchWrite()`）**：
   - 步骤① 预加载所有点位，校验值范围（如开度 0-100，风量不在 min/max 之间报错）
   - 步骤② 遍历读取每个点位的当前 PLC 值 → 保存为快照数组 `snapshots[0..N]`
   - 步骤③ 逐条写入 PLC，成功加入 `succeeded` 列表，任一条失败立即 break
   - 步骤④ 如果中途失败（`firstFailure >= 0`）：遍历 `succeeded.reverse()` 逆序恢复快照值 → 写 ROLLBACK 日志 → 抛异常告知"已回滚 N 条"
   - 步骤⑤ 全部成功 → 返回结果列表
6. **汇总 `partialFailureList`** → `allOf.get(30, SECONDS)` 等所有 future 完成 → 完成的拿结果，超时的记 TIMEOUT → 前端展示"AHU-01 成功 / AHU-02 成功 / VAV-101 失败：值超出范围"

> **关键文件**：`EquipmentControlServiceImpl`（编排）、`DeviceControlProcessor`（独立事务）、`AhuControlServiceImpl.batchWrite()`（快照回滚）、`ThreadPoolConfig`（线程池）

---

#### ③ 实时状态推送（Redis Pub/Sub → WebSocket）

**业务场景**：管理员 A 在浏览器修改了 AHU-01 的参数。管理员 B 正在看同一建筑下的设备状态页面，如果不刷新，他看到的是旧数据。需要一种机制让变更发生后，所有关注该建筑的用户页面自动更新。

**完整链路**：

1. **`DeviceControlProcessor.processOne()` 执行完成后** → 设备状态已更新到 MySQL，此时发布一条 Redis 消息
2. **`redisTemplate.convertAndSend("cams:state:{buildingId}", msg)`** → 消息内容仅包含 `equipmentId` + `buildingId` + `timestamp`，**不包含具体参数值**（推拉结合——推只发事件通知，具体值由前端自己拉）
3. **Redis Pub/Sub 广播** → channel 命名按建筑拆分（`cams:state:BLDG-A`），同一建筑的设备变更走同一频道，减少无关推送
4. **`StateChangeListener.onMessage()` 接收** → 通过 `PSUBSCRIBE cams:state:*` 通配符订阅所有建筑频道 → 回调中提取 `buildingId = channel.replace("cams:state:", "")`
5. **桥接到 WebSocket** → `messagingTemplate.convertAndSend("/topic/building/" + buildingId, body)` → Spring STOMP 消息代理广播给所有订阅了该 topic 的 WebSocket 连接
6. **前端 `useWebSocket.ts`** → `@stomp/stompjs` + `sockjs-client` 建立连接 → `SUBSCRIBE /topic/building/{buildingId}` → 收到消息回调 `onStateChange(change)` → 判断 `change.equipmentId` 是否匹配当前页面 → 匹配则调 `fetchState()` 拉最新数据
7. **容错机制**：
   - SockJS 降级：WebSocket 不可用时（企业防火墙拦截 HTTP Upgrade）自动切 HTTP 长轮询
   - 断线重连：`reconnectDelay: 5000`，每 5 秒尝试重连，重连成功后自动重新 SUBSCRIBE
   - 推拉结合：消息丢了 ≠ 数据错了。客户端下次打开页面时主动 GET 接口拉，永远以拉到的值为权威

> **关键文件**：`StateChangeListener`（Redis→WebSocket 桥接）、`WebSocketConfig`（端点/代理配置）、`useWebSocket.ts`（前端 STOMP 客户端）

---

#### ④ RabbitMQ 异步控制指令

**业务场景**：同步模式下 POST /control 需要等所有设备处理完才返回（并发也要 ~300ms）。当一次请求涉及更多设备、或需要外部系统（如钉钉审批回调）触发控制时，同步方式无法扩展。改为异步：接口秒级响应，后台可靠消费。

**完整链路**：

1. **客户端 POST /control** → Controller 校验建筑 → 调 `Producer.submit()`
2. **`Producer` 生成幂等键** → `requestId = MD5(buildingId + source + timestamp)` → **先写 `control_tasks` 表**（`status=pending`，保存原始请求 JSON）→ 再发 MQ（**先写表后发 MQ 的顺序很重要**——即使 MQ 挂了，任务记录也在数据库里，补偿定时任务能扫到）
3. **`rabbitTemplate.convertAndSend("cams.control.exchange", equipmentType, msg)`** → 按设备类型做 routingKey：AHU → `cams.control.ahu` 队列，VAV → `cams.control.vav` 队列。分开队列的好处：AHU 通常比 VAV 多（4 台 vs 2 台），AHU 队列配 5-10 个消费者，VAV 配 3-5 个，独立调并发
4. **接口立即返回** → `{ taskId, status: "pending" }`，耗时 ~50ms。客户端拿到 taskId 后轮询 `GET /control/tasks/{taskId}` 或等 WebSocket 通知完成
5. **`@RabbitListener` 异步消费**（5-10 线程并发）：
   - ① **幂等检查**：`redisTemplate.opsForValue().setIfAbsent("cams:control:" + taskId, "1", 24h)` → 返回 false = 重复消息 → `channel.basicAck()` 直接丢弃
   - ② **更新任务状态** → `control_tasks.status = 'processing'`
   - ③ **执行控制** → 复用 `DeviceControlProcessor.processOne()`，包括校验、更新状态、写日志、Modbus 下发
   - ④ **写回结果** → `control_tasks.status = 'completed'` + `result` JSON
   - ⑤ **`channel.basicAck()`** → 手动确认消费，消息从 Queue 删除
6. **异常路径 — 死信队列（DLQ）**：
   - 触发条件：`processOne()` 抛异常 → Spring AMQP 自动 `basicNack(requeue=false)`；或 Queue TTL 30 秒超时无人消费；或队列积压超 1000 条
   - 消息自动转发到 `cams.dlx.exchange` → `cams.control.dlq`
   - `DeadLetterHandler` 消费死信 → 标记 `control_tasks.status = 'failed'` → 发送钉钉告警通知运维
7. **补偿机制**：`@Scheduled(fixedDelay = 30000)` 每 30 秒扫描 `status = 'send_failed'` 的任务 → 重试 `rabbitTemplate.convertAndSend()` → 成功则更新状态为 `pending` 等待消费
8. **三层可靠性保证**：L1 Publisher Confirm（消息到 Queue 才返回）/ L2 幂等键（重复投递自动丢弃）/ L3 MySQL 事务回滚（JVM 崩溃→连接断开→未提交事务自动回滚）

> **关键文件**：`ControlTaskProducer`、`ControlTaskConsumer`、`DeadLetterHandler`、`RabbitMQConfig`

---

#### ⑤ 传感器数据监测模块（cams-cgq）

**模块定位**：面向洁净室（医院病房、实验室、制药车间等）的空气质量实时监控与智能告警平台，通过传感器采集温湿度、CO₂、洁净空气量（CADR）、滤网压力等环境指标，提供传感器管理、数据采集、指令下发、时序存储与智能预警。

**业务场景**：洁净室部署 100+ 个环境传感器，分布在 AHU 的 OA/RC/SA/DOWN/UP 五个点位，每 60 秒上报一次 37 维测量数据（温度、湿度、CO₂、颗粒物计数、风速风量、压差、滤网压损）。需要支持实时监控、趋势分析和异常预警。

**完整链路（已实现）**：

1. **传感器注册管理** → `SensorController` 提供传感器 CRUD → `sensors` 表记录 sensor_id（19~20 位 ICCID）、类型（ENVIRONMENTAL/PARTICLE/AIRFLOW/COMBINED）、安装点位（OA/RC/SA/DOWN/UP）、tags 分组、`sync_enabled` / `sync_interval` 采集开关
2. **数据生成（开发/测试阶段）** → `SensorDataGenerator` 基于真实物理模型模拟 → 温度用余弦函数模拟昼夜变化（中午峰值 + 高斯噪声 ±0.5℃）→ CO₂ 区分工作时间（8:00-18:00 叠加 300ppm 人体活动增量）→ 颗粒物按幂律分布 `d⁻²·⁵` × 区域缩放系数（Down=1.0×, Up=2.8×, OA=2.5×, RC=0.9×, SA=0.6×）模拟洁净室各区域洁净度梯度
3. **定时同步 `SensorDataSyncJob`** → `@Scheduled(fixedDelay = 60000)` 每 60 秒遍历 `sync_enabled=true` 的传感器 → 逐条同步测定值 → 写入 `sensor_measurements` 表（37 维 + raw_data 原始 JSON + data_quality 质量标记）
4. **指令下发与 ACK 追踪** → `SensorCommandController` 下发指令 → `sensor_commands` 表记录 cmd_id、op、arg、expires → ACK 状态机（pending → sent → acked / failed / timeout / expired）→ 定时轮询 ACK 直到超时
5. **MySQL 分区维护** → `PartitionMaintenanceJob` 定期对 `sensor_measurements` 按时间分区（partition by range），过期分区直接 DROP 而非逐行 DELETE，避免表碎片
6. **离线标记** → 同步失败的传感器调用 `updateOnlineStatus(sensorId, "offline")` → 前端面板显示红色离线标记

**规划 / 待实现**（技术上已论证，后续落地）：

- **InfluxDB 时序存储升级**：当前数据存 MySQL，量级上来后写入吞吐与大范围时间扫描会成为瓶颈。规划迁移 InfluxDB——Line Protocol 写入 → TSM 引擎列式压缩（10×+）→ Continuous Query 自动降采样（1h/1d）→ Retention Policy 分层（raw 7 天 / 1h 90 天 / 1d 365 天），查询按时间范围自动路由到最优 RP
- **预警引擎**：`sensors.alarm_config` 已预留阈值配置字段。规划实现三级判定——阈值判断 + 毛刺过滤（异常持续 ≥30s 才触发，过滤开门等瞬时波动）+ 冷却去重（同指标 300s 内不重复推送）→ Redis 发布告警 → WebSocket 推送前端 + 多渠道通知

> **关键文件**：`SensorController`、`SensorDataSyncJob`、`SensorCommandController`、`PartitionMaintenanceJob`、`SensorDataGenerator`

---

#### ⑥ AI 智能助手（系统级，RAG 垂直领域）

**模块定位**：不止于定时报告，而是面向整个 CAMS 的垂直领域运维助手——基于企业知识库（设备使用说明、维修步骤、检测指标标准）做检索增强（RAG），让运维人员用自然语言完成查询、诊断与决策。

**已实现（Python 侧）**：

- **Function Calling 工具链**：封装 5 个数据查询工具（query_rooms / query_stats / query_alerts / query_room_trend / query_anomaly_rooms），模型先决策调用哪个工具 → 执行 → 二次调用 LLM 生成自然语言回复。解决 LLM 自由文本无法直接对接数据库、结果不可控的问题
- **日报自动生成**：每日 08:00 定时汇总统计 + 异常 + 告警历史，拼装 Prompt 由 DeepSeek 生成 Markdown 日报，多渠道推送（定时任务能做的只是"到点推送"，日报的内容组织靠 LLM 而非硬编码模板）

**规划 / 待实现（RAG 知识库）**：

1. **文档切分**：将企业知识库（设备使用说明、维修手册、检测指标标准、SOP）切分为语义块
2. **向量化 + 入库**：embedding 模型将文本块转为向量，存入向量库（Milvus / FAISS）
3. **检索增强**：用户提问 → 向量检索 Top-K 相关文档 → 拼入 Prompt → LLM 生成带出处的回答
4. **知识库范围**：设备使用说明、维修步骤、检测指标阈值标准、历史告警处置记录

> **为什么是 RAG 而非微调**：企业知识库会随设备型号、检测标准持续更新，微调每次都要重训、成本高且时效差；RAG 只需更新向量库，检索结果带出处可追溯，更适合企业知识库频繁更新的场景。

> **技术栈**：Python FastAPI + DeepSeek（Function Calling）+ 向量数据库（规划）

---

---

## 二、技术栈一览

| 层级 | 技术 | 用途 |
|------|------|------|
| 后端框架 | Spring Boot 2.7 | 主应用 + 传感器微服务（cams-cgq） |
| ORM | MyBatis-Plus | 数据访问层 |
| 关系数据库 | MySQL 8.0 | 业务数据 + 设备状态 + 传感器时序（分区） |
| 缓存 | Redis 7 | 缓存 + Pub/Sub + 幂等键 |
| 消息队列 | RabbitMQ | 控制指令异步解耦 |
| 实时推送 | WebSocket + STOMP | 设备状态实时推送 |
| 时序数据库 | InfluxDB（规划） | 传感器时序存储升级，CQ 降采样 + RP 分层 |
| AI / LLM | Python FastAPI + DeepSeek | AI 助手（Function Calling）+ RAG（规划） |
| 向量数据库 | Milvus / FAISS（规划） | RAG 知识库检索 |
| 前端 | Vue 3 + TypeScript + Element Plus | 管理后台 |
| 部署 | Docker Compose + Nginx | 容器化部署 |

---

## 三、分点知识点拓展

### 1. 设备控制指令链路设计

#### 1.1 业务背景

半导体洁净室的 AHU（Air Handling Unit，空气处理机组）需要精确控制各风阀开度与风机转速以维持洁净度。HON9000 是甲方指定的上层工业接口规范，定义了 airflowControlMode（autoOn/autoOff/filter）三种运行模式及各参数语义。PLC 是底层执行硬件，通过 Modbus TCP 协议控制风阀和风机。

核心问题：**上层业务参数（m³/h、%）和底层硬件寄存器（0-100 整数）不是一一对应的**，需要一个转换层。

#### 1.2 转换规则

| 换算类型 | 输入 | 输出 | 公式 | 适用参数 |
|----------|------|------|------|----------|
| PERCENT_DIRECT | % | 0-100 int | 直接写入 | raDamperPositionSetpoint, saFanSpeedSetpoint, eaFanSpeedSetpoint |
| AIRFLOW_TO_PERCENT | m³/h | 0-100 int | value / max_airflow × 100 | minOaAirflowSetpoint, fixedOaAirflowSetpoint |
| AIRFLOW_TO_PERCENT_SPLIT | m³/h | 0-100 int | value / max_airflow × 100 / 2 | eaAirflowSetpoint → Room1 + Room2 各 50% |

#### 1.3 三模式动作矩阵

| 模式 | SA 阀 | OA 阀 | RA 阀 | Room1 | Room2 | 新风机 | 开关 |
|------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:----:|
| autoOff | 0% | 0% | 0% | 0% | 0% | 0% | 全 OFF |
| autoOn | 100% | 按 minOa | 100% | 100% | 100% | 100% | 全 ON |
| filter | 按 saFan | 按 fixedOa | 按 raDamper | 按 eaAir÷2 | 按 eaAir÷2 | 按 eaFan | 全 ON |

#### 1.4 面试追问预期

**Q: "回读校验"具体怎么做的？**

> 写入后立即读取同一寄存器地址，对比写入值与回读值。回读成功返回真实值；回读失败（超时/异常）不影响主流程，仅记录日志。真实值优先于目标值返回给前端。

**Q: 如果 PLC 返回的值跟你写的不一样怎么办？**

> 可能的场景：PLC 内部有限幅逻辑（比如最大值钳位到 80%），或者寄存器被其他系统同时修改了。当前策略是以回读值为准返回，不做自动重试——因为不知道差异原因，盲目重试可能造成振荡。差异记录到 command_log 供运维排查。

**Q: max_airflow 怎么来的？**

> 存储在 `modbus_ahu_devices.max_airflow`，默认 2000 m³/h，可按设备单独配置。不同的 AHU 型号最大风量不同（2000/3000/4000），写成配置项而非硬编码。

---

### 2. 多线程并发控制 + 快照回滚

#### 2.1 改前改后对比

```
改前（串行）：
  请求 → AHU-01(300ms) → AHU-02(300ms) → VAV-101(300ms) → 返回
  总耗时 ≈ 900ms

改后（并发）：
  请求 → ┬─ AHU-01(300ms) ┐
         ├─ AHU-02(300ms) ┤ CompletableFuture + 线程池
         └─ VAV-101(300ms)┘
         allOf 等待全部 → 汇总 → 返回
  总耗时 ≈ max(300,300,300) = 300ms
```

#### 2.2 线程池参数设计

```java
corePoolSize = CPU核数 × 2   // I/O密集型：大部分时间等数据库
maxPoolSize  = CPU核数 × 4   // 峰值弹性
workQueue    = LinkedBlockingQueue(200)  // 有界队列防 OOM
rejectedHandler = CallerRunsPolicy       // 队列满时调用者线程执行，天然限流
```

#### 2.3 为什么是 I/O 密集而非 CPU 密集

`processOne()` 单次调用涉及 5-6 次数据库操作（查建筑、查设备、查状态、逐字段更新、写日志），CPU 大部分时间在等 MySQL 网络 I/O 返回，处于空闲状态。此时多开线程可以并行利用空闲窗口。

```
时间线（单线程）：
  [SQL][等待数据库返回][SQL][等待][SQL][等待]  ← CPU 大量闲置

时间线（2 线程）：
  Thread-1 [SQL][等待][SQL][等待]
  Thread-2          [SQL][等待][SQL][等待]  ← CPU 利用率翻倍
```

#### 2.4 快照回滚机制

```
batchWrite 执行流程：
  ① 预加载所有点位 + 校验值范围
  ② 遍历读取每个点位的当前值 → 保存快照数组 snapshots[]
  ③ 逐条写入，成功则加入 succeeded 列表，失败则 break
  ④ 如果中途失败（firstFailure >= 0）：
     for idx in succeeded:          // 逆序回滚
         doWrite(slaveId, point, snapshots[idx])  // 恢复到快照值
         saveLog(ROLLBACK)
     抛异常：已回滚 N 条
  ⑤ 全部成功 → 返回结果
```

#### 2.5 事务隔离

每台设备的处理逻辑拆到独立 Service 类 `DeviceControlProcessor`，标注 `@Transactional(propagation = Propagation.REQUIRES_NEW)`。

**为什么要拆独立类？** Spring 事务基于 AOP 代理，本类内部调用 `this.processOne()` 不经过代理 → `@Transactional` 失效。必须注入另一个 Bean 调用才触发代理。

**为什么用 REQUIRES_NEW？** 每台设备独立事务，一台失败回滚自己的，不影响其他已提交设备的修改。

#### 2.6 线程安全

当前设计天然线程安全——`DeviceControlProcessor` 无成员变量，所有数据在方法局部变量（栈上私有，线程隔离）。每台设备操作不同数据库行，MySQL 行级锁天然不冲突。

四个线程安全原则：
1. 无状态（无成员变量）→ 天然安全 ✅
2. 有状态但不可变 → 安全
3. 有状态可变但用 ConcurrentHashMap/AtomicInteger → 安全
4. 有状态可变但用 synchronized/ReentrantLock → 安全但可能性能差

#### 2.7 面试追问预期

**Q: 快照回滚如果也失败了怎么办？**

> 记录 ROLLBACK_FAIL 日志 + 钉钉告警，人工介入。回滚失败的场景极少（通常是 PLC 断连或网络故障），此时已写入的点位值被部分修改，需要运维到 Modbus 调试面板手动恢复。

**Q: 为什么不直接用 synchronized 或 Lock？**

> synchronized 是悲观锁，多线程会串行化——等于白并发。当前场景无共享状态，不需要锁。

**Q: CompletableFuture.allOf 和 CountDownLatch 有什么区别？**

> CountDownLatch 只能等，不能获取线程返回值；CompletableFuture 可以获取每个 future 的返回值用于汇总 partialFailure 列表。CountDownLatch 适合"等 N 个线程就绪后一起开始"的场景，CompletableFuture 适合"等 N 个任务完成并收集结果"的场景。

---

### 3. 实时推送（Redis Pub/Sub → WebSocket）

#### 3.1 整体数据流

```
DeviceControlProcessor.processOne()
  → redisTemplate.convertAndSend("cams:state:{buildingId}", msg)
    → Redis Pub/Sub 广播
      → StateChangeListener.onMessage()        ← PSUBSCRIBE cams:state:*
        → messagingTemplate.convertAndSend(
            "/topic/building/{buildingId}", body)
          → WebSocket STOMP 推送到浏览器
            → 前端自动刷新设备状态
```

端到端延迟 < 300ms。

#### 3.2 为什么选 Redis Pub/Sub 而不是 RabbitMQ 做推送？

| 维度 | Redis Pub/Sub | RabbitMQ |
|------|--------------|----------|
| 消息持久化 | ❌ 不存 | ✅ 磁盘持久化 |
| 消费确认 | ❌ 无 ACK | ✅ 消费者 ACK |
| 吞吐量 | ~10 万条/秒 | ~1 万条/秒 |
| 部署成本 | 已有 Redis，零额外 | 需额外部署 |
| 适用场景 | 实时推送（丢几条没事） | 业务消息（一条不能丢） |

设备状态推送是"软实时"——丢了最多用户没看到刷新，手动 F5 即可，不需要持久化。

#### 3.3 推拉结合

推送消息体只发变更事件（equipmentId + buildingId + timestamp），不包含具体值——前端收到后调 API 拉最新权威数据。这样即使推送丢了，数据也不会错误。

#### 3.4 SockJS 降级

WebSocket 需要 HTTP Upgrade，部分企业网络代理/防火墙会拦截。SockJS 在 WebSocket 不可用时自动降级到 HTTP 长轮询（long polling），保证兼容性。

#### 3.5 STOMP 协议

裸 WebSocket 只是双向字节流。STOMP 在 WebSocket 上加了消息语义层——SUBSCRIBE/UNSUBSCRIBE/SEND/MESSAGE——不需要自己定 JSON 协议来区分消息类型。

#### 3.6 面试追问预期

**Q: 1000 人同时在线，Spring SimpleBroker 扛得住吗？**

> 上限约 1-2 万连接。超过可以换外部 STOMP Broker（如 RabbitMQ STOMP 插件），架构不需要改，只改 broker 配置。

**Q: 怎么保证消息只推给有权限的人？**

> STOMP CONNECT 阶段校验 token，ChannelInterceptor 拦截 SUBSCRIBE 请求校验该用户是否有对应 buildingId 的权限。

---

### 4. RabbitMQ 异步解耦

#### 4.1 为什么需要异步

同步模式下，客户端 POST /control 后要等所有设备处理完才返回（3 台设备 ≈ 300ms，10 台可能更长）。异步化后接口秒返 taskId，客户端轮询或 WebSocket 通知结果。

#### 4.2 架构

```
客户端 POST /control
  → Controller 校验建筑
  → 写 control_tasks (status=pending)
  → rabbitTemplate.convertAndSend("cams.control.exchange", "AHU", msg)
  → 立即返回 { taskId, status: "pending" }    ← ~50ms 返回

后台异步：
  @RabbitListener(queues = "cams.control.ahu")
  → 幂等检查 (Redis SETNX)
  → 更新任务状态 → processing
  → DeviceControlProcessor.processOne()
  → 更新任务状态 → completed
  → channel.basicAck()
```

#### 4.3 为什么用 Direct Exchange 按设备类型路由

AHU 和 VAV 的处理逻辑相同但流量不同（通常 AHU 多于 VAV），分开队列可以独立调并发数。例如 AHU 队列配 5-10 个消费者，VAV 配 3-5 个。

#### 4.4 死信队列（DLQ）

三种触发条件：
1. 消息被拒绝（basicNack）且 requeue=false → 消费者处理抛异常
2. 消息 TTL 超时（30 秒）→ 消费者全挂/忙不过来
3. 队列满（maxLength=1000）→ 突发流量保护

死信处理器 → 标记任务 failed + 钉钉告警 → 人工介入排查。

#### 4.5 幂等性

问题：网络闪断导致 Producer 重试，Consumer 收到两条相同消息。

解法：Redis `SETNX`（SET if Not eXists）原子操作：

```java
Boolean acquired = redisTemplate.opsForValue()
    .setIfAbsent("cams:control:" + taskId, "1", Duration.ofHours(24));
if (!acquired) {
    channel.basicAck(deliveryTag, false);  // 重复消息，直接丢掉
    return;
}
```

#### 4.6 补偿机制

定时任务每 30 秒扫描 `send_failed` 状态的任务，重试发送到 RabbitMQ：

```
T+0s    RabbitMQ 挂了 → 消息写表 (send_failed)
T+30s   定时扫描 → 重试 → 成功 → 状态改为 pending → 消费者消费
```

#### 4.7 面试追问预期

**Q: RabbitMQ vs Kafka vs RocketMQ 怎么选？**

> RabbitMQ：业务消息路由、Exchange 智能分发、Spring AMQP 一等公民、部署轻量 → 本场景最优。Kafka 面向海量日志/流计算，吞吐高但无优先级/死信原生支持。RocketMQ 擅长电商交易/分布式事务（半消息），部署重、非阿里系团队运维成本高。

**Q: 消息丢了怎么办？**

> 三层防护：① Publisher Confirm（消息到达 Queue 才返回）；② 幂等键（重复投递自动丢弃）；③ MySQL 事务回滚（JVM 崩溃 → 连接断开 → 未提交事务自动回滚）。

**Q: 为什么不用 WebSocket 直接推送任务完成通知？**

> 可以叠加——P2 阶段 WebSocket 推送任务完成事件，客户端收到后停止轮询。轮询是兜底方案。

---

### 5. 传感器数据监测 + InfluxDB 时序存储（规划）

#### 5.1 为什么用时序数据库

传感器数据特征：写入频率固定（每 60s）、数据只追加不修改、查询按时间范围、过期数据定期清理。MySQL 行存引擎对此效率低——大量 DELETE 产生表碎片、按时间范围扫描需全表、空间占用大。

InfluxDB 优势：
- **列式压缩**：浮点数序列压缩率 10×+，磁盘占用大幅降低
- **写入优化**：LSM-Tree 引擎，顺序追加写，吞吐远超 MySQL
- **自动降采样**：Continuous Query 定期将原始数据聚合为 1h/1d 粒度，查询时自动选最优精度
- **自动过期**：Retention Policy 按时间自动删除，无需手动 DROP PARTITION

#### 5.2 数据规模估算

```
100 路传感器 × 1 条/分钟 × 60 分钟 × 24 小时 × 365 天
= 100 × 1440 × 365
≈ 5,256 万条/年
```

每条 37 个维度，年增约 52 亿个数据点。

#### 5.3 数据分层策略

| 层级 | 粒度 | 保留周期 | 存储 | 用途 |
|------|------|----------|------|------|
| 热数据 | 原始（1min） | 7 天 | 内存缓存 | 实时监控面板 |
| 温数据 | 1h 聚合 | 90 天 | SSD | 趋势分析、异常回溯 |
| 冷数据 | 1d 聚合 | 365 天 | HDD/归档 | 审计合规 |

#### 5.4 Continuous Query（连续查询）

InfluxDB 的 CQ 类似 MySQL 的定时 GROUP BY，但由数据库引擎自动执行：

```sql
CREATE CONTINUOUS QUERY "cq_1h" ON "cams_sensors"
BEGIN
  SELECT mean(temperature), mean(humidity), mean(co2), ...
  INTO "cams_sensors"."rp_1h".:MEASUREMENT
  FROM "cams_sensors"."rp_raw"./.*/
  GROUP BY time(1h), *
END
```

每次 CQ 执行后，查询 1h 粒度数据时直接命中预聚合结果，而非扫描数百万行原始数据。

#### 5.5 面试追问预期

**Q: InfluxDB vs TDengine vs TimescaleDB？**

> InfluxDB：生态最成熟、K8s 部署友好、但集群版收费；TDengine：国产、单机性能极高（10× InfluxDB）、SQL 兼容好、超级表模型天然匹配传感器场景；TimescaleDB：基于 PG，适合已有 PG 技术栈的团队。选型取决于团队技术栈和是否需要集群。

**Q: InfluxDB 的存储原理？**

> TSM（Time-Structured Merge Tree）引擎：数据按 series key + time 排序存储，相同 series 的数据在磁盘上物理相邻，时间范围扫描是顺序读。写入先落 WAL 再刷 TSM 文件，宕机不丢数据。每个 shard 内的数据按列压缩——同一列的值变化小、差分编码 + 变长编码压缩率高。

**Q: 为什么不用 Elasticsearch 做时序？**

> ES 可以做，但索引开销大（倒排索引对时序数据无用）、写入吞吐不如 InfluxDB、聚合查询需要大量内存。ES 适合日志全文搜索，时序数据库专门优化了按时间范围聚合的场景。

---

### 6. AI 智能助手（RAG）

#### 6.1 为什么用 Function Calling 而不是自由文本

LLM 直接生成 SQL / JSON 是不可控的：字段名可能错、格式不稳定、甚至幻觉出不存在的表。Function Calling 把"能做什么"定义成受控的工具接口，模型只负责"决策调用哪个工具 + 传什么参数"，实际查询由代码执行，返回结构化 JSON 再交给模型组织语言。两轮调用链：

```
用户输入 → LLM 决策 tool_calls → 执行工具 → LLM 生成自然语言回复
```

#### 6.2 RAG 完整链路

```
① 文档切分：知识库按语义块切分（chunk）
② 向量化：embedding 模型将文本块转为向量
③ 入库：向量 + 原文存入向量库（Milvus / FAISS）
④ 检索：用户问题向量化 → 相似度检索 Top-K
⑤ 生成：检索到的文档块拼入 Prompt → LLM 生成带出处的回答
```

#### 6.3 面试追问预期

**Q: RAG 和微调怎么选？**

> 知识库频繁更新 → RAG：更新向量库即可，成本低、时效好、答案带出处可追溯。知识库稳定且需要模型"内化"领域术语/风格 → 微调。本场景设备手册、检测标准持续更新，选 RAG。

**Q: 检索不准怎么办？**

> 分块策略调优（语义块大小）、混合检索（向量 + 关键词 BM25）、召回后重排（rerank）、Prompt 里加"仅依据提供的文档回答，不知道就说不知道"约束幻觉。

**Q: 为什么不用定时任务生成日报，非要用 LLM？**

> 定时任务只能"到点触发"，日报的内容组织（哪些异常值得写、怎么表述、按什么优先级排序）靠 LLM 从原始数据中提炼，而不是硬编码模板拼字符串。LLM 的价值在"内容生成"，定时调度只是触发器。

---

## 四、系统架构总图

```
┌────────────────────────────────────────────────────────────────┐
│                         前端 Vue 3                              │
│   Dashboard │ 设备管理 │ Modbus面板 │ 传感器 │ AI助手 │ 日志查询 │
└──────────────┬─────────────────────────────────────────────────┘
               │ Nginx :10027 → :8080
┌──────────────▼─────────────────────────────────────────────────┐
│                    Spring Boot (CAMS)                           │
│                                                                 │
│  ┌─ 设备控制 ────┐  ┌─ Modbus模块 ─┐  ┌─ 传感器模块(cams-cgq) ┐│
│  │ EquipmentCtrl │  │ ModbusConv   │  │ SensorData            ││
│  │ + 多线程并发   │  │ Service      │  │ + MySQL分区(→InfluxDB) ││
│  │ + 快照回滚    │  │ 协议转换引擎  │  │ + 指令下发/ACK        ││
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────────────┘│
│          │                 │                  │                 │
└──────────┼─────────────────┼──────────────────┼─────────────────┘
           │                 │                  │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐  ┌───────────────┐
    │   MySQL     │  │  PLC 硬件   │  │ MySQL(分区)  │  │ Python AI 服务 │
    │  + Redis   │  │ 10.168.1.8  │  │ → InfluxDB   │  │ FastAPI        │
    │  + RabbitMQ│  │  :502       │  │   (规划)     │  │ + DeepSeek     │
    └─────────────┘  └─────────────┘  └──────────────┘  │ + RAG向量库    │
                                                         │   (规划)      │
                                                         └───────────────┘

数据流：
  HON9000 参数 → MySQL → RabbitMQ → Consumer → Modbus TCP → PLC
                                                ↓ 回读
                                   Redis Pub/Sub → WebSocket → 前端
  传感器模拟 → MySQL(分区) → API → 前端图表        (→ InfluxDB 规划)
  AI：自然语言 → DeepSeek Function Calling → 查询 DB → 回复   (RAG 规划)
```

---

## 五、常见面试问题速查

### Java 基础

- HashMap 底层原理，1.7 vs 1.8 区别（红黑树、尾插法）
- ConcurrentHashMap 为什么线程安全（分段锁 → CAS + synchronized）
- 线程池 7 参数 + 4 种拒绝策略 + 工作流程
- synchronized 锁升级（偏向锁 → 轻量级锁 → 重量级锁）
- volatile 可见性 + 禁止指令重排，DCL 单例为什么需要 volatile
- ThreadLocal 原理 + 内存泄漏（弱引用 key，强引用 value）
- JVM 内存模型（堆、栈、方法区、程序计数器）+ CMS/G1 区别

### Spring

- Spring AOP 原理（JDK 动态代理 vs CGLIB）+ 本类调用失效问题
- Spring 事务传播行为（7 种，重点 REQUIRED/REQUIRES_NEW/NESTED）
- Spring Bean 生命周期 + 三级缓存解决循环依赖
- Spring Boot 自动配置原理（@EnableAutoConfiguration → spring.factories）
- @Transactional 失效的 8 种场景（非 public、本类调用、异常被 catch、rollbackFor 未指定等）

### MySQL

- 索引底层（B+Tree） + 聚簇索引 vs 二级索引 + 回表
- 最左前缀原则 + 索引失效场景（函数、类型转换、LIKE %开头）
- 事务隔离级别 + MVCC 原理（undo log + ReadView）
- 间隙锁（Gap Lock）+ 临键锁（Next-Key Lock）+ 幻读解决
- SQL 优化套路（EXPLAIN、覆盖索引、分页优化）

### Redis

- 5 种基础数据结构 + 底层实现（SDS、ziplist、skiplist）
- 缓存穿透（布隆过滤器 + 缓存空值）/ 击穿（互斥锁 + 逻辑过期）/ 雪崩（随机 TTL + 多级缓存）
- Redis 持久化 RDB vs AOF + 混合持久化
- Redis 集群（主从 + 哨兵 + Cluster 分片）
- 分布式锁（SET NX EX + Redisson 看门狗 + 红锁争议）

### RabbitMQ

- Exchange 四种类型（Direct / Fanout / Topic / Headers）+ 路由规则
- Connection vs Channel 的区别和设计原因
- 消息可靠性：Publisher Confirm → 持久化 → Consumer ACK → 死信
- 重复消费怎么解决（幂等键）
- RabbitMQ vs Kafka 核心定位差异

### InfluxDB / 时序数据库（规划）

- 时序数据库的核心优化点（列式存储、时间排序、降采样、自动过期）
- InfluxDB Line Protocol + Tag vs Field 设计
- Continuous Query + Retention Policy 配合
- InfluxDB vs TDengine vs TimescaleDB 选型对比
- MySQL 分区表 vs 时序数据库的边界（什么时候必须换）

### AI / LLM / RAG

- Function Calling 原理（工具定义 → 模型决策 → 工具执行 → 二次生成）
- RAG 完整链路（文档切分 → 向量化 → 检索 → 增强生成）
- RAG vs 微调（知识库时效性、成本、可追溯性）
- 向量检索：embedding / 余弦相似度 / Top-K / 召回 vs 精排
- LLM 输出不可控的应对（结构化工具调用、受控 JSON）

---

> 📅 最后更新：2026-08-03
