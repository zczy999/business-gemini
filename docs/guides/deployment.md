# Business Gemini Pool 项目分析与部署指南

## 📋 项目概述

**Business Gemini Pool** 是一个基于 Flask 的 Google Gemini Enterprise API 代理服务，主要功能包括：

- ✅ **多账号轮训管理**：支持配置多个 Gemini 账号，自动轮训使用
- ✅ **OpenAI 兼容接口**：提供与 OpenAI API 完全兼容的接口格式
- ✅ **流式响应**：支持 SSE (Server-Sent Events) 流式输出
- ✅ **图片处理**：支持图片输入和输出（AI 生成的图片）
- ✅ **Web 管理控制台**：美观的 Web 界面，支持明暗主题切换
- ✅ **代理支持**：支持 HTTP/HTTPS 代理配置
- ✅ **JWT 自动管理**：自动获取和刷新 JWT Token
- ✅ **账号冷却机制**：智能处理账号限流和错误，自动冷却
- ✅ **Cookie 自动刷新**：每30分钟自动检查过期 Cookie，使用临时邮箱自动登录刷新

## 🏗️ 项目结构

```
business-gemini-pool-main/
├── gemini.py                          # 后端服务主程序（Flask应用）
├── templates/                         # HTML 模板目录
│   ├── index.html                    # Web 管理控制台
│   ├── chat_history.html             # 聊天记录页面
│   └── login.html                    # 登录页面
├── business_gemini_session.json       # 配置文件（运行时生成，主要用于备份）
├── requirements.txt                   # Python 依赖
├── Dockerfile                         # Docker 镜像构建文件
├── docker-compose.yml                 # Docker Compose 配置
├── README.md                          # 项目文档
├── docs/                              # 文档目录
└── image/                             # 图片缓存目录（自动创建）
└── video/                             # 视频缓存目录（自动创建）
```


## 🐧 Linux 部署指南

### 方式一：直接运行（推荐用于开发/测试）

#### 1. 环境要求

```bash
# Python 3.7+ （推荐 3.8+）
python3 --version

# pip 包管理器
pip3 --version
```

#### 2. 安装依赖

```bash
# 进入项目目录
cd business-gemini-pool-main

# 安装 Python 依赖
pip3 install -r requirements.txt

# 安装 Playwright 浏览器（用于 Cookie 自动刷新）
playwright install chromium

# 或者使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
playwright install chromium
```

#### 3. 启动服务

```bash
# 直接运行
python3 gemini.py

# 或者后台运行
nohup python3 gemini.py > gemini.log 2>&1 &

# 或者使用 systemd（见下方）
```

系统会自动：
- ✅ 创建数据库文件 `geminibusiness.db`
- ✅ 初始化数据库表结构
- ✅ 生成管理员密钥（如果不存在）

#### 4. 访问服务

- Web 管理控制台：`http://your-server-ip:8000/`
- API 接口：`http://your-server-ip:8000/v1/...`
- 健康检查：`http://your-server-ip:8000/health`

### 方式二：使用 Docker（推荐用于生产环境）

#### 1. 安装 Docker 和 Docker Compose

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose -y

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker-compose --version
```

#### 2. 构建和启动

```bash
# 构建镜像并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重新构建镜像（代码更新后）
docker-compose up -d --build
```

#### 3. 端口配置

如果需要修改端口，编辑 `docker-compose.yml`：

```yaml
ports:
  - "8001:8000"  # 将主机端口 8001 映射到容器端口 8000
```

或通过环境变量：

```yaml
environment:
  - SERVER_PORT=8001
```

#### 4. 更新配置

通过 Web 管理界面修改配置，或使用配置导入/导出功能。

### 方式三：使用 Systemd 服务（推荐用于生产环境）

> **注意**：如果使用命令行参数（如 `--port`、`--host`），需要在 systemd 服务文件中更新 `ExecStart` 命令。

#### 1. 创建 systemd 服务文件

```bash
sudo nano /etc/systemd/system/business-gemini-pool.service
```

#### 2. 添加服务配置

```ini
[Unit]
Description=Business Gemini Pool Service
After=network.target

[Service]
Type=simple
User=your-username  # 替换为你的用户名
WorkingDirectory=/path/to/business-gemini-pool-main  # 替换为实际路径
Environment="PATH=/path/to/venv/bin:/usr/local/bin:/usr/bin:/bin"  # 如果使用虚拟环境
ExecStart=/path/to/venv/bin/python /path/to/business-gemini-pool-main/gemini.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. 启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start business-gemini-pool

# 设置开机自启
sudo systemctl enable business-gemini-pool

# 查看状态
sudo systemctl status business-gemini-pool

# 查看日志
sudo journalctl -u business-gemini-pool -f
```

### 防火墙配置

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8000/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## 🖥️ Cookie 自动刷新模式配置

Cookie 自动刷新功能使用 Playwright 浏览器执行登录流程。根据运行环境不同，需要配置合适的浏览器模式。

### 模式说明

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **有头模式** | 浏览器可视化运行，能看到操作界面 | macOS 本地开发、调试问题 |
| **无头模式** | 浏览器后台运行，无界面 | Linux 服务器、Docker 容器 |

### macOS 本地开发

macOS 默认使用**有头模式**（可视化），无需额外配置：

```bash
# 直接启动，默认有头模式
python gemini.py

# 如需强制无头模式（例如后台运行）
python gemini.py --headless
```

### Linux 服务器部署

Linux 系统会**自动检测**是否有图形界面（通过 `DISPLAY` 环境变量）：

- 有图形界面（`DISPLAY` 有值）→ 使用有头模式
- 无图形界面（`DISPLAY` 为空）→ 使用无头模式

```bash
# 自动检测模式（推荐）
python gemini.py

# 强制无头模式（确保在无图形界面服务器上运行）
python gemini.py --headless

# 强制有头模式（调试用，需要 X11 转发或 VNC）
python gemini.py --headed
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--headless` | 强制使用无头模式，忽略系统检测结果 |
| `--headed` | 强制使用有头模式（优先级高于 `--headless`） |

### 环境变量

也可以通过环境变量配置，适用于 Docker 或 systemd 部署：

| 环境变量 | 值 | 说明 |
|----------|-----|------|
| `FORCE_HEADLESS` | `1` | 强制无头模式 |
| `FORCE_HEADED` | `1` | 强制有头模式（优先级更高） |

**优先级顺序**：`FORCE_HEADED` > `FORCE_HEADLESS` > 命令行参数 > 系统自动检测

### Docker 部署配置

在 `docker-compose.yml` 中设置：

```yaml
environment:
  - FORCE_HEADLESS=1  # Docker 容器无图形界面，强制无头模式
```

### Systemd 服务配置

在服务文件中添加环境变量：

```ini
[Service]
Environment="FORCE_HEADLESS=1"
# 其他配置...
```

### 调试 Cookie 刷新问题

如果 Cookie 刷新失败，可以临时使用有头模式观察浏览器行为：

```bash
# macOS 或有图形界面的 Linux
python gemini.py --headed
```

然后在 Web 控制台手动触发刷新，观察浏览器操作过程。

## 🔄 远程同步与主从部署

当你有多台服务器时，可以使用**主从部署**模式：一台 macOS 主控端负责刷新 Cookie，自动同步到多台 Linux 服务器。

### 部署架构

```
┌─────────────────────┐                    ┌─────────────────────┐
│   macOS 主控端       │                    │   Linux 服务器 A     │
│   (Cookie 刷新机)    │    Cookie 同步      │   (只接收同步)       │
│                     │ ──────────────────→ │                     │
│ • 执行 Cookie 刷新   │                    │ • sync_only_mode    │
│ • 有头模式便于调试    │                    │ • 无头模式运行       │
│ • 配置远程同步 URL   │                    │ • 提供 API 服务      │
└─────────────────────┘                    └─────────────────────┘
                        │
                        │ Cookie 同步
                        ↓
                ┌─────────────────────┐
                │   Linux 服务器 B     │
                │   (只接收同步)       │
                └─────────────────────┘
```

### macOS 主控端配置

1. **启用 Cookie 自动刷新**（Web 控制台 → 系统设置）

2. **配置远程同步**：
   - `remote_sync_url`: 服务器地址，如 `https://server-a.example.com`
   - `remote_sync_api_key`: 服务器的管理员密钥

3. **启动服务**：
```bash
# macOS 默认有头模式
python gemini.py
```

### Linux 服务器端配置

1. **启用"只接收同步"模式**（Web 控制台 → 系统设置 → 勾选 "只接收同步模式"）

2. **启动服务**：
```bash
# 强制无头模式（服务器无图形界面）
python gemini.py --headless
```

或使用环境变量：
```bash
export FORCE_HEADLESS=1
python gemini.py
```

### 配置项说明

| 配置项 | 配置位置 | 说明 |
|--------|----------|------|
| `remote_sync_url` | 主控端 | 远程服务器 URL |
| `remote_sync_api_key` | 主控端 | 远程服务器的管理员密钥 |
| `sync_only_mode` | 服务器端 | 启用后不主动刷新，只接收同步 |
| `auto_refresh_cookie` | 主控端 | 启用 Cookie 自动刷新 |

### 工作流程

1. 主控端检测到 Cookie 过期
2. 主控端执行自动刷新（使用临时邮箱登录）
3. 刷新成功后，自动推送到配置的远程服务器
4. 服务器端接收并更新 Cookie

### 同步多台服务器

目前每次只能配置一个远程同步地址。如需同步多台服务器，可以：

1. **方案一**：部署反向代理，将同步请求转发到多台服务器
2. **方案二**：使用 Nginx 负载均衡
3. **方案三**：在服务器间再配置级联同步

## ⚙️ 配置说明

系统现在主要使用**数据库**存储配置，所有配置都可以通过 Web 管理界面完成。详细说明请参考 [首次使用指南](./getting-started.md)。

### 环境变量配置

生产环境建议设置以下环境变量：

#### API 密钥加密密钥

```bash
# 生成 32 字节的随机密钥
export API_KEY_ENCRYPTION_KEY="$(openssl rand -base64 32 | head -c 32)"
```

或在 `docker-compose.yml` 中设置：

```yaml
environment:
  - API_KEY_ENCRYPTION_KEY=your-32-byte-encryption-key-here!!
```

#### 管理员密钥（可选）

```bash
export ADMIN_SECRET_KEY="your-admin-secret-key-here"
```

如果不设置，系统会自动生成并保存到配置文件。

### Docker 环境变量

在 `docker-compose.yml` 中设置环境变量：

```yaml
environment:
  - API_KEY_ENCRYPTION_KEY=your-32-byte-encryption-key-here!!
  - ADMIN_SECRET_KEY=your-admin-secret-key-here
```

或使用 `.env` 文件（推荐）：

```bash
# .env 文件
API_KEY_ENCRYPTION_KEY=your-32-byte-encryption-key-here!!
ADMIN_SECRET_KEY=your-admin-secret-key-here
```

然后在 `docker-compose.yml` 中引用：

```yaml
env_file:
  - .env
```

## 🔐 安全建议

1. **配置文件安全**
   - 不要将 `business_gemini_session.json` 提交到 Git 仓库
   - 设置适当的文件权限：`chmod 600 business_gemini_session.json`
   - 定期备份配置文件

2. **API 密钥安全**
   - 使用 Web 管理界面创建和管理 API 密钥
   - 定期轮换 API 密钥
   - 不要在前端代码中暴露 API 密钥
   - 详细说明请参考：[API密钥管理](./api-keys.md)

3. **管理员密码**
   - 首次登录后立即设置强密码
   - 定期更换管理员密码

4. **网络安全**
   - 生产环境建议使用 HTTPS（通过 Nginx 反向代理）
   - 限制管理接口的访问 IP
   - 使用防火墙限制端口访问


## 🐛 常见问题

### 1. 账号认证失败

**问题**：账号测试时提示认证失败

**解决方案**：
- 检查 Cookie 是否过期，重新获取
- 确认 `team_id` 是否正确
- 检查代理是否可用

### 2. 代理连接失败

**问题**：无法通过代理访问 Google 服务

**解决方案**：
- 测试代理是否可用：`curl -x http://proxy:port https://www.google.com`
- 检查代理地址和端口是否正确
- 确认防火墙设置

### 3. 端口被占用

**问题**：启动时提示端口 8000 已被占用

**解决方案**：
```bash
# 查找占用端口的进程
sudo lsof -i :8000
# 或
sudo netstat -tulpn | grep 8000

# 使用命令行参数指定其他端口
python gemini.py --port 8001

# 或修改 docker-compose.yml 中的端口映射
ports:
  - "8001:8000"
```

### 4. 图片无法访问

**问题**：生成的图片 URL 无法访问

**解决方案**：
- 检查 `image_base_url` 配置是否正确
- 确认媒体缓存目录权限：`chmod 755 image/ video/`
- 检查防火墙是否开放了相应端口

### 5. Cookie 自动刷新失败

**问题**：Cookie 自动刷新功能无法正常工作

**解决方案**：
- 确认已安装 Playwright：`playwright install chromium`
- 检查账号是否配置了 `tempmail_url` 和 `tempmail_name`
- 确认临时邮箱 URL 有效（可以手动访问测试）
- 如果临时邮箱服务支持 API，配置 `tempmail_worker_url` 以使用 API 方式（更快、更稳定）
- 系统会自动在 API 方式和浏览器方式之间切换，无需手动配置
- 查看日志文件 `log/app.log` 或 `log/error.log` 获取详细错误信息
- Linux 系统需要确保有图形界面或使用无头模式（系统会自动检测）

### 6. 环境变量未生效

**问题**：设置的环境变量没有生效

**解决方案**：
- 确认环境变量名称正确（`API_KEY_ENCRYPTION_KEY`、`ADMIN_SECRET_KEY`）
- 重启服务以使环境变量生效
- 在 Docker 中，确认 `docker-compose.yml` 或 `.env` 文件配置正确
- 检查环境变量是否被正确传递到容器中：`docker exec business-gemini-pool env | grep API_KEY_ENCRYPTION_KEY`

## 🔧 Nginx 反向代理配置

如果使用 Nginx 作为反向代理，需要增加超时时间以支持 Cookie 自动刷新功能。

### Nginx 配置示例

创建或编辑 Nginx 配置文件（如 `/etc/nginx/sites-available/gemini`）：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名
    
    # 增加超时时间（重要：自动刷新 Cookie 需要较长时间）
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    send_timeout 600s;

    # 关闭代理缓冲，提高响应速度
    proxy_buffering off;
    
    # 启用分块传输编码
    chunked_transfer_encoding on;
    
    # TCP 优化
    tcp_nopush on;
    tcp_nodelay on;
    
    # 保持连接超时
    keepalive_timeout 120;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 应用配置

```bash
# 测试配置
sudo nginx -t

# 重载配置
sudo nginx -s reload

# 或重启 Nginx
sudo systemctl restart nginx
```

### 关键配置说明

- **`proxy_read_timeout 600s`**: 从后端读取响应的超时时间，设置为 600 秒（10 分钟），确保自动刷新有足够时间
- **`proxy_connect_timeout 600s`**: 连接后端的超时时间
- **`proxy_send_timeout 600s`**: 向后端发送请求的超时时间
- **`send_timeout 600s`**: 向客户端发送响应的超时时间

## 📚 更多信息

- 详细 API 文档请参考 [README.md](../README.md)
- Web 管理控制台提供完整的配置管理功能
- 支持配置导入/导出，方便备份和迁移

