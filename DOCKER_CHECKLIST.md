# 🐳 Docker 部署检查清单

## ✅ 必要文件检查

### 核心应用文件
- [x] `main.py` - Flask 主应用
- [x] `database.py` - 数据库管理
- [x] `user_management.py` - 用户管理 API
- [x] `wenxiaobai_client.py` - 文小白客户端
- [x] `balance_checker.py` - 余额查询
- [x] `task_system.py` - 任务系统
- [x] `logging_system.py` - 日志系统

### 前端文件
- [x] `static/admin.html` - 管理员控制台
- [x] `static/dashboard.html` - 用户控制台
- [x] `static/login.html` - 登录页面
- [x] `static/register.html` - 注册页面
- [x] `static/index.html` - 首页

### Docker 配置文件
- [x] `Dockerfile` - Docker 镜像配置
- [x] `docker-compose.yml` - Docker Compose 配置
- [x] `.dockerignore` - Docker 忽略文件
- [x] `requirements.txt` - Python 依赖

### 配置文件
- [x] `.env.example` - 环境变量示例
- [x] `.gitignore` - Git 忽略文件

### 文档文件
- [x] `README.md` - 项目说明
- [x] `DEPLOYMENT.md` - 部署指南

## 🔧 Docker 配置验证

### Dockerfile 配置
```dockerfile
FROM python:3.10-slim
WORKDIR /app

# 系统依赖（包含 curl 用于健康检查）
RUN apt-get update && apt-get install -y gcc curl

# Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 应用代码
COPY . .

# 目录创建
RUN mkdir -p /app/sessions /app/logs /app/data

# 健康检查
HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} main:app
```

### docker-compose.yml 配置
```yaml
version: '3.8'
services:
  wenxiaobai-api:
    build: .
    ports:
      - "8080:8080"
    environment:
      # 内置配置（无需修改）
      - API_USERNAME=web.1.0.beta
      - API_SECRET_KEY=TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z
      - PORT=8080
      - FLASK_ENV=production
    volumes:
      # 数据持久化
      - wenxiaobai-sessions:/app/sessions
      - wenxiaobai-data:/app/data
      - wenxiaobai-logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
```

## 🚀 部署命令

### 1. 克隆项目
```bash
git clone https://github.com/liuyanghegg/CatieCli.git
cd CatieCli
```

### 2. 一键启动
```bash
docker-compose up -d
```

### 3. 验证部署
```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 测试健康检查
curl http://localhost:8080/health

# 访问管理员控制台
curl http://localhost:8080/admin.html
```

## 📊 环境变量配置

### 必需的环境变量（已内置）
- `API_USERNAME=web.1.0.beta`
- `API_SECRET_KEY=TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z`

### 可选的环境变量
- `PORT=8080` - 服务端口
- `FLASK_ENV=production` - Flask 环境
- `SECRET_KEY=change-this-in-production` - 会话密钥
- `DATABASE_PATH=/app/data/wenxiaobai_users.db` - 数据库路径
- `SESSION_DATA_DIR=/app/sessions` - 会话目录
- `LOG_DIR=/app/logs` - 日志目录

## 🔒 数据持久化

### Docker 卷配置
- `wenxiaobai-sessions:/app/sessions` - 会话数据
- `wenxiaobai-data:/app/data` - 数据库文件
- `wenxiaobai-logs:/app/logs` - 日志文件

### 数据备份
```bash
# 备份数据库
docker cp wenxiaobai-api-proxy:/app/data/wenxiaobai_users.db ./backup/

# 恢复数据库
docker cp ./backup/wenxiaobai_users.db wenxiaobai-api-proxy:/app/data/
```

## 🌐 访问地址

部署成功后可访问：
- **API 服务**: http://localhost:8080
- **管理员控制台**: http://localhost:8080/admin.html
- **用户控制台**: http://localhost:8080/dashboard.html
- **健康检查**: http://localhost:8080/health

## 🔑 默认账户

- **管理员**: `admin` / `admin123`
- **普通用户**: 可自行注册

## ✅ 部署验证清单

- [ ] 容器成功启动
- [ ] 健康检查通过
- [ ] 管理员页面可访问
- [ ] 用户注册功能正常
- [ ] 数据库自动创建
- [ ] 日志正常输出
- [ ] 数据持久化正常

## 🔧 故障排除

### 常见问题
1. **端口被占用**: 修改 docker-compose.yml 中的端口映射
2. **权限问题**: 确保 Docker 有足够权限
3. **网络问题**: 检查防火墙和网络配置
4. **数据丢失**: 确保卷挂载配置正确

### 调试命令
```bash
# 进入容器
docker exec -it wenxiaobai-api-proxy bash

# 查看容器日志
docker logs wenxiaobai-api-proxy

# 重启服务
docker-compose restart

# 完全重建
docker-compose down
docker-compose up --build -d
```

---

**🎉 所有配置已优化，支持零配置一键部署！**