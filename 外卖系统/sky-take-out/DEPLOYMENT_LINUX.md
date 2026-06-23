# Linux服务器部署文档

本文档详细介绍了如何在Linux服务器上部署Sky-Take-Out项目，包括环境准备、应用打包、数据库配置及服务启动等步骤。

## 1. 环境准备

### 安装JDK 8
```bash
# 更新软件包列表
sudo yum update -y

# 安装OpenJDK 8
sudo yum install -y java-1.8.0-openjdk-devel

# 验证安装
java -version
javac -version
```

### 安装MySQL 8
```bash
# 下载MySQL官方仓库
wget https://dev.mysql.com/get/mysql80-community-release-el7-3.noarch.rpm
sudo rpm -ivh mysql80-community-release-el7-3.noarch.rpm

# 安装MySQL
sudo yum install -y mysql-server

# 启动MySQL服务
sudo systemctl start mysqld
sudo systemctl enable mysqld

# 获取临时密码
sudo grep 'temporary password' /var/log/mysqld.log

# 运行安全配置向导
sudo mysql_secure_installation
```

### 安装Redis
```bash
# 安装EPEL仓库
sudo yum install -y epel-release

# 安装Redis
sudo yum install -y redis

# 启动Redis服务
sudo systemctl start redis
sudo systemctl enable redis
```

### 安装Nginx
```bash
# 安装Nginx
sudo yum install -y nginx

# 启动Nginx服务
sudo systemctl start nginx
sudo systemctl enable nginx
```

## 2. 开启防火墙端口

```bash
# 开启常用端口
sudo firewall-cmd --permanent --add-port=80/tcp    # HTTP
sudo firewall-cmd --permanent --add-port=443/tcp   # HTTPS
sudo firewall-cmd --permanent --add-port=3306/tcp  # MySQL
sudo firewall-cmd --permanent --add-port=6379/tcp  # Redis
sudo firewall-cmd --permanent --add-port=8080/tcp  # 应用服务

# 重载防火墙配置
sudo firewall-cmd --reload

# 查看开放的端口
sudo firewall-cmd --list-all
```

## 3. 前端项目打包(web-sky-admin)

### 修改生产环境配置
在打包前需要修改前端项目的生产环境配置文件，将后端服务地址改为实际的服务器IP地址：

1. 编辑 [.env.production](file:///E:/WorkSpace/back/2025/sky-take-out/web-sky-admin/.env.production) 文件：
   ```bash
   cd web-sky-admin
   vi .env.production
   ```

2. 修改以下配置项为您的服务器IP地址：
   ```
   # 修改为您的服务器IP地址和端口
   VUE_APP_URL = 'http://你的服务器IP:8080/admin'
   VUE_APP_SOCKET_URL = 'ws://你的服务器IP:8080/ws/'
   ```

### 打包前端项目
```bash
# 安装依赖
npm install

# 打包生产环境
npm run build
```

### 部署前端资源到Nginx
```bash
# 复制打包后的文件到Nginx目录(注意是sky) 可通过ftp上传
sudo cp -r dist/* /usr/share/nginx/html/sky/

# 配置Nginx反向代理
sudo vi /etc/nginx/nginx.conf
```

在nginx.conf中添加以下配置:
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    client_max_body_size 200m;

    sendfile        on;
    keepalive_timeout  65;


    map $http_upgrade $connection_upgrade{
		default upgrade;
		'' close;
    }

    upstream webservers{
	  server 192.168.1.104:8080 weight=90 ;
	  #server 127.0.0.1:8088 weight=10 ;
    }

    include /etc/nginx/conf.d/*.conf;

    server {
        listen       80;
        server_name  192.168.1.104;

        location / {
            root   /usr/share/nginx/html/sky;
            index  index.html index.htm;
        }

        #error_page  404              /404.html;

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }

        # 反向代理,处理管理端发送的请求
        location /api/ {
            proxy_pass   http://192.168.1.104:8080/admin/;
        }
		
		# 反向代理,处理用户端发送的请求
        location /user/ {
            proxy_pass   http://webservers/user/;
        }
		
		# WebSocket
		location /ws/ {
            proxy_pass   http://webservers/ws/;
			proxy_http_version 1.1;
			proxy_read_timeout 3600s;
			proxy_set_header Upgrade $http_upgrade;
			proxy_set_header Connection "$connection_upgrade";
        }
    }
}




```

重启Nginx:
```bash
sudo systemctl restart nginx
```

## 4. 后端项目打包(sky-server)

### 构建JAR包
```bash
# 进入sky-server目录
cd sky-server

# 使用Maven构建生产环境JAR包（可通过maven插件勾选后package，记得跳过测试）
mvn clean package -Pprod
```

### 创建部署目录
```bash
sudo mkdir -p /opt/www/sky-take-out

将sky-server.jar上传到部署目录（可通过ftp上传）
/opt/www/sky-take-out/
```

## 5. 数据库配置

### 导入SQL脚本
```bash
# 登录MySQL
mysql -u root -p

# 创建数据库（一下可通过navicat远程连接）
CREATE DATABASE sky_take_out CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 退出MySQL并导入SQL文件
exit
mysql -u root -p sky_take_out < base-sql/sky_take_out.sql
```

## 6. 配置文件调整

### 修改生产环境配置
```bash
# 编辑生产环境配置文件
sudo vi /opt/www/sky-take-out/application-prod.yml
```

确保以下关键配置正确:
```yaml
sky:
  datasource:
    host: localhost
    port: 3306
    database: sky_take_out
    username: sky_user
    password: your_password  # 替换为您设置的实际密码
  redis:
    host: localhost
    port: 6379
    # 如果设置了密码需要配置password字段
```

## 7. 部署静态资源

### 导入图片资源
```bash
# 创建图片存储目录
sudo mkdir -p /var/project_asset/sky-take-out/uploads/images

# 复制base-images中的图片到指定目录（可通过ftp上传）
sudo cp -r base-image/* /var/project_asset/sky-take-out/uploads/images/

# 设置权限
sudo chown -R nginx:nginx /var/project_asset/sky-take-out
```

## 8. 启动服务

### 启动Java应用
```bash
# 使用nohup启动应用
nohup java -jar /opt/www/sky-take-out/sky-server.jar --spring.profiles.active=prod > /dev/null 2>&1 &

# 查看进程
ps -ef | grep sky-server
```

### 设置开机自启(可选)
创建systemd服务文件:
```bash
sudo vi /etc/systemd/system/sky-server.service
```

添加以下内容:
```ini
[Unit]
Description=Sky Take Out Server
After=syslog.target network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/www/sky-take-out
ExecStart=/usr/bin/java -jar sky-server.jar --spring.profiles.active=prod
SuccessExitStatus=143
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sky-server
sudo systemctl start sky-server
```

## 9. 验证部署

1. 检查各服务运行状态:
   ```bash
   sudo systemctl status mysql
   sudo systemctl status redis
   sudo systemctl status nginx
   ps -ef | grep sky-server
   ```

2. 检查端口监听:
   ```bash
   netstat -tlnp | grep -E ':(80|443|3306|6379|8080)'
   ```

3. 访问应用:
   - 前端管理界面: `http://你的服务器IP`
   - 后端API接口: `http://你的服务器IP:8080`

默认管理员账号:
- 用户名: admin
- 密码: 123456

## 10. 故障排除

如果遇到问题，请检查以下几点：

1. 查看应用日志：
   ```bash
   tail -f /var/project_asset/sky-take-out/logs/*.log
   ```

2. 确认所有服务都在运行：
   ```bash
   sudo systemctl status mysqld
   sudo systemctl status redis
   sudo systemctl status nginx
   ```

3. 检查防火墙规则是否正确配置

4. 确认前端配置中的后端服务地址是否正确

至此，Sky Take Out项目已在Linux服务器上部署完成。