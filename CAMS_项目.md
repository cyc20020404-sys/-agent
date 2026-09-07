# CAMS — 简历项目描述与面试知识点拓展

---

## 一、简历项目描述（精简版）

**风机系统管理平台（CAMS）**

面向洁净室的空调风机设备管理系统，主要负责空调指令控制、传感器数据监测两个核心模块。对接下游硬件通信规范，通过 MQTT/Modbus实现软件到 PLC 硬件的完整控制，基于传感器时序数据实现运维查询与智能告警。
技术栈：Vue 3 + Spring Boot + MySQL + Redis + RabbitMQ + InfluxDB + Docker + Python FastAPI。

- **多线程并发控制 + 快照回滚**：CompletableFuture + 自定义线程池实现多设备并发，响应 O(n)→O(max)；写前全量快照，中途失败逆序回滚已写点位；REQUIRES_NEW 事务隔离保证单台失败不影响其余

- **RabbitMQ 异步解耦**：请求秒返 taskId，Consumer 异步执行；Direct Exchange 按 AHU/VAV 独立路由；死信队列处理超时异常 + 钉钉告警；Redis SETNX 幂等防重

- **MQTT 通信与消息可靠性**：对接下游硬件设备 MQTT 协议，按 Topic 设计路由接收上报数据和下发指令；QoS + retained + 断线自动重连，保障通道稳定可靠。

- **传感器数据监测**：面向洁净室的空气质量实时监控与智能告警，采集温湿度、CO₂、洁净空气量（CADR）、滤网压力等指标；传感器数据定时同步至 InfluxDB 时序库，Continuous Query 自动降采样 + Retention Policy 分层存储

- **指令下发与 ACK 闭环**：指令先写库再发 MQTT，构建 ACK 状态机，定时 + 主动轮询双路判定执行结果，实现下发—执行—确认全链路闭环，消息不丢、可追溯。

---

### 对应技术实现与链路拆解

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

**已实现（InfluxDB + 预警引擎）**：InfluxDB 1.8（InfluxQL）已落地——`schema_influxdb.sql` 初始化三层 RP + 两级 CQ，`InfluxDBServiceImpl` 用 Line Protocol 写入 37 维数据；`AlertEngine` 三级判定预警引擎已实现。详见 5.6~5.10。

#### 5.6 InfluxDB Line Protocol 写入（拷打重点）

**InfluxDBServiceImpl.buildPoint() 组装的 Line Protocol**（一行一条时序数据）：

```
sensor_data,sensor_id=SN-001 temperature=23.5,humidity=55.2,co2=450,... 1712345678000000000
   ↑measurement(表名)  ↑tag(带索引)        ↑field(数值,无索引)              ↑时间戳(纳秒)
```

四个组成部分：

| 组成 | 含义 | 你代码里的取值 |
|------|------|---------------|
| **measurement** | 表名 | `sensor_data`（Point.measurement("sensor_data")） |
| **tag** | 索引维度，字符串，用于 WHERE 过滤 / GROUP BY | `sensor_id=SN-001` |
| **field** | 实际测量值，数值，用于聚合计算 | temperature / humidity / co2 / 37 维粒子计数 / 气流指标 |
| **timestamp** | 时间戳 | `m.getMeasuredAt()` 转 UTC 毫秒（`TimeUnit.MILLISECONDS`） |

**为什么 sensor_id 用 tag 不用 field**（面试高频）：
- 查询几乎都是"按传感器查"（`WHERE sensor_id='SN-001'`）。**tag 有索引**，按 tag 查是索引查找，快。
- 如果 sensor_id 写成 **field**：按传感器查询时 InfluxDB **没索引可用**，只能全库扫所有 field 值做过滤；且 field **不能用于 GROUP BY**，"按传感器分组聚合"都做不了。
- **经验规则**：经常用来过滤/分组的**低基数**字段放 tag，**数值测量**放 field。
- ⚠️ 别用 MySQL 的"回表"概念套 InfluxDB——field 不是"回表去查"，是**根本没索引**。tag 才有索引。

#### 5.7 三层 RP + 两级 CQ 逐级降采样（拷打重点）

**CQ（Continuous Query）≠ RP（Retention Policy）——两件事，别混**：

| | CQ 连续查询 | RP 保留策略 |
|---|---|---|
| 干什么 | **降采样**：把原始数据聚合成粗粒度（mean） | **保留时长**：每层数据留多久，到期自动删 |
| 你代码 | `cq_1h` / `cq_1d`：`SELECT mean(*) ... GROUP BY time(1h/1d)` | `rp_raw` 7d / `rp_1h` 90d / `rp_1d` 365d |

**为什么 RP 分三层**：原始数据精确但占空间，只留 7 天；降采样后的粗粒度数据占空间小，能留更久（90 天、365 天）。核心是**用空间换时间精度**——越老的数据越粗、越省空间，同时满足三种查询：实时看精确、历史看趋势、审计看一年。

**为什么 CQ 两级（raw→rp_1h→rp_1d）而不是一杆子 raw→rp_1d**：
- 逐级降采样，**每级都在更粗的源上再聚合**。
- 如果 raw→rp_1d 一杆子到底，等于对 7 天内所有原始点（1 分钟一个，10 万+点）直接算天均值；而 raw→rp_1h→rp_1d 是对 90 天的小时均值（最多 2160 个点）算天均值，**源数据量差两个数量级**。
- **逐级降 = 每层算的都是"上一层已经粗化过的数据"，又省空间又省算力**。

**`GROUP BY time(1h), *` 里的 `*` = 按所有 tag 分组，不是"全部列"**（面试必抠）：
- 你数据只有 `sensor_id` 一个 tag。`GROUP BY time(1h), *` = 先按 1 小时分桶，再在桶内按所有 tag 分组。
- **有 `*`**：SN-001 和 SN-002 在同一个小时桶里**各自算一个 mean**，每个传感器每小时一条。✅ 这是你要的。
- **没有 `*`**：同一个小时桶里所有传感器的值**混在一起算一个 mean**，SN-001 和 SN-002 的温度被平均成一坨。❌ 数据脏了。

**`./.*/` = 正则匹配"当前库所有 measurement"**：
- `./` = 当前数据库（cams_sensors），`.*` = 任意 measurement 名。
- 好处：以后新增 measurement 不用改 CQ，自动纳入。也可写成 `"cams_sensors"."rp_raw"."sensor_data"` 指定单一 measurement。

```sql
CREATE CONTINUOUS QUERY "cq_1h" ON "cams_sensors"
BEGIN
  SELECT mean(*) INTO "cams_sensors"."rp_1h".:MEASUREMENT
  FROM "cams_sensors"."rp_raw"./.*/
  GROUP BY time(1h), *      -- * = 按所有 tag 分组（保各 sensor 独立）
END;
```

#### 5.8 列式存储 + tag 基数陷阱（拷打重点）

**列式存储**：数据按"列"而不是按"行"连续存放。

```
行式(MySQL InnoDB):  行1:[SN-001,23.5,55.2,450] 行2:[SN-001,23.6,...]   ← 一行所有字段挨着
列式(InfluxDB):     temperature列:[23.5,23.6,23.4,...] humidity列:[55.2,...] ← 所有行同列挨着
```

为什么列式对时序有利（两个点）：
1. **压缩率高**：同一列类型相同、数值相近（温度都在 23 附近），InfluxDB 用差值编码 + 变长编码，存"23.5, +0.1, -0.2"这种差值，比原始浮点数省几十倍。行式相邻的是不同类型、无规律的数据，压不动。
2. **聚合快**：`SELECT mean(temperature)` 只碰 temperature 这一列，一次扫完；行式要读整行、把 temperature 从每行抠出来，读了大量用不上的字段。你的 CQ `SELECT mean(*)` 就是逐列算均值，列式天生快。

**tag 基数陷阱**（面试必抠）：**值"每个都不一样"的高基数字段绝不能放 tag**。
- 反例：原始测量值（温度 23.51、23.52...）、随机 UUID。如果当 tag，InfluxDB 要为每个不同值建一条索引、**常驻内存倒排索引**，几十万种值 → 内存直接爆。这就是官方说的 "high cardinality kills InfluxDB"。
- **判断规则**：值域小、可枚举、用来过滤/分组的放 tag（sensor_id、机房、设备类型）；值域大、连续变化的数值放 field。
- `time` 不是 tag 也不是 field，是独立的 timestamp 维度，不能当 tag。

#### 5.9 预警引擎 AlertEngine 三级判定（拷打重点）

`sensors.alarm_config`（JSON）里每个 metric 配 `min/max/durationSeconds/cooldownSeconds/enabled`。`AlertEngine.evaluate()` 对每条测量数据做三级判定：

```
① 阈值判断：value < min || value > max → 初步异常
② 毛刺过滤（duration / abnormalSince）：异常需持续 ≥ durationSeconds 秒才触发
③ 冷却去重（cooldown / lastAlertAt）：触发过一次后，cooldownSeconds 内不重复推送
```

| 判定 | 解决什么问题 | 用的状态 | 管什么 |
|------|-------------|---------|--------|
| **阈值判断** | 值超出 [min,max] 范围 → 初步异常 | 无 | 判断"是否超限" |
| **毛刺过滤** | 过滤"开门瞬间超阈值又立刻恢复"这类毛刺 | `abnormalSince`：sensorId:metric→首次异常时间 | **要不要开始告警**（持续够久才算异常） |
| **冷却去重** | 避免同一异常反复推送刷屏 | `lastAlertAt`：sensorId:metric→上次告警时间 | **要不要重复告警**（告警过就歇一会） |

**一句话记牢**：毛刺过滤管"要不要**开始**告警"，冷却管"要不要**重复**告警"。**别搞反**——这是最常见的答错点。

**内存态隐患（进程重启后果）**：两个 Map 都是内存态 `ConcurrentHashMap`，重启全清空，但后果方向**相反**：

| 状态 | 丢失后果 | 表现 |
|------|---------|------|
| `abnormalSince` 丢失 | 毛刺过滤**重新计时** | 传感器持续异常，重启后要再等满 durationSeconds 才告警 → **告警延迟** |
| `lastAlertAt` 丢失 | 冷却**失效** | 值仍异常时立刻再次告警，冷却期内本该被压住 → **重复告警** |

本质是"告警判定所需的时序状态没持久化"。生产环境应挪 Redis；cams-cgq 没引 Redis 先用内存态顶着——**主动说清这个 tradeoff 反而是加分项**。

#### 5.10 面试追问预期

**Q: 为什么 sensor_id 用 tag 不用 field？**
> 查询几乎都按传感器查，tag 有索引可 WHERE/GROUP BY；field 无索引、不能 GROUP BY，按传感器查会全表扫描。经验：低基数过滤字段放 tag，数值测量放 field。

**Q: 为什么 RP 分三层？CQ 是干嘛的？**
> RP 管保留时长（7/90/365 天），CQ 管降采样（mean 聚合）。分三层用空间换时间精度：原始数据精确但只留 7 天，越老越粗越省空间，同时满足实时精确/历史趋势/审计一年三种查询。CQ 是数据库自动执行的定时 GROUP BY。

**Q: `GROUP BY time(1h), *` 里的 `*` 和 `./.*/` 是什么意思？**
> `*` 是按所有 tag 分组，保证不同传感器在同一个小时桶内各自算 mean 不混；`./.*/` 是正则匹配当前库所有 measurement，新增表自动纳入 CQ。

**Q: 预警引擎三个判定用什么数据结构，各解决什么问题？**
> 阈值判断（值范围）→ 毛刺过滤（ConcurrentHashMap: abnormalSince，管要不要开始告警，持续够久才算异常）→ 冷却去重（ConcurrentHashMap: lastAlertAt，管要不要重复告警，告警过就歇一会）。

**Q: 进程重启后预警状态会怎样？**
> 两个 Map 都清空。abnormalSince 丢失→毛刺重新计时→持续异常告警延迟；lastAlertAt 丢失→冷却失效→重复告警。该状态生产应挪 Redis。

> **关键文件**：`schema_influxdb.sql`、`InfluxDBServiceImpl`、`AlertEngine`、`SensorController`、`SensorDataSyncJob`、`SensorCommandController`、`PartitionMaintenanceJob`、`SensorDataGenerator`

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

### 7. MQTT 通信与消息可靠性（cams-cgq，Eclipse Paho）

**模块定位**：传感器（上行上报）+ 指令下发（下行）的 MQTT 通信层。传感器每 60s 上报 37 维数据、回 ACK、发心跳/遗嘱；系统向传感器下发控制指令。对应简历 bullet「MQTT 通信与消息可靠性」。

**Topic 设计与路由**（`MqttProperties` + `MqttInboundHandler`）：

| Topic | 方向 | 作用 | QoS |
|-------|------|------|-----|
| `data/${sensorId}` | 上行 | 测量数据落库（MySQL + InfluxDB + 告警） | 0 |
| `ack/${sensorId}` | 上行 | 指令 ACK 回填 | 1 |
| `status/${sensorId}` | 上行 | 在线状态（online 心跳 / offline 遗嘱）+ 自动注册 | 0 |
| `cmd/${sensorId}` | 下行 | 下发控制指令（CSV 文本） | 1 |

`MqttInboundHandler` 按 **Topic 第一段路由**：`messageArrived` 里 `topic.substring(0, indexOf('/'))` 取前缀，switch 到 handleData / handleAck / handleStatus。

**① QoS 语义（面试必抠，最容易记反）**：

| QoS | 语义 | 机制 | 代价 |
|-----|------|------|------|
| **QoS0** | **at most once**（最多一次） | 发出去不管，丢了就丢 | 无，最快 |
| **QoS1** | **at least once**（至少一次） | 收不到 PUBACK 就重发，**可能重复** | 低 |
| **QoS2** | **exactly once**（恰好一次） | 四次握手（PUBREC/PUBREL/PUBCOMP），不丢**也不重** | 高，多两轮握手 |

**指令为什么用 QoS1 不用 QoS2**：QoS2 多两轮握手，延迟和吞吐吃亏；而指令即使 QoS1 重复投递，**也不会执行两次**——`sensor_commands` 有 `uk_sensor_cmd` 唯一索引 + cmdId 幂等兜底，重复的指令被识别为"同一 cmdId"。**QoS2 唯一的"不重复"优势已被业务幂等兜住**，所以 QoS1 够用还省开销。

**② retained（补收最后一条指令）+ expires（防过期执行）**：
- retained：Broker 保存该 Topic 最后一条 retained 消息，**新订阅者 / 断线重连重订阅**时主动推送，不用等重新发布。
- 场景：传感器断线重连 → 重新 subscribe `cmd/${sensorId}` → 收到最后一条 retained 指令 → 补收执行。
- **隐患**：补收的指令可能已过期。靠 `SensorCommand.expires` + `isExpired()` 判断，过期就丢弃。**retained 补收 + expires 防过期执行**是一组配合，不是摆设。

**③ 两套断线重连（面试必抠，看似冗余实则兜底）**：

| 重连机制 | 负责什么 | 不覆盖什么 |
|---------|---------|-----------|
| Paho `setAutomaticReconnect(true)` | **连接建立过之后**断线自动重连，重连后自动恢复订阅 | 首次连接失败 |
| 自研 `@Scheduled(fixedDelay=15000)` 的 `reconnect()` | **首次连接失败 / broker 晚于应用启动**时主动 connect() | —— |

**为什么两套都要**：Paho 的 automaticReconnect 只在"之前连上过、后来断了"才自动重连；**应用启动时 broker 还没就绪、第一次 connect() 抛异常，Paho 不自动重试**。所以自研定时任务每 15s 主动 connect() 兜住"从没连上"的洞。`connect()` 异常只 `log.warn` 不抛——**首次连接失败不阻断应用启动**，靠定时任务在后面兜。

**④ cleanSession=true 的取舍**：
- `cleanSession=true`：不保存会话，断开后 broker 丢弃订阅和离线消息，重连是全新会话需重新订阅。
- 对 `data/#` 数据上报：离线时 broker 丢弃 data 消息。**可接受**——数据周期上报，丢一条只是少一个快照，下轮还来。
- 对 ACK 链路：离线时回的 ACK 可能丢，但已用"先落库 + 定时/主动轮询"兜底，`pollPendingAcks` 会发现指令一直是 pending，靠 expires/timeout 收场，不会永久卡死。
- **为什么选 true**：避免 broker 为每个离线客户端无限累积高频消息撑爆内存。用 cleanSession 换内存，用业务幂等兜底。

**⑤ Topic 通配符 `#` vs `+`（面试必抠）**：
- `#` 匹配**任意多层**（含 0 层）；`+` 匹配**正好一层**。
- 你订阅 `data/#`、`ack/#`、`status/#`。当前协议是 `data/SN-001` 单层，`#` 和 `+` 都能匹配。
- **为什么选 `#`**：意图是"前缀下所有消息都收"，`#` 更宽松，以后扩展成 `data/SN-001/metric` 两层也不用改订阅。代价是精确性（会误收更深层）。诚实答法：协议固定单层用 `+` 更严谨，选 `#` 是"前缀语义 + 扩展性"的设计选择。

**⑥ LWT 遗嘱 vs 数据超时（两层兜底，面试必抠）**：
- **LWT（Last Will）**：设备连接时登记遗嘱，**设备异常断线（掉电/断网/崩溃）时 broker 主动发布**。抓的是**连接级**异常。
- **LWT 盲区**：**设备进程还活着、MQTT 连接还挂着，但传感器已经不采集数据了**（固件卡死、采集线程挂掉、硬件故障但网络正常）——broker 收不到断开，LWT 永不触发，但数据确实停了。
- **数据超时兜底**：`SensorDataSyncJob` 里 `Duration.between(lastSeen, now).getSeconds() > offlineTimeoutSeconds(90)` 判离线。
- **为什么 90s**：上报周期 60s，阈值必须明显大于一个周期避免误判，90s > 60s 留一轮余量。经验法则：离线阈值 ≈ 上报周期 × 1.5~2。
- **一句话**：LWT 抓"连接断了"，数据超时抓"连接没断但数据停了"，两层互补，都要。

> **关键文件**：`MqttClientManager`（生命周期）、`MqttInboundHandler`（上行路由）、`MqttGateway`（下行发布）、`MqttProperties`（Topic/QoS 配置）、`SensorDataSyncJob`（离线判定）

---

### 8. 指令下发与 ACK 闭环（cams-cgq）

**模块定位**：下发控制指令给传感器，并追踪设备是否执行成功，形成"下发—执行—确认"闭环。对应简历 bullet「指令下发与 ACK 闭环」。核心在 `SensorCommandServiceImpl`。

**① 完整链路**：

```
1. SensorCommandController 收请求 → sendCommand()
2. @Transactional：校验传感器存在 → 解析 command{op,expires,flags,arg,cmdId} → 组装 SensorCommand
3. 落库 sensor_commands（status=pending）→ 拿到 cmdId → 组下行 CSV
4. 事务提交后（afterCommit）→ MqttGateway.publishCommand() 发到 cmd/${sensorId}
5. 设备收到执行 → 回 ack/${sensorId} → MqttInboundHandler.handleAck() → 回填 ACK 状态
6. 状态机 pending → acked / failed / expired / timeout
```

**② 为什么先落库再发 MQTT（面试必抠）**：
1. **先持久化**：MQTT 挂了指令不丢，可补偿重试。
2. **必须先落库才有 cmdId**：cmdId 是 `nextCmdId`（MAX+1）从数据库来的，下行 CSV 第 2 字段就是 cmdId——**没有 cmdId 就没法组 CSV、没法发 MQTT**。落库在逻辑上必须先于发布（依赖关系，不只是为了安全）。

**③ afterCommit 竞态（代码里最精华的一处，必考）**：
- 不能"落库后立刻发"，必须**事务提交后再发**（`TransactionSynchronization.afterCommit()`）。
- **为什么**：对瞬时响应类指令（STOP_MEASURE / SET_PM_POWER），设备毫秒级回 ACK。若在事务提交前就发 MQTT，并发 ACK 线程 `findBySensorIdAndCmdId` 按 MySQL 默认隔离级别（REPEATABLE READ）**读不到尚未提交的指令行** → 误判"未知指令的 ACK"而丢弃 → **ACK 丢失**。
- 所以：**等事务提交 → 再发 MQTT → 设备回 ACK 时行已可见 → 正确回填**。

**④ ACK 状态机（pending 是起点，4 个终态）**：

```
                 ┌─ 上行 ACK status=OK   → acked
                 ├─ 上行 ACK status≠OK   → failed
pending ─────────┤
                 ├─ expires 已过         → expired
                 └─ ackPollCount ≥ 60    → timeout
```

| 终态 | 到达路径 | 对应代码 |
|------|---------|---------|
| **acked** | 上行 `ack/${sensorId}` 且 status=OK | `handleAck()` 设 "acked" |
| **failed** | 上行 ACK 且 status≠OK | `handleAck()` 设 "failed" |
| **expired** | 轮询时发现 `expires` 已过 | `doPollAck()` → `isExpired()` |
| **timeout** | 轮询计数 ≥ MAX_ACK_POLL_COUNT(60) | `doPollAck()` → ackPollCount |

⚠️ **pending 是起点不是终态**——别把它当"到达的状态"列进去。

**⑤ 定时 + 主动双路判定（简历原文，必考）**：

| 路径 | 触发 | 职责 |
|------|------|------|
| **定时** `pollPendingAcks()` | `@Scheduled(fixedDelay=30000)` | **状态机收敛兜底**：即使没人查，也把 pending 推进到 timeout/expired，ACK 永远不来也不会卡死 |
| **主动** `pollAck()` | 用户调 API | **即时反馈**：查一下立刻触发判定，不用等 30s 定时器 |

**为什么两条都要**：
- **缺了定时**：ACK 永远不来（传感器丢了指令）时，指令永远 pending、卡死。定时是"没人管也要自己收敛"的可靠性兜底。
- **缺了主动**：用户点"查 ACK"要多等最多 30s 定时器才看到结果，体验差。主动是"有人要结果就立刻给"的即时反馈。
- 一条管**兜底**，一条管**体验**，不是重复。

**⑥ cmdId 生成：MAX+1 + 唯一索引 + 乐观重试（面试必抠）**：

```java
int maxRetry = 5;
for (int i = 0; ; i++) {
    command.setCmdId(sensorCommandMapper.nextCmdId(sensorId));  // SELECT COALESCE(MAX(cmd_id),0)+1 WHERE cloud_sensor_id=?
    try { sensorCommandMapper.insert(command); break; }
    catch (DuplicateKeyException e) { if (i >= maxRetry - 1) throw e; }  // 撞号重新生成再试
}
```

- **cmdId 是协议域整数**：进 CSV 被设备解析、ACK 要带回。**不能**用数据库自增（全局一条龙，跨传感器跳号、失去"设备内指令计数"的协议语义）或 UUID（字符串，设备没法解析）。
- **"按传感器分组"不是存储隔离**：数据都在同一张 `sensor_commands` 表，靠 `WHERE cloud_sensor_id=?` 过滤出"这台设备的 MAX" + `uk_sensor_cmd(sensor_id, cmd_id)` 复合唯一索引兜底。
- **为什么不用锁**：synchronized 只对单 JVM 有效（多实例要分布式锁），且串行化损失并发。MAX+1 + 唯一索引 + 乐观重试**不用锁、几乎不损失并发**，撞了再试（概率低、代价小）。
- ⚠️ 诚实边界：如果固件协议只要求"cmdId 整数 + 每传感器唯一、不要求连续递增"，全局自增 + 复合唯一索引也能跑；MAX+1 是为了贴合"设备内递增指令计数"的协议语义。

> **关键文件**：`SensorCommandServiceImpl`（sendCommand / handleAck / doPollAck / pollPendingAcks）、`SensorCommandMapper`（nextCmdId / findBySensorIdAndCmdId）、`MqttGateway`、`MqttInboundHandler`、`SensorDataSyncJob`（定时轮询）

#### 1.4 面试追问预期

**Q: "回读校验"具体怎么做的？**

> 写入后立即读取同一寄存器地址，对比写入值与回读值。回读成功返回真实值；回读失败（超时/异常）不影响主流程，仅记录日志。真实值优先于目标值返回给前端。

**Q: 如果 PLC 返回的值跟你写的不一样怎么办？**

> 可能的场景：PLC 内部有限幅逻辑（比如最大值钳位到 80%），或者寄存器被其他系统同时修改了。当前策略是以回读值为准返回，不做自动重试——因为不知道差异原因，盲目重试可能造成振荡。差异记录到 command_log 供运维排查。

**Q: max_airflow 怎么来的？**

> 存储在 `modbus_ahu_devices.max_airflow`，默认 4000 m³/h（代码里 `getMaxAirflow() == null ? 4000.0`），可按设备单独配置。不同的 AHU 型号最大风量不同，写成配置项而非硬编码。

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

### 5. 传感器数据监测 + InfluxDB 时序存储

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
│  │ + 多线程并发   │  │ Service      │  │ + MySQL+InfluxDB(CQ/RP)││
│  │ + 快照回滚    │  │ 协议转换引擎  │  │ + MQTT通信/指令ACK闭环 ││
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────────────┘│
│          │                 │                  │                 │
└──────────┼─────────────────┼──────────────────┼─────────────────┘
           │                 │                  │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐  ┌───────────────┐
    │   MySQL     │  │  PLC 硬件   │  │ MySQL +      │  │  MQTT Broker  │
    │  + Redis   │  │ 10.168.1.8  │  │ InfluxDB(已) │  │  (EMQX)       │
    │  + RabbitMQ│  │  :502       │  │ CQ+RP 分层   │  │ data/ack/     │
    └─────────────┘  └─────────────┘  └──────────────┘  │ status/cmd    │
                                                         └───────┬───────┘
                                                               │ 传感器
数据流：
  HON9000 参数 → MySQL → RabbitMQ → Consumer → Modbus TCP → PLC
                                                ↓ 回读
                                   Redis Pub/Sub → WebSocket → 前端
  传感器 MQTT(data/status/ack) → MySQL + InfluxDB(CQ/RP) → API → 前端图表
  指令下发：落库 → afterCommit → MQTT cmd/ → 设备回 ack/ → ACK状态机闭环
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

## 六、问题研究（架构深挖，拷打时追问出来的）

> 这一节记录面试拷打中被追问出来的、文档正文没完全展开的架构问题与答案。简历先不改，先沉淀研究结论。

### 问题 1：控制下发——"同步线程"和"异步 MQ"到底怎么分工？

**一条下发逻辑，两条触发入口。**

下发指令的**核心逻辑只有一份**：`DeviceControlProcessor.processOne()`。它被两条路径共同调用：
- **同步线程路径**：`EquipmentControlServiceImpl.control()` → 每台设备 `CompletableFuture.supplyAsync(processOne, executor)` → 同步等结果 → 返回 `partialFailureList`
- **异步 MQ 路径**：`ControlTaskConsumer.onMessage()` → `processOne()` → 手动 ACK

**前端"点下发"实际走哪条？——同步线程路径。**

前端只有两个下发入口（都走同步）：
| 前端页面 | 调的方法 | HTTP 路径 | 后端 Controller |
|---|---|---|---|
| BatchControlView | `openApi.controlEquipmentStates` | `POST /openApi/v1/buildings/{id}/controlEquipmentStates` | `CamsController`（source=cams_api） |
| DeviceDetailView | `deviceApi.control` | `POST /admin/buildings/{id}/control` | `EquipmentStateController`（source=admin_web） |

**`/control/async`（MQ 异步）在后端已实现，但前端目前没有调用**——grep 前端只有 `controlEquipmentStates` 和 `deviceApi.control`，无 `controlAsync`。所以 MQ 异步是"能力就绪、待业务接入"的备选方案，不是当前主力。

**两条路径的区别**（业务场景相同：都是下发指令）：
| | 同步线程 | 异步 MQ |
|---|---|---|
| 返回 | 同步等全部结果，返回 partialFailureList | 立即返回 taskId，后台执行 |
| 触发 | 手动批量、要即时看结果 | 耗时/批量大/外部系统触发/要可靠投递 |
| 可靠性 | 无重试死信（当场知道成败） | 死信 + 补偿 + SETNX 幂等 |
| 适用 | 管理后台手动操作 | 外部系统调用、告警联动、定时调度 |

> **一句话**：不是"MQ 不是下发"，而是"同一份 processOne 被同步线程和异步 MQ 两条路径按不同触发场景各自调用"。面试别把两者说成互斥的两套功能。

**关键修正：对"运维手动下发"这个当前真实场景，同步不仅不是缺方案，而是语义正确的选择——MQ 反而不合适。**

同步路径的**结果即语义**：processOne 每个 future 的返回值本来就是"这台设备成没成"，同步路径让这个结果**零额外成本**流到调用方——运维点一下，当场看到 `AHU-01 成功 / VAV-101 失败:值超出范围`。

MQ 异步要拿到同样结果，得**刻意回传**一条完整闭环：
- 消费端执行完 → 写回 `control_tasks.status = completed + result`
- 调用方轮询 `GET /control/tasks/{taskId}` 去捞
- 或再加 MQ 回执 / WebSocket 通知"被通知"而非"去查"

**同一份结果，同步是"顺手给"，异步是"刻意回传"——画蛇添足。** 且手动下发请求量极低（运维点按钮），MQ 的削峰优势完全用不上。**判据：调用方是人且要即时结果 → 同步；调用方不是人 / 量大不能等 / 跨模块解耦 → MQ。** 手动下发属前者，所以前端走同步是正确设计，不是"MQ 没接上"的缺憾。

**最干净的结论（同步 vs 异步的两判据，面试用它开头）**：
> 同步还是异步，就看两点——**① 业务能不能接受"先给受理状态、结果让 MQ 消费后慢慢给"**；**② 量级有没有大到必须削峰**。
> - **CAMS 手动下发**：两个都指向同步——不接受"先受理再查"（运维要当场知道这台设备成没成），量级又小到线程池全程空闲。所以同步是两判据同时指向的答案，不是妥协。
> - **电商下单**：两个都指向异步——点击给受理凭证 orderId 就够（支付结果本来就是后查的），量级大到不削峰线程池必炸。

**别被电商反例将死**：电商的 orderId 是"受理凭证"，订单行其实**同步落库**、下游（库存/支付/通知）才走 MQ；CAMS 要的是"这台设备成没成"这个**最终结果**，且量级小能全同步。同一原则，分界线位置由两判据决定——量级一旦变大（上千台+多运维并发+要留痕审计），CAMS 手动下发也会退化成电商模式：接口同步只写 control_tasks 拿 taskId，设备逐台挪 MQ 分队列慢消费。

---

### 问题 2：MQ 异步解耦能用在哪些真实业务场景？（前端未接，需有支撑场景）

现状：MQ 异步代码是完整闭环（生产/消费/幂等/死信/补偿全有），但前端没接 `control/async`。简历写"RabbitMQ 异步解耦"必须有**一个真实场景**支撑，否则面试官追问"这套代码在跑什么业务"会露馅。贴合 CAMS 的场景：

**① 外部系统 / 边缘服务器触发控制（最贴）**：`CamsController` 的 openApi 路径是给外部系统（HON9000 边缘服务器、第三方上位机）调的。外部系统**不能同步等 30s+**，应秒回 taskId 后台执行。`source="cams_api"` 已区分调用方，外部系统把 URL 换成 `/control/async` 即可全部复用。

**② 告警联动自动调节（跨模块解耦，最能讲故事）**：预警引擎 `AlertEngine` 检测到 CO₂ 超标 → 自动调大新风。告警是传感器模块（cams-cgq）发的，控制是 cams-backend 的，**跨模块同步调用会把采集延迟拖进控制链路**。用 MQ：告警发消息 → 控制消费者异步接收 → 复用 `processOne` 执行。这就是"报警即处置"的自动闭环。

**③ 定时 / 调度控制**：洁净室有固定运行计划（8:00 切 autoOn、18:00 切 autoOff、按班次切 filter）。定时任务后台自动触发，没有前端等结果，MQ 的**任务表 + 状态机 + 死信 + 补偿**正好把"这次调度下发了几台、哪台失败、原因"完整留痕审计。

**④ 大批量设备集中下发（削峰）**：一个区域上百台设备统一调参，同步线程池（core=16, max=32, 队列200）扛不住、前端挂几分钟。MQ 秒回 + 后台消费 + 消息持久化（服务重启不丢），天然削峰。

> **面试主线建议**：挑场景①（跨系统必须异步，理由硬）或场景②（把告警+MQ+控制串成闭环，最能展示架构，还能带出 AlertEngine）。

---

### 问题 3：下发指令的顺序怎么保证？

**当前代码有没有保证？——没有显式保证，MQ 恰好有序是"默认巧合"。**

| 路径 | 是否有序 | 原因 |
|---|---|---|
| MQ 异步 | ✅ 恰好有序（非设计保证） | `application.yml` 只配 `manual ACK + prefetch:1`，没配 concurrency → Spring AMQP 默认 **1 线程串行消费** → 同队列 FIFO |
| 同步线程 | ❌ 不保证 | 两次独立请求，同一设备进不同 CompletableFuture/线程，可能并发、顺序不定 |
| cmdId | ⚠️ 递增但不等于执行序 | `MAX+1` 保证数字递增，不代表先发的先执行完 |

> **隐性地雷**：MQ 现在的"有序"靠默认单消费者。一旦未来配 `concurrency: N`（多线程消费），同一设备的多条消息立即乱序。

**关键修正：单条控制会在 Modbus 层裂变成多条写指令，但仍是"单线程串行"消化。**

上面表格说"同步路径不保证"，但**同一请求内**的顺序其实有更深一层：一个 item（一台设备的一次控制）在 `ModbusConversionService.convertAndExecute()` 里**裂变成多条 PLC 写**——`writeSwitches()` 写 4 个开关线圈（FC=5）+ for 循环写 4 个开度寄存器（FC=6），一条"手动调 AHU-01"≈ **8 条 Modbus 写**。

**但这些裂变指令全在 processOne 的同一个线程里串行 for 循环执行**：
```
processOne (CompletableFuture 线程 T)
 └─ convertAndExecute
     ├─ writeSwitches → 4× writeCoil      串行 for
     └─ for regWrites → 4× writeRegister  串行 for
```
没有多线程竞争、没有线程池调度，就一个线程顺序执行。顺序 = **程序顺序（program order）**：先全部开关、再全部开度。

**为什么 JMM 重排不了它**：as-if-serial 语义不允许重排这两个调用——它们都有外部副作用（往 PLC 发字节、写 command_log），"先写开关"≠"先写开度"（可观察结果不同），编译器无法证明它们独立，不能重排；CPU 层前一个**阻塞 socket 写未返回**，后续指令根本不在执行流里。

**这个"先开关后开度"是刻意语义**：先建立通断状态（预位/上电），再写入设定值（幅度）；autoOff 是"开关全 OFF + 开度归 0"，必须先断开再清幅度。先后语义写死在源码顺序里。

**真正的顺序风险只在跨请求**：两个并发请求各起一个 processOne，并行写同一批寄存器——这才是未保序、后写覆盖的缺口（`regWrites` 循环里失败只记日志不回滚，见 `convertAndExecute` ⑤，连补偿都没有）。此时才需要问题 4 的 seq + 设备级锁。

**五种保序方案对比**：

| 方案 | 保序粒度 | 并行度 | 资源 | 复杂度 | CAMS 适配 |
|---|---|---|---|---|---|
| ① 每设备单线程池 | 设备 | 高 | 随设备数膨胀 | 低 | 设备多时偏高 |
| ② 条纹化线程池 | 设备 | 中 | **固定 N** | 中 | ✅ 同步路径推荐 |
| ③A 每设备队列 | 设备 | 高 | 队列爆炸 | 高 | ❌ |
| ③B 单队列单消费者 | 全局 | 无 | 低 | 低 | ✅ 当前默认，写死 concurrency=1 |
| ③C 哈希分 K 队列 | 分区 | 中 | 固定 K | 中高 | ✅ MQ 并行保序 |
| ④ Redis 锁 | 设备(互斥非序) | 中 | 低 | 低 | ⚠️ 只互斥不保序 |
| ⑤ 严格串行 | 全局 | 无 | 低 | 低 | 一般不 |

- **② 条纹化**：`int idx = (deviceId.hashCode() & 0x7fffffff) % N; pool[idx].submit(task)`，同一设备 hash 到同池有序，N 固定线程数可控。
- **③C MQ 哈希分区**：生产者 `routingKey = equipmentType + deviceId.hash()%K`，同一设备固定进同一队列（单消费者）即有序，不同设备分布到 K 队列并行。这是 Kafka 分区思想在 RabbitMQ 的落地。
- **④ Redis 锁**：只保证"同一设备不同时执行"（互斥），**不保证顺序**（谁先抢到锁谁先跑），别当保序方案用。

> **面试话术**：当前 MQ 恰好有序是默认单消费者，不算设计保证。真要保序，同步用条纹化（N 调大控损失），MQ 把 routingKey 改成 equipmentType + deviceId hash 分 K 队列、每队列单消费者。

---

### 问题 4：保序 vs 并行——为什么是零和？（条纹化 tradeoff）

**核心结论：你不能既让"同一设备严格有序"又让"所有设备全并行"，因为同一设备的两条指令同时执行就没有顺序可言。保序 = 串行 = 放弃对应并行度。**

**两种"排队"，性质不同**：
| 排队来源 | 例子 | 是损失吗 |
|---|---|---|
| 同一设备的多次操作 | 一个请求两次改 AHU-01 | ❌ **必要代价**——保序本来就要串行 |
| 不同设备 hash 撞同一池 | AHU-01、AHU-02 都进 pool[2] | ✅ **无谓损失**——这俩不需保序却串行 |

**响应时间量化**（3 台各 300ms，N=8，AHU-01/AHU-02 撞 pool[2]）：
```
原始全并行：3 台各进线程，响应 = max(300,300,300) = 300ms
条纹化：   pool[2]: AHU-01→AHU-02(600ms)  pool[5]: VAV-101(300ms)
           响应 = max(600,300) = 600ms   ← 变长
```
撞池的那几台响应 = **耗时之和**，整体响应从 max 退化成"每个池内耗时的最大和"。

**N 是旋钮**：N 越大，异设备撞池概率越低（≈设备数/N），但线程越贵。同设备撞同池后的串行**躲不掉**（保序本质就是串行），条纹化能减少的只是"异设备被误伤"那部分。

**更优解：per-device 队列 + 共享 worker 池**（想"异设备全并行 + 同设备串行"时）：
```java
// 每设备一个串行队列（保序容器）
ConcurrentHashMap<String, BlockingQueue<Runnable>> perDeviceQueue;
// 每设备一个执行许可，保证同设备同时只出一个任务
ConcurrentHashMap<String, Semaphore> perDevicePermit;   // permit = 1
```
同一设备任务进它自己的队列，靠 semaphore=1 保证同时刻只执行一条 → 串行保序；不同设备各有队列 → 互不阻塞可并行。**代价：实现复杂**（管队列、许可、worker 唤醒、关闭），所以工程上很多人宁可用条纹化接受折中。

> **工程判断（面试可讲）**：绝大多数设备间无依赖，用全并行拿 max 响应；只有同一设备确实需要保序时才串行——用条纹化（N 调大）或 per-device 队列。条纹化的坑是异设备 hash 撞池被误伤串行，所以 N 不能太小。

---

### 问题 5：同步线程路径——从请求到返回的完整执行链路（含返回）

把真实代码 `EquipmentControlServiceImpl.control()` + `DeviceControlProcessor.processOne()` 从进到出完整过一遍，含主线程/工作线程分工、超时、返回汇总。

**入口**（前端真实走的同步路径）：
```
前端 POST /openApi/v1/buildings/{id}/controlEquipmentStates
  → CamsController（source=cams_api）
  → EquipmentControlServiceImpl.control(buildingId, request, source)
```

**主线程（请求线程）——只做编排，不做并发**：
1. 主线程**同步校验建筑**：`selectById` + 检查 `active` → 这一步不需要并发，先保证 building 合法
2. 校验 `equipmentStates` 非空
3. 为**每个 item** 建 `CompletableFuture.supplyAsync(() -> processOne(...), executor)` 提交到线程池
4. `CompletableFuture.allOf(futures).get(30, SECONDS)` 等全部完成（或超时）

**线程池 `executor`（deviceControlExecutor）**：
- core=CPU×2 / max=CPU×4 / `LinkedBlockingQueue(200)` / `CallerRunsPolicy`
- 每个 item 一个任务 → 工作线程并发执行 `processOne`
- 队列满时 CallerRunsPolicy 让主线程自己跑 → 主线程也会变成"执行者"之一，天然限流

**每个工作线程 `processOne`（`@Transactional(REQUIRES_NEW)` 独立事务）**——逐台设备、独立事务，单台失败只回滚自己。九步逐段拆解（核心代码来自 `DeviceControlProcessor.java`）：

> 注解：`@Transactional(propagation = Propagation.REQUIRES_NEW, rollbackFor = Exception.class)` → 挂起外层事务（如有），每台设备开全新独立事务；一台成功即提交一台，单台失败不影响其他。

**① 参数校验**
```java
if (equipmentId == null || equipmentId.isEmpty()) throw new BusinessException(400, "equipmentId 不能为空");
if (equipmentType == null || !VALID_TYPES.contains(equipmentType)) throw new BusinessException(400, "无效的 equipmentType: " + equipmentType);  // VALID_TYPES = {AHU, VAV}
if (operations == null || operations.isEmpty()) throw new BusinessException(400, "operations 不能为空");
```

**② 确认设备已注册 + 类型匹配**
```java
Device device = findDeviceByEquipmentId(buildingId, equipmentId);  // WHERE building_id=? AND equipment_id=? AND status='active'
if (device == null) throw new BusinessException(400, "设备未注册: " + equipmentId);
if (!equipmentType.equals(device.getEquipmentType())) throw new BusinessException(400, "设备类型不匹配: 请求=" + equipmentType + ", 实际=" + device.getEquipmentType());
```

**③ 白名单 + 只读校验（`validateOperations`）**
```java
Object modeObj = operations.get("airflowControlMode");
if (modeObj == null) throw new BusinessException(400, "缺少 airflowControlMode 参数");
String mode = String.valueOf(modeObj);
if (!VALID_MODES.contains(mode)) throw ...;            // VALID_MODES = {autoOn, autoOff, filter}
Map<String, Set<String>> typeMap = FIELD_WHITELIST.get(mode);   // mode → (type → 允许字段集)
Set<String> allowedFields = typeMap.get(equipmentType);
for (String field : operations.keySet()) {
    if ("airflowControlMode".equals(field)) continue;
    if (READ_ONLY_FIELDS.contains(field)) throw ...;   // 只读：oaAirVelocity / saAirflow
    if (!allowedFields.contains(field)) throw ...;      // 不在该 mode 白名单
}
```
`FIELD_WHITELIST` 是静态结构：`mode → equipmentType → 允许字段集合`。例：`autoOn` 下 AHU 只允许 `minOaAirflowSetpoint`、VAV 只允许 `minSaAirflowSetpoint`；`filter` 下 AHU 允许 `fixedOaAirflowSetpoint / raDamperPositionSetpoint / saFanSpeedSetpoint / eaAirflowSetpoint / eaFanSpeedSetpoint`。**校验在写库之前做，非法请求直接抛错，绝不落库**。

**④ 获取当前状态（快照旧值用）**
```java
EquipmentState state = findStateByDeviceId(device.getId());   // WHERE device_id=?
if (state == null) throw new BusinessException(500, "设备状态记录不存在: " + equipmentId);
Map<String, Object> stateData = state.getStateDataMap();      // equipment_states.state_data 整个 JSON
```

**⑤ 逐字段更新 `equipment_states` + 收集变更明细**
```java
for (Map.Entry<String, Object> op : operations.entrySet()) {
    String fieldName = op.getKey();
    if ("airflowControlMode".equals(fieldName)) continue;     // mode 单独第⑥步处理
    Object oldValueObj = stateData.get(fieldName);            // 旧值（写日志用）
    String jsonPath = "$." + fieldName;                        // JSON path 定位
    equipmentStateMapper.updateStateField(device.getId(), jsonPath, toJsonString(newValue));  // MySQL JSON_SET
    changes.add(new LinkedHashMap<>(){{ put("fieldName",fieldName); put("oldValue",oldValueStr); put("newValue",newValueStr); }});
}
```
**核心**：`updateStateField` 用 MySQL 的 **`JSON_SET` 只更新 JSON 里的单字段**（`$."fieldName"`），不是整行覆盖——并发多字段不互相踩。`toJsonString()` 对字符串做引号转义，防止 JSON 注入破坏结构。`changes` 收集每个字段的 old/new 供合并日志用。

**⑥ 更新 `airflowControlMode`（mode 单独落）**
```java
if (operations.containsKey("airflowControlMode")) {
    equipmentStateMapper.updateStateField(device.getId(), "$.airflowControlMode", toJsonString(modeValue));
    // 若⑤没收集到变更，这里补一条 mode 变更进 changes
}
```

**⑦ 写一条合并日志**
```java
ModificationLog log = new ModificationLog();
log.setDeviceId(device.getId()); log.setEquipmentId(equipmentId); log.setSource(source);
log.setChanges(changes);                     // 本次所有字段 old→new 明细
log.setRequestBody(requestBody); log.setResponseBody(Collections.singletonMap("partialFailureList", Collections.emptyList()));
log.setApiStatus("success");
modificationLogMapper.insert(log);           // 一条日志汇总整台设备本次全部变更，不逐字段碎日志
```

**⑧ Redis Pub/Sub 推送变更事件**
```java
try {
    String topic = "cams:state:" + buildingId;
    redisTemplate.convertAndSend(topic, objectMapper.writeValueAsString(pushMsg));  // 只发 {equipmentId, buildingId, timestamp}
} catch (Exception ignored) { /* 推送失败不影响主流程 */ }
```
**推拉结合**：消息体只发变更事件（equipmentId + buildingId + timestamp），**不带具体值**——前端收到后调 API 拉最新权威数据。推送丢了几条不致命（软实时），前端 F5 即可。

**⑨ 【Modbus 融合】下发到 PLC**
```java
Long modbusDeviceId = device.getModbusDeviceId();
if (modbusDeviceId != null) {
    try {
        String mode = operations.containsKey("airflowControlMode") ? String.valueOf(operations.get("airflowControlMode")) : null;
        if (mode != null) modbusConversionService.convertAndExecute(modbusDeviceId, equipmentType, mode, operations);
    } catch (Exception e) {
        modbusLogger.warn("Modbus 硬件写入失败: equipmentId={}, error={}", equipmentId, e.getMessage());  // 不回滚 equipment_states
    }
}
```
**关键边界**：Modbus 写入失败**只 log.warn、不回滚 equipment_states**——软件状态和硬件是两套，软件状态已提交成功，硬件下发失败留给运维排查，不能因为 PLC 没写上把已经对的 DB 也回滚。`convertAndExecute` 内部：先 `writeSwitches`（4 开关线圈 FC=5）、再 for `regWrites`（4 开度寄存器 FC=6），单线程串行、程序顺序保序。

**返回阶段（回到主线程）**：
1. `allOf.get(30s)`：超时抛 `TimeoutException` → 被 catch，未完成任务后面单独记
2. 遍历所有 future 汇总 `partialFailureList`：**只收非 null = 失败**（成功返回 null）
3. **future 未 done（超时）** → 记 `{errorCode: "TIMEOUT", message: "设备处理超时"}`
4. 返回 `{ partialFailureList }` → 前端展示"AHU-01 成功 / VAV-101 失败：值超出范围"

**四种结果形态**：
| 场景 | future 返回 | 是否进 partialFailureList |
|---|---|---|
| 成功 | `null` | ❌ 不入列（null = 无失败标记） |
| 校验失败（BusinessException） | Map `VALIDATION_ERROR` + failedParameters | ✅ |
| 未知异常 | Map `INTERNAL_ERROR` | ✅ |
| 30s 超时 | future 未 done | ✅ 记 TIMEOUT |

**线程安全来源**：`processOne` **无成员变量**，全部数据在方法局部变量（栈上私有，线程隔离）；每台设备操作不同 DB 行 → MySQL 行级锁天然不冲突。**无需锁**。

**为什么用 CompletableFuture 而非 CountDownLatch**：CountDownLatch 只能等 N 个线程就绪/完成，**拿不到每个线程的返回值**；CompletableFuture 泛型是 `Map<String,Object>`，能携带失败信息用于汇总 partialFailure。这是选它的核心理由。

### 问题 6：设备状态数据模型统一——点位值表作为唯一权威

#### 6.1 痛点：两套状态模型数据不一致

改造前系统里有两套"设备状态"各管各的，互相不通：

| 存储 | 存什么 | 谁写 | 谁读 |
|---|---|---|---|
| `equipment_states.state_data` | **HON9000 参数**（airflowControlMode、各设定值） | `processOne`（同步路径，DB 权威） | 前端**参数业务视图** |
| `modbus_ahu_points` | 点位**配置**（地址/类型），**不含当前值** | 建表种子 | 面板读实时值要**实时读 PLC** |
| `modbus_ahu_point_values`（**新增**） | 点位**当前值**（权威） | `convertAndExecute` + `batchWrite` | 面板 `listWithValues` + 参数视图 |

**一致性 bug**：Modbus 面板 `batchWrite` 写 PLC + 记 `command_logs`，但**不更新任何 DB 状态** → 面板把 PLC 风阀开到 80%，前端参数页还显示旧值。`convertAndExecute`（processOne 调它）换算点位后**只写 PLC、不落库**，软件层对硬件到底到没到没有记录。

**统一结论**：点位表和参数必须"同一起来"——新建 `modbus_ahu_point_values` 表作为**唯一权威**，所有写路径落它、所有读路径读它，前端永远一致。**DB 权威 + 补偿机制**（呼应问题 5 的边界：软件状态已提交，硬件尽力而为）。

#### 6.2 建表（唯一权威）

```sql
CREATE TABLE modbus_ahu_point_values (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id   BIGINT      NOT NULL COMMENT 'FK modbus_ahu_devices.id',
    point_code  VARCHAR(50) NOT NULL COMMENT '逻辑标识',
    point_value VARCHAR(50) COMMENT '点位当前值(权威)：开关 true/false，开度 0-100 int',
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pv_device_point (device_id, point_code)   -- 一个设备一个点位只一行，upsert 用
) ENGINE=InnoDB COMMENT='AHU Modbus 点位当前值(统一权威)';
```

#### 6.3 关键语义：DB 权威值不依赖 PLC 成败

这是整个设计能离线测、且和"DB 权威 + 补偿"自洽的核心：

> `point_value` 存的是 **DB 权威值（命令意图/换算目标）**。PLC 写不写、连不连得上，**都先落库**；PLC 成败只记 `command_logs`。PLC 离线时前端看到的仍是 DB 一致状态，PLC 恢复后由回读/补偿收敛到实际。

- `convertAndExecute`（改造前第 ② 步 `connect` 失败直接 return）→ 改为**先 `computeTargets` 算出目标值 → `persistPoints` 落库 → 再尝试连 PLC 写**。PLC 连不上只 `log.warn` + 记失败日志，不再提前退出、不再丢落库。
- `batchWrite`：先记快照（从 `point_values` 读权威值），逐条 `doWrite` 成功 → `upsertValue` 新值；中途失败 → 逆序回滚，把已成功点位的 `point_values` **恢复为快照**（硬件写回 + DB 权威值一并还原，方向一致）。

#### 6.4 换算逻辑（HON9000 → 点位）

`ModbusConversionService.convertAndExecute` 复用 `AHU_RULES` 换算表，三种换算类型：

```java
PERCENT_DIRECT:  result = val;                        // RA 开度直通（1:1，单位一致）
AIRFLOW_TO_PERCENT:  result = (val / maxAirflow) * 100;   // 风量 m³/h → 开度 %
AIRFLOW_TO_PERCENT_SPLIT: result = (val / maxAirflow) * 100 / 2;  // 双路均分
```

`computeTargets(mode, operations, maxAirflow, regWrites)` 按 `airflowControlMode` 分派：
- `autoOff`：全关（开关 OFF + 所有开度 0）
- `autoOn`：平衡（OA=进风基准，SA=OA，RA=OA×0.7，新风 50）
- `filter`（手动）：按 operations 逐字段换算写 regWrites

落库调用：
```java
private void persistPoints(Long deviceId, boolean switchesOn,
        Map<String, Integer> regWrites, Map<String, AhuPoint> pointMap) {
    for (String sc : ALL_SWITCHES) if (pointMap.containsKey(sc))
        persistPointValue(deviceId, sc, String.valueOf(switchesOn));  // "true"/"false"
    for (Map.Entry<String,Integer> e : regWrites.entrySet()) if (pointMap.containsKey(e.getKey()))
        persistPointValue(deviceId, e.getKey(), String.valueOf(e.getValue())); // "23"/"60"/...
}
```

`AhuPointValueMapper.upsertValue` 用唯一键去重：
```java
@Insert("INSERT INTO modbus_ahu_point_values (device_id, point_code, point_value) "
      + "VALUES (#{deviceId}, #{pointCode}, #{pointValue}) "
      + "ON DUPLICATE KEY UPDATE point_value = VALUES(point_value)")
int upsertValue(@Param("deviceId") Long deviceId, ...);
```

#### 6.5 读路径统一（PLC 离线也能一致）

**`AhuPointServiceImpl.listWithValues`**（面板 loadPoints，改造前 PLC 连不上直接抛 500）→ 改为：
1. 先从 `modbus_ahu_point_values` 读 DB 权威值；
2. 再 `tryConnect` 尝试连 PLC 回读刷新（尽力而为，**离线跳过**）；
3. PLC 可连时回读成功 → 用实际值覆盖并 `upsertValue` 刷新权威值。

**`EquipmentStateServiceImpl.queryEquipmentStates`**（参数视图）：对绑定了 `devices.modbus_device_id` 的 AHU 设备，把 `modbus_ahu_point_values` 当前值合并进 `currentEquipmentState` 的嵌套 `modbusPoints` 对象，类型还原（`true/false`→Boolean，数字→int/double）：
```java
Map<String, Object> modbusPoints = loadModbusPoints(modbusDeviceId);
if (!modbusPoints.isEmpty()) currentState.put("modbusPoints", modbusPoints);
```

#### 6.6 为什么不做"点位反算回参数"（反向映射）

`minOaAirflowSetpoint` / `fixedOaAirflowSetpoint` **两个参数都映射到 `damper_oa_percent`**，且取决于 mode——从点位反推回参数是**有损/不确定**的。所以不强行反算，而是**两个投影都保留**：
- 参数意图留 `equipment_states.state_data`（该到哪）
- 点位实际值放 `modbus_ahu_point_values`（实际到哪）

参数视图两个都展示 → 前端既看"该到哪"又看"实际到哪"，**面板改完参数页天然一致**，还多了一层可观测性。

#### 6.7 实测验证（PLC 离线，验证 DB 一致性）

环境：AHU-01 绑定 `modbus_device_id=2`，PLC 经内网穿透 `27bh18jy5636.vicp.fun:49415`（`modbusClient.connect` 失败，硬件写不进去）。

① **HON9000 控制路径落库**（`POST /openApi/.../controlEquipmentStates`，mode=filter）：
```json
{"partialFailureList":[]}
```
`modbus_ahu_point_values` 落库（换算正确）：
```
damper_oa_percent=23   ← fixedOaAirflowSetpoint=900, max_airflow=4000 → (900/4000)*100=22.5→23
damper_ra_percent=60   ← raDamperPositionSetpoint 直通
damper_sa_percent=20   ← saFanSpeedSetpoint=800 → 20
fresh_air_percent=50   ← filter 固定
damper_*_switch=true   ← 开关全开
```

② **参数视图合并 modbusPoints**（`GET .../getCurrentEquipmentStates?equipmentId=AHU-01`）：
```json
"modbusPoints": {"damper_oa_percent": 23, "damper_oa_switch": true,
  "damper_ra_percent": 60, "damper_ra_switch": true,
  "damper_sa_percent": 20, "damper_sa_switch": true,
  "fresh_air_percent": 50, "fresh_air_switch": true}
```

③ **autoOff 全关**再触发 → 参数视图即时一致：
```json
"modbusPoints": {"damper_oa_percent": 0, "damper_oa_switch": false, ... 全部 0 / false}
```

④ **`listWithValues` PLC 离线读 DB**（面板点位列表，改造前 500）→ 现正常返回 DB 权威值。

⑤ **`batchWrite` 离线不污染 DB**：PLC 连不上在连接处失败，`point_value` 保持原值（未被改成 80），DB 不被脏写。

#### 6.8 面试追问预期

- **为什么落库不依赖 PLC 成败？** DB 是审计权威 + 补偿基准（呼应问题 5 的边界：软件状态已提交成功，硬件下发失败留给运维排查，不能因为 PLC 没写上把对的 DB 也回滚）。离线也要能跑、能测、前端一致。
- **batchWrite 回滚和 HON9000 补偿方向一致吗？** 一致——都是"以 DB 权威值为准，硬件尽力写回"。`batchWrite` 中途失败把成功点位的 DB 权威值恢复为快照 + PLC 逆序写回，方向是回滚到旧值；`processOne`/`convertAndExecute` 是补偿到新值（DB 权威）。方向相反但基准相同：**都是 DB 说了算**。
- **为什么面板点位级写也能和参数页统一？** 因为 `batchWrite` 也 upsert 进 `modbus_ahu_point_values`，参数视图读同一个表 → 天然一致。这就是"一个系统一个设计"。
- **点位数 vs 参数是两个投影，会不会冗余？** 会有一点冗余，但这是**刻意**的：反向映射有损（同一点位对两个参数），所以保留命令意图投影 + 点位实际投影，物理统一存在 DB，换取前端一致和可观测。
- **量表很大怎么办？** `(device_id, point_code)` 唯一键 + 单点一行，一个设备点位几十个，量级很小；真到海量设备可按 building_id 分片/归档，此处 YAGNI。

---

> 📅 最后更新：2026-09-04（问题 6：设备状态数据模型统一——新增 `modbus_ahu_point_values` 唯一权威表，convertAndExecute/batchWrite 落库、listWithValues/参数视图从 DB 读，PLC 离线实测 DB 一致性通过）
