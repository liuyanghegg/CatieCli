# 1. 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖文件并安装
# 使用 --no-cache-dir 来减小镜像体积
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制应用程序代码到工作目录
COPY . .

# 5. 创建会话数据目录
RUN mkdir -p /app/sessions

# 6. 暴露端口
# Zeabur 会自动检测并使用 $PORT 环境变量，但声明 EXPOSE 是一个好习惯
EXPOSE 8080

# 7. 声明数据卷
VOLUME ["/app/sessions"]

# 8. 使用 Gunicorn 运行应用
# Zeabur 会注入 $PORT 环境变量，我们将其传递给 Gunicorn
# --workers 建议设置为 (2 * CPU核心数) + 1。这里我们用 3 作为一个合理的默认值。
# --timeout 120 增加超时时间以处理长请求
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "3", "--timeout", "120", "main:app"]
