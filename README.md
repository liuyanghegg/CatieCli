# WenXiaoBai OpenAI Compatible API Proxy

一个完全兼容 OpenAI API 格式的文小白 API 代理服务，支持用户管理、Token管理、自动任务系统和完整的管理员控制台。

## 🌟 功能特性

### ✅ OpenAI API 完全兼容
- 符合 OpenAI Chat Completions API 规范
- 符合 OpenAI Models API 规范
- 支持 Azure OpenAI 部署端点格式
- 支持流式和非流式响应
- 完全兼容 Cursor、Cline 等 AI 编程工具

### ✅ 21种模型配置
支持 DeepSeek V3_2、DeepSeek V3、小白5 等多个模型系列，每个系列都提供基础、搜索、深度思考等不同能力组合。

### ✅ 完整的用户管理系统
- 用户注册、登录、权限管理
- API Key 生成和管理
- Token 上传和验证
- 余额查询和监控
- 自动任务系统

### ✅ 强大的管理员控制台
- 系统统计概览
- 用户管理（启用/禁用/删除）
- Token 批量管理
- 重复检测和验证
- 实时监控和日志

### ✅ 智能任务系统
- 自动余额监控
- 智能任务执行（浏览任务、签到任务）
- 每日统计和报告
- 低余额自动禁用保护

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

1. **克隆项目**
```bash
git clone https://github.com/liuyanghegg/CatieCli.git
cd CatieCli
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 ACCESS_TOKEN
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问服务**
- API 服务: http://localhost:8080
- 用户控制台: http://localhost:8080/dashboard.html
- 管理员控制台: http://localhost:8080/admin.html

### 方式二：本地运行

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件
```

3. **启动服务**
```bash
python main.py
```

## 📱 用户界面

### 用户控制台功能
- **Token 管理**: 上传、启用/禁用、删除 Token
- **API Key 管理**: 生成、管理 API Key
- **余额查询**: 实时查询 Token 余额
- **自动任务**: 配置自动任务执行
- **API 测试**: 测试 Token 连接性
- **模型查看**: 查看所有可用模型

### 管理员控制台功能
- **系统统计**: 用户数、Token数、活跃状态
- **用户管理**: 查看、启用/禁用、删除用户
- **Token 管理**: 批量管理所有用户的 Token
- **重复检测**: 基于文小白用户名的重复检测
- **批量操作**: 批量启用/禁用、删除、切换自动任务

## 🔑 默认账户

- **管理员**: `admin` / `admin123`
- 普通用户需要注册创建

## 📋 支持的模型

### DeepSeek V3_2 系列（8个变体）
- `wenxiaobai-base` - 基础模型
- `wenxiaobai-v3_2-base` - DeepSeek V3_2 基础模型
- `wenxiaobai-search` - 搜索模型
- `wenxiaobai-v3_2-search` - DeepSeek V3_2 搜索模型
- `wenxiaobai-deep-thought` - 深度思考模型
- `wenxiaobai-v3_2-deep-thought` - DeepSeek V3_2 深度思考模型
- `wenxiaobai-search-deep-thought` - 搜索+深度思考模型
- `wenxiaobai-v3_2-search-deep-thought` - DeepSeek V3_2 搜索+深度思考模型

### DeepSeek V3 系列（5个变体）
- `deepseek-v3` - DeepSeek V3 模型
- `deepseek-v3-base` - DeepSeek V3 基础模型
- `deepseek-v3-search` - DeepSeek V3 搜索模型
- `deepseek-v3-deep-thought` - DeepSeek V3 深度思考模型
- `deepseek-v3-search-deep-thought` - DeepSeek V3 搜索+深度思考模型

### 小白5 系列（5个变体）
- `xiaobai-5` - 小白5模型
- `xiaobai-5-base` - 小白5基础模型
- `xiaobai-5-search` - 小白5搜索模型
- `xiaobai-5-deep-thought` - 小白5深度思考模型
- `xiaobai-5-search-deep-thought` - 小白5搜索+深度思考模型

### 直接使用模型ID（3个变体）
- `deepseekV3` - DeepSeek V3 原始模型
- `xiaobai5` - 小白5 原始模型
- `deepseekV3_2` - DeepSeek V3_2 原始模型

## 🔧 API 使用示例

### 基础聊天请求
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "wenxiaobai-deep-thought",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "stream": true
  }'
```

### Python 客户端
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="YOUR_API_KEY"
)

response = client.chat.completions.create(
    model="wenxiaobai-deep-thought",
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='', flush=True)
```

## 🗄️ 数据库设计

系统使用 SQLite 数据库，包含以下表：
- `users` - 用户信息
- `api_keys` - API Key 管理
- `tokens` - 文小白 Token 管理
- `usage_logs` - 使用记录
- `task_logs` - 任务记录
- `token_daily_stats` - 每日统计

## 🔒 安全特性

- 密码哈希存储
- API Key 验证
- 会话管理
- 权限控制
- Token 重复检测
- 自动任务保护

## 📊 监控和日志

- 完整的请求日志
- 错误处理和记录
- 性能监控
- 健康检查端点
- 使用统计

## 🐳 Docker 部署

### 环境变量配置
```env
# 必填
ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE

# 可选（已有默认值）
API_USERNAME=web.1.0.beta
API_SECRET_KEY=TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z
PORT=8080
FLASK_ENV=production
```

### 数据持久化
- 数据库: `/app/data/wenxiaobai_users.db`
- 会话数据: `/app/sessions`
- 日志文件: `/app/logs`

## 🛠️ 开发和贡献

### 项目结构
```
CatieCli/
├── main.py                 # Flask 主应用
├── database.py             # 数据库管理
├── user_management.py      # 用户管理 API
├── wenxiaobai_client.py    # 文小白客户端
├── balance_checker.py      # 余额查询
├── task_system.py          # 任务系统
├── logging_system.py       # 日志系统
├── static/                 # 前端文件
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── admin.html
├── requirements.txt        # 依赖列表
├── Dockerfile             # Docker 配置
├── docker-compose.yml     # Docker Compose 配置
└── README.md              # 项目文档
```

### 技术栈
- **后端**: Python 3.10, Flask, SQLite
- **前端**: HTML, CSS, JavaScript
- **部署**: Docker, Gunicorn
- **API**: OpenAI 兼容格式

## 📝 更新日志

### v2.0.0 (最新)
- ✅ 完整的用户管理系统
- ✅ 管理员控制台
- ✅ Token 重复检测
- ✅ 自动任务系统
- ✅ 批量操作功能
- ✅ 余额监控和保护

### v1.0.0
- ✅ OpenAI API 兼容
- ✅ 21种模型支持
- ✅ 会话管理
- ✅ Docker 部署

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请：
1. 查看文档和 FAQ
2. 提交 GitHub Issue
3. 联系项目维护者

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**