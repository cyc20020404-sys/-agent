
**权限隔离的具体实现**（全过程追踪）：

先看 Spring Boot 源码的真实情况：

```
Step 1. JWT 签发 — 里面没有 role 字段

  UserController.java (用户登录):
    claims = { "userId": 4 }
    -> JwtUtil.createJWT("itheima", ttl, claims)
    -> 返回给 H5 -> 存入 Vuex

  EmployeeController.java (管理员登录):
    claims = { "empId": 1 }
    -> JwtUtil.createJWT("yhans", ttl, claims)
    -> 返回给管理后台 -> 存入 localStorage

  JwtClaimsConstant.java 定义的字段只有: EMP_ID, USER_ID, PHONE, USERNAME, NAME

Step 2. 权限判断 — URL 路径模式，不是 role 鉴权

  WebMvcConfiguration.java:
    jwtTokenAdminInterceptor -> 拦截所有 /admin/**
    jwtTokenUserInterceptor  -> 拦截所有 /user/**

  逻辑很简单：能解析出 empId -> 有权访问 /admin/*
           能解析出 userId -> 有权访问 /user/*

  管理员和用户被建模为两套独立的后端子模块，不是 RBAC。
  这是一个学生项目的简化设计，生产系统通常会用一个 role 字段统一管控。

Step 3. FastAPI Agent 层的对接

  api/main.py: 根据 Header 名字判断来源（不是解析 JWT）
    "token" header          -> auth_type = "admin"
    "authentication" header -> auth_type = "user"

  ticket_handler.py 中根据 auth_type 走向不同的 if/else 分支。
```

**结论：这个项目没有实现 role-based access control。** 权限隔离靠的是 URL 路径拦截器模式——admin 和 user 各自独立 JWT 配置和拦截器，互不相通。后续可以升级为统一 RBAC 模型。

**面试可讲**："AI 客服作为中间服务，权限隔离依赖两层。展示层在 FastAPI 根据请求 Header 名字区分功能入口——消费者看不到管理端专属工具。安全兜底层在 Spring Boot——`/admin/**` 和 `/user/**` 各自有独立的 JWT 拦截器校验。即使 AI 层分流出错，下游拦截器也不会把用户和管理员数据互串。当前实现可以进一步升级为统一 RBAC——在 JWT 里加 role 字段，用单一密钥签发，由一个拦截器根据 role 统一判断权限。"
