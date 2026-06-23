# sky-server 后端服务模块说明

本模块是苍穹外卖系统的后端服务，基于Spring Boot构建，提供RESTful API接口供管理后台和用户端调用。

## 1. 技术栈

- Spring Boot 2.7.3
- Spring MVC
- Spring Data Redis
- MyBatis
- MySQL 5.7+
- Redis
- JWT (身份认证)
- Alibaba Druid (数据库连接池)
- PageHelper (分页插件)
- Lombok
- Knife4j (Swagger API文档)

## 2. 模块结构

```
sky-server
├── src/main/java/com/sky
│   ├── annotation     // 自定义注解
│   ├── aspect        // 切面编程
│   ├── config        // 配置类
│   ├── controller    // 控制器
│   ├── handler       // 异常处理器
│   ├── interceptor   // 拦截器
│   ├── mapper        // 数据访问层
│   ├── service       // 业务逻辑层
│   ├── task          // 定时任务
│   └── websocket     // WebSocket相关
├── src/main/resources
│   ├── mapper        // MyBatis映射文件
│   ├── application.yml      // 主配置文件
│   ├── application-dev.yml  // 开发环境配置
│   ├── application-test.yml // 测试环境配置
│   ├── application-prod.yml // 生产环境配置
│   └── logback-spring.xml   // 日志配置
└── base-sql
    └── sky_take_out.sql     // 数据库初始化脚本
```

## 3. 日志配置和多环境支持说明

## 1. Logback日志配置

### 日志特性：

1. 按日志级别分离日志文件（debug、info、warn、error）
2. 日志文件按日期和大小滚动
3. 不同环境使用不同的日志配置：
    - 开发环境（dev）：控制台输出 + 所有级别的日志文件
    - 测试环境（test）：控制台输出 + 所有级别的日志文件
    - 生产环境（prod）：仅输出到文件 + 只记录warn及以上级别

### 日志文件位置：

默认日志文件存储在项目根目录下的`logs`文件夹中。

## 2. 多环境配置

### 环境配置文件：

- 开发环境：`application-dev.yml`
- 测试环境：`application-test.yml`
- 生产环境：`application-prod.yml`

### 默认环境：

默认激活开发环境（dev）

## 3. 如何切换环境打包

### Maven命令切换环境：

1. 开发环境打包（默认）：

```bash
mvn clean package
```

2. 测试环境打包：

```bash
mvn clean package -Ptest
```

3. 生产环境打包：

```bash
mvn clean package -Pprod
```

### 在IDE中切换环境：

在IDE的Maven面板中，选择对应的Profile进行构建：

- dev（默认）
- test
- prod

## 4. 配置说明

### application.yml

主配置文件中使用占位符`@environment@`来动态指定当前激活的环境。

### 各环境配置文件

每个环境配置文件包含了该环境特定的配置，如数据库连接、Redis配置等。

## 5. 数据库初始化

项目提供了SQL脚本用于初始化数据库结构和基础数据：

- [sky_take_out.sql](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/base-sql/sky_take_out.sql) -
  包含完整的数据库表结构和基础数据

## 6. 图片资源初始化

项目包含预设的菜品和套餐图片资源：

- [base-image](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/base-image) - 包含所有菜品和套餐的示例图片

在部署应用时，需将这些图片复制到配置文件中指定的图片上传路径中：

- 开发环境默认路径: `E:/MyHome/project_asset/sky-take-out/uploads/images`
- 生产环境默认路径: `/var/project_asset/sky-take-out/uploads/images`

## 7. 启动方式

### IDE启动

1. 导入项目到IDE（IntelliJ IDEA推荐）
2.
打开 [SkyApplication.java](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/src/main/java/com/sky/SkyApplication.java)
3. 运行main方法

### Maven命令启动

```bash
cd sky-server
mvn spring-boot:run
```

### 打包部署

```bash
cd sky-server
mvn clean package
java -jar target/sky-server.jar
```

## 8. API文档

项目集成了Knife4j Swagger文档，启动服务后可通过以下地址访问：

- API文档地址：http://localhost:8080/doc.html
- 接口基准路径：http://localhost:8080

## 9. 默认账户

系统内置了默认管理员账户用于登录管理后台：

- 用户名：admin
- 密码：123456
