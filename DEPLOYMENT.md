# 🚀 WenXiaoBai API Proxy 部署指南

## 📋 系统特性

✅ **零配置部署** - 无需预配置 ACCESS_TOKEN  
✅ **多用户支持** - 用户通过 Web 界面上传 Token  
✅ **管理员控制台** - 批量管理用户和 Token  
✅ **OpenAI 兼容** - 完全兼容 OpenAI API 格式  
✅ **Docker 支持** - 一键部署，开箱即用  

## 🐳 Docker 部署（推荐）

### 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/liuyanghegg/CatieCli.git
cd CatieCli

# 2. 一键启动（无需任何配置）
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 访问服务

- **API 服务**: http://localhost:8080
- **用户控制台**: http://localhost:8080/dashboard.html
- **管理员控制台**: http://localhost:8080/admin.html

### 默认账户

- **管理员**: `admin` / `admin123`
- **普通用户**: 可自行注册

## 💻 本地部署

### 环境要求

- Python 3.8+
- pip

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/liuyanghegg/CatieCli.git
cd CatieCli

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务（推荐使用启动脚本）
python start.py

# 或直接启动
python main.py
```

## 🔧 配置说明

### 内置配置

系统内置了所有必要配置，无需手动设置：

```env
API_USERNAME="web.1.0.beta"          # HMAC 认证用户名（固定）
API_SECRET_KEY="TkoWuEN8cpDJubb7..."  # HMAC 认证密钥（固定）
DEVICE_ID=""                         # 设备ID（自动生成）
```

### 可选配置

如需自定义，可创建 `.env` 文件：

```env
# 服务配置
PORT=8080
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-this-in-production

# 数据存储
DATABASE_PATH=./wenxiaobai_users.db
SESSION_DATA_DIR=./sessions
LOG_DIR=./logs
```

## 📱 使用流程

### 1. 管理员设置

1. 访问管理员控制台: http://localhost:8080/admin.html
2. 使用默认账户登录: `admin` / `admin123`
3. 查看系统统计和用户管理

### 2. 用户注册和使用

1. 访问注册页面: http://localhost:8080/register.html
2. 注册新用户账户
3. 登录用户控制台: http://localhost:8080/dashboard.html
4. 上传文小白 Token
5. 生成 API Key
6. 使用 OpenAI 兼容接口

### 3. API 调用示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="YOUR_GENERATED_API_KEY"  # 从用户控制台获取
)

response = client.chat.completions.create(
    model="wenxiaobai-deep-thought",
    messages=[
        {"role": "user", "content": "你好"}
    ]
)

print(response.choices[0].message.content)
```

## 🔒 安全建议

### 生产环境配置

1. **修改默认密码**
   ```bash
   # 登录管理员控制台后立即修改 admin 密码
   ```

2. **设置安全密钥**
   ```env
   SECRET_KEY=your-very-secure-secret-key-here
   ```

3. **使用 HTTPS**
   ```bash
   # 建议在生产环境中使用反向代理（如 Nginx）配置 HTTPS
   ```

4. **数据备份**
   ```bash
   # 定期备份数据库文件
   cp wenxiaobai_users.db backup/
   ```

## 📊 监控和维护

### 健康检查

```bash
curl http://localhost:8080/health
```

### 日志查看

```bash
# Docker 部署
docker-compose logs -f

# 本地部署
tail -f logs/app.log
```

### 数据管理

- **数据库**: `wenxiaobai_users.db`
- **会话数据**: `sessions/`
- **日志文件**: `logs/`

## 🔧 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 修改端口
   export PORT=8081
   docker-compose up -d
   ```

2. **权限问题**
   ```bash
   # 确保目录权限
   chmod -R 755 sessions/ logs/ data/
   ```

3. **数据库锁定**
   ```bash
   # 重启服务
   docker-compose restart
   ```

### 重置系统

```bash
# 停止服务
docker-compose down

# 清理数据（谨慎操作）
rm -rf sessions/ logs/ *.db

# 重新启动
docker-compose up -d
```

## 📈 扩展部署

### 多实例部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  wenxiaobai-api-1:
    build: .
    ports:
      - "8080:8080"
    # ... 其他配置
  
  wenxiaobai-api-2:
    build: .
    ports:
      - "8081:8080"
    # ... 其他配置
```

### 负载均衡

```nginx
# nginx.conf
upstream wenxiaobai_backend {
    server localhost:8080;
    server localhost:8081;
}

server {
    listen 80;
    location / {
        proxy_pass http://wenxiaobai_backend;
    }
}
```

## 📞 技术支持

- **GitHub Issues**: https://github.com/liuyanghegg/CatieCli/issues
- **文档**: README.md
- **更新日志**: Git commit history

---

**🎉 享受使用 WenXiaoBai API Proxy！**