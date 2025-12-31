# 使用官方 Python 运行时作为父镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/sessions /app/logs /app/data

# 设置权限
RUN chmod +x /app

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 使用 Gunicorn 运行应用
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 3 --timeout 120 --access-logfile - --error-logfile - main:app"]
