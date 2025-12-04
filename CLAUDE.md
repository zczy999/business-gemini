# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Business Gemini Pool 是一个基于 Flask 的 Google Gemini Enterprise API 代理服务，提供 OpenAI 兼容接口和 Web 管理控制台。核心功能包括多账号轮训、流式响应、图片/视频生成、Cookie 自动刷新。

## 常用命令

### 启动服务
```bash
# 默认启动（端口 8000）
python gemini.py

# 指定端口和主机
python gemini.py --host 127.0.0.1 --port 8001

# Cookie 刷新模式（浏览器可视化调试用）
python gemini.py --headed
```

### 数据迁移
```bash
# JSON 配置迁移到数据库
python gemini.py --migrate

# 强制覆盖迁移
python gemini.py --migrate --force

# 导出数据库到 JSON（备份）
python gemini.py --export
```

### 安装依赖
```bash
pip install -r requirements.txt

# Playwright 浏览器（Cookie 自动刷新需要）
playwright install chromium
```

### Docker
```bash
docker build -t business-gemini .
docker run -p 8000:8000 business-gemini
```

## 代码架构

### 入口与初始化
- `gemini.py` - 主入口，解析命令行参数，启动 Flask + SocketIO 服务
- `app/__init__.py` - Flask 应用工厂，初始化 SocketIO 和路由

### 核心模块 (`app/`)
- `routes.py` - 所有 API 端点（OpenAI 兼容接口、账号管理、系统配置等）
- `account_manager.py` - 多账号轮训管理，JWT 缓存，配额追踪。全局单例 `account_manager`
- `chat_handler.py` - 聊天处理，流式响应解析，OpenAI 格式转换
- `session_manager.py` - Gemini 会话管理，文件上传
- `cookie_refresh.py` - Cookie 自动刷新后台线程（使用临时邮箱）

### 存储层
- `database.py` - SQLAlchemy 模型定义（Account, Model, SystemConfig, APIKey, APICallLog）
- `migration.py` - JSON 到数据库迁移工具
- 数据库文件：`geminibusiness.db`（SQLite）
- 配置文件：`business_gemini_session.json`（备份/兼容用）

### 辅助模块
- `config.py` - 配置常量（API URLs, 冷却时间, 缓存配置）
- `jwt_utils.py` - JWT Token 获取和缓存
- `media_handler.py` - 图片/视频下载、缓存、过期清理
- `cfbed_upload.py` - 图片上传到 cfbed 服务
- `tempmail_api.py` - 临时邮箱 API 集成
- `exceptions.py` - 自定义异常（AccountRateLimitError, AccountAuthError, NoAvailableAccount 等）
- `websocket_manager.py` - WebSocket 实时通知
- `logger.py` - 日志模块，支持级别控制和日期轮转

### 前端
- `templates/index.html` - 管理控制台（单文件 Vue 应用）
- `templates/chat_history.html` - 聊天界面
- `templates/login.html` - 登录页面

## 请求处理流程

聊天请求 `/v1/chat/completions` 的处理流程：
1. `routes.py` 接收请求，验证 API Key
2. `account_manager.get_next_account()` 轮训获取可用账号
3. `jwt_utils.py` 获取/缓存 JWT Token
4. `session_manager.py` 创建/复用 Gemini 会话
5. `chat_handler.py` 发送请求并解析流式响应，转换为 OpenAI 格式
6. 如遇错误（401/403/429），`account_manager.mark_quota_error()` 触发账号冷却

## Session 机制

Session 管理位于 `session_manager.py`，核心数据结构：
- `account_states[idx]["session"]` - 当前 session
- `account_states[idx]["session_count"]` - session 使用次数
- `account_states[idx]["session_created_time"]` - session 创建时间戳

### 简化规则

每个账号只维护一个 session，更新条件：
- **对话数超过 50 次** → 创建新 session
- **超过 12 小时** → 创建新 session

### JWT 与 Session 生命周期
- JWT 有效期约 240 秒（4分钟），过期自动刷新
- JWT 刷新后会清除旧 session（JWT 与 session 绑定）
- Session 通过 `widgetCreateSession` API 创建，返回 session_name

## 关键 API 端点

| 端点 | 说明 |
|------|------|
| `POST /v1/chat/completions` | OpenAI 兼容聊天接口 |
| `GET /v1/models` | 获取模型列表 |
| `POST /v1/files` | 文件上传 |
| `GET /v1/files` | 文件列表 |
| `GET /v1/files/<id>` | 获取文件信息 |
| `DELETE /v1/files/<id>` | 删除文件 |
| `GET /api/accounts` | 账号列表（含配额信息） |
| `POST /api/accounts/<id>/auto-refresh-cookie` | 临时邮箱自动刷新 Cookie |

## API 请求格式

### 文件上传 (`POST /v1/files`)

```bash
curl -X POST http://127.0.0.1:8000/v1/files \
  -F "file=@image.png" \
  -F "purpose=assistants"
# 返回: {"id": "file-xxx", "object": "file", ...}
```

### 聊天请求 (`POST /v1/chat/completions`)

**基本格式**：
```json
{
  "model": "gemini-enterprise",
  "messages": [...],
  "stream": true
}
```

**图片输入方式**（4种）：

1. **file_id 引用**（推荐，先上传后引用）：
```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "描述这张图片"},
    {"type": "file", "file_id": "file-xxx"}
  ]
}
```

2. **image_url + base64**（OpenAI 标准格式）：
```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "描述这张图片"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]
}
```

3. **image_url + URL**：
```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "描述这张图片"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}
  ]
}
```

4. **prompts + files 数组**（扩展格式）：
```json
{
  "model": "gemini-enterprise",
  "prompts": [
    {
      "role": "user",
      "text": "描述这张图片",
      "files": [
        {"data": "data:image/png;base64,...", "type": "image"}
      ]
    }
  ]
}
```

### 消息转换

OpenAI messages 格式转换为 Gemini 请求：

```json
// 输入
{"role": "system", "content": "You are a helpful assistant."},
{"role": "user", "content": "Hello"}

// 转换后
{
  "query": {
    "parts": [{
      "text": "[System Instruction]\nYou are a helpful assistant.\n\n[User Message]\nHello"
    }]
  }
}
```

- **system** → 拼接到 user 消息前面（`[System Instruction]` 标记）
- **user** → 提取最后一条用户消息（`[User Message]` 标记）
- **assistant** → 忽略（历史对话由 Gemini session 维护）

### 文件处理流程

```
1. 内联 base64/URL 图片 → 自动上传到 Gemini → 获取 gemini_file_id
2. OpenAI file_id → 查询 file_manager → 获取 gemini_file_id
3. 聊天时携带 gemini_file_id 发送请求
```

相关代码：
- 图片解析：`media_handler.py:extract_images_from_openai_content()`
- 文件上传：`session_manager.py:upload_file_to_gemini()`
- 文件管理：`file_manager.py`（OpenAI file_id ↔ Gemini file_id 映射）

## 账号轮训机制

`AccountManager` 使用被动检测方式管理账号：
- 账号选择：`get_next_account()` 轮训获取可用账号
- 错误处理：根据 HTTP 状态码（401/403/429）自动冷却账号
- 配额类型：支持 `images`、`videos` 配额隔离

冷却时间配置在 `config.py`：
- 凭证错误：15分钟
- 触发限额：5分钟（或到太平洋时间午夜）
- 其他错误：2分钟

## 环境变量

| 变量 | 说明 |
|------|------|
| `API_KEY_ENCRYPTION_KEY` | API 密钥加密密钥（32字节） |
| `ADMIN_SECRET_KEY` | 管理员密钥（自动生成） |
| `LOG_LEVEL` | 日志级别（DEBUG/INFO/ERROR） |
| `FORCE_HEADLESS` | 强制无头模式 Cookie 刷新 |
