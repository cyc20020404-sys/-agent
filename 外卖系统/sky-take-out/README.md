# 苍穹外卖 (Sky Take Out) 项目说明

本项目是一个基于Spring Boot + Vue的外卖管理点餐系统，包含管理后台、用户端（微信小程序）和后端服务三个主要模块。

## 项目结构

- `web-sky-admin`: 管理后台前端项目（基于Vue+TypeScript）
- `web-sky-weixin-uniapp`: 用户端微信小程序项目（基于UniApp）
- `mp-weixin`: 微信小程序编译后的静态文件
- `sky-server`: 后端服务项目（Spring Boot）

## 项目特点

1. **权限认证**：使用JWT实现管理员和用户的身份认证和权限控制
2. **缓存优化**：使用Redis缓存热门数据，提高系统性能
3. **文件存储**：支持本地文件存储菜品和套餐图片
4. **消息推送**：集成微信消息推送，实时通知用户订单状态
5. **数据统计**：提供营业数据统计功能，帮助商家分析经营状况
6. **多端适配**：一套后端API同时支持管理后台和用户端小程序
7. **接口文档**：集成Knife4j自动生成API文档，便于前后端协作开发

## 技术栈

### 后端技术栈
- Spring Boot
- Spring MVC
- Spring Data Redis
- MyBatis
- JWT
- Alibaba Druid
- PageHelper
- Lombok
- Knife4j (Swagger)
- MySQL
- Redis

### 管理后台前端技术栈
- Vue.js 2.x
- TypeScript
- Element UI
- Vue Router
- Vuex
- Axios
- Sass

### 用户端技术栈
- UniApp
- Vue.js
- JavaScript

## 启动流程

### 1. 后端服务启动

#### 环境要求
- JDK 1.8+
- Maven 3.6+
- MySQL 5.7+
- Redis

#### 配置步骤
1. 创建数据库并导入数据：
   - 创建名为 `sky_take_out` 的数据库
   - 执行数据库脚本文件 [sky_take_out.sql](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/base-sql/sky_take_out.sql)

2. 初始化图片资源：
   - 将 [base-image](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/base-image) 目录下的图片文件复制到配置文件中指定的图片上传路径中
   - 开发环境默认路径: `E:/MyHome/project_asset/sky-take-out/uploads/images`
   - 生产环境默认路径: `/var/project_asset/sky-take-out/uploads/images`

3. 修改数据库配置：
   - 在 [sky-server/src/main/resources/application-dev.yml](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/src/main/resources/application-dev.yml) 中修改MySQL连接信息
     ```yaml
     sky:
       datasource:
         host: localhost
         port: 3306
         database: sky_take_out
         username: root
         password: 123456
     ```

4. 修改Redis配置：
   - 在 [sky-server/src/main/resources/application-dev.yml](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/src/main/resources/application-dev.yml) 中修改Redis连接信息
     ```yaml
     sky:
       redis:
         host: localhost
         port: 6379
         password: 123456
         database: 1
     ```

#### 启动方式
1. 使用IDE启动：
   - 在IDE中打开 [SkyApplication.java](file:///E:/WorkSpace/back/2025/sky-take-out/sky-server/src/main/java/com/sky/SkyApplication.java) 文件
   - 直接运行main方法

2. 使用Maven命令启动：
   ```bash
   cd sky-server
   mvn spring-boot:run
   ```

服务默认运行在 `http://localhost:8080`

API文档地址：http://localhost:8080/doc.html

### 2. 管理后台启动

#### 环境要求
- Node.js 12.22.12

#### 安装依赖
```bash
cd web-sky-admin
npm install
```

#### 启动开发服务器
```bash
npm run serve
```

访问地址：http://localhost:80

#### 构建生产版本
```bash
npm run build
```

### 3. 用户端（微信小程序）启动

#### 方式一：使用HBuilderX运行到微信小程序（推荐）

1. 下载并安装HBuilderX
   - 访问[DCloud官网](https://www.dcloud.io/hbuilderx.html)下载HBuilderX开发工具
   - 安装HBuilderX及其相关插件

2. 导入项目到HBuilderX
   - 打开HBuilderX
   - 选择"文件" -> "导入" -> "从本地目录导入"
   - 选择项目目录下的 `web-sky-weixin-uniapp` 文件夹

3. 配置小程序AppID
   - 在项目根目录找到 [manifest.json](file:///E:/WorkSpace/back/2025/sky-take-out/web-sky-weixin-uniapp/manifest.json) 文件
   - 打开该文件，在"微信小程序配置"中填写您的小程序AppID

4. 运行到微信小程序
   - 点击HBuilderX顶部菜单栏"运行" -> "运行到小程序模拟器" -> "微信开发者工具"
   - 如果是首次运行，可能需要配置微信开发者工具的路径
   - 等待编译完成后，项目将自动在微信开发者工具中打开并运行

#### 方式二：使用微信开发者工具直接打开

1. 下载并安装微信开发者工具
2. 打开微信开发者工具
3. 导入项目目录下的 `mp-weixin` 文件夹
4. 配置小程序的appid（在[project.config.json](file:///E:/WorkSpace/back/2025/sky-take-out/web-sky-weixin-uniapp/project.config.json)中）
5. 点击编译即可预览
6. 调试基础库切换为2.0+
注意：小程序端需要后端服务正常运行才能完整使用各项功能。