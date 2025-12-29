# WenXiaoBai OpenAI Compatible API

这是一个完全兼容 OpenAI API 格式的文小白 API 代理服务，支持四种模型配置，可以灵活组合搜索和深度思考功能。

## 功能特性

✅ **完全 OpenAI 兼容**
- 符合 OpenAI Chat Completions API 规范
- 符合 OpenAI Models API 规范
- 支持 Azure OpenAI 部署端点格式
- 支持流式和非流式响应
- 完全兼容 roo code、Cline 等 AI 编程工具

✅ **21种模型配置**

**DeepSeek V3_2 系列（8个变体）**
1. `wenxiaobai-base` - 基础模型，无搜索和深度思考
2. `wenxiaobai-v3_2-base` - DeepSeek V3_2 基础模型
3. `wenxiaobai-search` - 搜索模型，具备联网搜索能力
4. `wenxiaobai-v3_2-search` - DeepSeek V3_2 搜索模型
5. `wenxiaobai-deep-thought` - 深度思考模型，具备深度推理能力
6. `wenxiaobai-v3_2-deep-thought` - DeepSeek V3_2 深度思考模型
7. `wenxiaobai-search-deep-thought` - 搜索+深度思考模型
8. `wenxiaobai-v3_2-search-deep-thought` - DeepSeek V3_2 搜索+深度思考模型

**DeepSeek V3 系列（5个变体）**
9. `deepseek-v3` - DeepSeek V3 模型，具备深度搜索能力
10. `deepseek-v3-base` - DeepSeek V3 基础模型
11. `deepseek-v3-search` - DeepSeek V3 搜索模型
12. `deepseek-v3-deep-thought` - DeepSeek V3 深度思考模型
13. `deepseek-v3-search-deep-thought` - DeepSeek V3 搜索+深度思考模型

**小白5 系列（5个变体）**
14. `xiaobai-5` - 小白5模型，基础对话模型
15. `xiaobai-5-base` - 小白5基础模型
16. `xiaobai-5-search` - 小白5搜索模型
17. `xiaobai-5-deep-thought` - 小白5深度思考模型
18. `xiaobai-5-search-deep-thought` - 小白5搜索+深度思考模型

**直接使用模型ID（3个变体）**
19. `deepseekV3` - DeepSeek V3 原始模型
20. `xiaobai5` - 小白5 原始模型
21. `deepseekV3_2` - DeepSeek V3_2 原始模型

✅ **灵活的能力组合**
- 搜索功能：联网搜索最新信息
- 深度思考：增强的推理和分析能力
- 可以根据需求选择合适的模型

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd weixiaobai
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的凭据：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# API_USERNAME 和 API_SECRET_KEY 已预设固定值
# 只需填写 ACCESS_TOKEN

API_USERNAME=web.1.0.beta
API_SECRET_KEY=TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z
ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE

# DEVICE_ID 会自动生成，无需填写
DEVICE_ID=

PORT=8080
DEBUG=false
SESSION_DATA_DIR=./sessions
```

## 使用方法

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8080` 启动。

### API 端点

#### 1. 列出所有模型

```bash
GET /v1/models
```

**响应示例：**

```json
{
  "object": "list",
  "data": [
    {
      "id": "wenxiaobai-base",
      "object": "model",
      "created": 1234567890,
      "owned_by": "wenxiaobai",
      "permission": [],
      "root": "wenxiaobai-base",
      "parent": null,
      "description": "基础模型，无搜索和深度思考功能"
    },
    {
      "id": "wenxiaobai-search",
      "object": "model",
      "created": 1234567890,
      "owned_by": "wenxiaobai",
      "permission": [],
      "root": "wenxiaobai-search",
      "parent": null,
      "description": "搜索模型，具备联网搜索能力"
    },
    {
      "id": "wenxiaobai-deep-thought",
      "object": "model",
      "created": 1234567890,
      "owned_by": "wenxiaobai",
      "permission": [],
      "root": "wenxiaobai-deep-thought",
      "parent": null,
      "description": "深度思考模型，具备深度推理能力"
    },
    {
      "id": "wenxiaobai-search-deep-thought",
      "object": "model",
      "created": 1234567890,
      "owned_by": "wenxiaobai",
      "permission": [],
      "root": "wenxiaobai-search-deep-thought",
      "parent": null,
      "description": "搜索+深度思考模型，同时具备联网搜索和深度推理能力"
    }
  ]
}
```

#### 2. 获取特定模型信息

```bash
GET /v1/models/{model_id}
```

#### 3. 聊天完成（标准 OpenAI 格式）

```bash
POST /v1/chat/completions
```

**请求示例：**

```json
{
  "model": "wenxiaobai-deep-thought",
  "messages": [
    {
      "role": "user",
      "content": "你好，请介绍一下你自己"
    }
  ],
  "stream": true,
  "temperature": 1.0,
  "max_tokens": 2000,
  "top_p": 1.0
}
```

**流式响应示例：**

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"wenxiaobai-deep-thought","choices":[{"index":0,"delta":{"content":"你好"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"wenxiaobai-deep-thought","choices":[{"index":0,"delta":{"content":"！我是文小白"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"wenxiaobai-deep-thought","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**非流式响应示例：**

设置 `"stream": false` 可以获取完整的响应：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "wenxiaobai-deep-thought",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是文小白，一个AI助手。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

#### 4. Azure OpenAI 兼容端点

```bash
POST /v1/deployments/{deployment_name}/chat/completions
```

#### 5. 健康检查

```bash
GET /health
```

**响应示例：**

```json
{
  "status": "ok",
  "service": "wenxiaobai-openai-proxy",
  "version": "1.0.0"
}
```

## 模型说明

### DeepSeek V3_2 系列

#### wenxiaobai-base
- **描述**: 基础模型（deepseekV3_2），无搜索和深度思考功能
- **适用场景**: 简单对话、基础问答
- **特点**: 响应快速，适合不需要额外功能的场景

#### wenxiaobai-v3_2-base
- **描述**: DeepSeek V3_2 基础模型，无搜索和深度思考功能
- **适用场景**: 简单对话、基础问答
- **特点**: 使用 DeepSeek V3_2 模型

#### wenxiaobai-search
- **描述**: 搜索模型（deepseekV3_2），具备联网搜索能力
- **适用场景**: 需要最新信息的问答、时事新闻、技术查询
- **特点**: 可以访问互联网获取最新信息

#### wenxiaobai-v3_2-search
- **描述**: DeepSeek V3_2 搜索模型，具备联网搜索能力
- **适用场景**: 需要最新信息的问答、时事新闻、技术查询
- **特点**: 使用 DeepSeek V3_2 模型 + 搜索功能

#### wenxiaobai-deep-thought
- **描述**: 深度思考模型（deepseekV3_2），具备深度推理能力
- **适用场景**: 复杂问题分析、逻辑推理、代码编写
- **特点**: 提供更深入的分析和推理

#### wenxiaobai-v3_2-deep-thought
- **描述**: DeepSeek V3_2 深度思考模型，具备深度推理能力
- **适用场景**: 复杂问题分析、逻辑推理、代码编写
- **特点**: 使用 DeepSeek V3_2 模型 + 深度思考功能

#### wenxiaobai-search-deep-thought
- **描述**: 搜索+深度思考模型（deepseekV3_2），同时具备联网搜索和深度推理能力
- **适用场景**: 需要最新信息的复杂分析、综合研究
- **特点**: 结合了搜索和深度思考的优势

#### wenxiaobai-v3_2-search-deep-thought
- **描述**: DeepSeek V3_2 搜索+深度思考模型，同时具备联网搜索和深度推理能力
- **适用场景**: 需要最新信息的复杂分析、综合研究
- **特点**: 使用 DeepSeek V3_2 模型 + 搜索 + 深度思考

### DeepSeek V3 系列

#### deepseek-v3
- **描述**: DeepSeek V3 模型，具备深度搜索能力
- **适用场景**: 需要深度搜索的复杂查询
- **特点**: 强大的搜索和推理能力

#### deepseek-v3-base
- **描述**: DeepSeek V3 基础模型，无额外功能
- **适用场景**: 简单对话、基础问答
- **特点**: 使用 DeepSeek V3 模型

#### deepseek-v3-search
- **描述**: DeepSeek V3 搜索模型，具备联网搜索能力
- **适用场景**: 需要最新信息的问答、时事新闻、技术查询
- **特点**: 使用 DeepSeek V3 模型 + 搜索功能

#### deepseek-v3-deep-thought
- **描述**: DeepSeek V3 深度思考模型，具备深度推理能力
- **适用场景**: 复杂问题分析、逻辑推理、代码编写
- **特点**: 使用 DeepSeek V3 模型 + 深度思考功能

#### deepseek-v3-search-deep-thought
- **描述**: DeepSeek V3 搜索+深度思考模型，同时具备联网搜索和深度推理能力
- **适用场景**: 需要最新信息的复杂分析、综合研究
- **特点**: 使用 DeepSeek V3 模型 + 搜索 + 深度思考

### 小白5 系列

#### xiaobai-5
- **描述**: 小白5模型，基础对话模型
- **适用场景**: 日常对话、简单问答
- **特点**: 轻量级，响应快速

#### xiaobai-5-base
- **描述**: 小白5基础模型，无额外功能
- **适用场景**: 简单对话、基础问答
- **特点**: 使用 xiaobai5 模型

#### xiaobai-5-search
- **描述**: 小白5搜索模型，具备联网搜索能力
- **适用场景**: 需要最新信息的问答、时事新闻、技术查询
- **特点**: 使用 xiaobai5 模型 + 搜索功能

#### xiaobai-5-deep-thought
- **描述**: 小白5深度思考模型，具备深度推理能力
- **适用场景**: 复杂问题分析、逻辑推理、代码编写
- **特点**: 使用 xiaobai5 模型 + 深度思考功能

#### xiaobai-5-search-deep-thought
- **描述**: 小白5搜索+深度思考模型，同时具备联网搜索和深度推理能力
- **适用场景**: 需要最新信息的复杂分析、综合研究
- **特点**: 使用 xiaobai5 模型 + 搜索 + 深度思考

### 直接使用模型ID

#### deepseekV3
- **描述**: DeepSeek V3 原始模型
- **适用场景**: 直接使用 DeepSeek V3 模型
- **特点**: 原始模型，无额外配置

#### xiaobai5
- **描述**: 小白5 原始模型
- **适用场景**: 直接使用 xiaobai5 模型
- **特点**: 原始模型，无额外配置

#### deepseekV3_2
- **描述**: DeepSeek V3_2 原始模型
- **适用场景**: 直接使用 DeepSeek V3_2 模型
- **特点**: 原始模型，无额外配置

## 会话管理

API 支持智能会话保持功能，可以在多轮对话中自动保持上下文。

### 核心特性

✅ **自动会话管理**
- 不提供 `session_id` 时自动生成唯一会话ID
- 自动保存和恢复会话上下文
- 支持会话数据持久化

✅ **多轮对话支持**
- 在同一会话中保持对话历史
- AI 可以记住之前的对话内容
- 支持长时间对话

✅ **会话隔离**
- 不同 `session_id` 的会话完全隔离
- 每个会话独立管理上下文
- 支持多个并发会话

### 使用方法

#### 方法1：自动会话（推荐）

不提供 `session_id`，系统自动创建和管理会话：

```json
{
  "model": "wenxiaobai-deep-thought",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": false
}
```

**优点**：
- 无需手动管理会话ID
- 适合单次对话场景
- 简单易用

#### 方法2：指定会话ID

在请求中添加 `session_id` 参数：

```json
{
  "model": "wenxiaobai-deep-thought",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": false,
  "session_id": "my-session-123"
}
```

**优点**：
- 可以跨请求保持会话
- 适合多轮对话场景
- 可以恢复之前的会话

### 会话规则

1. **首次请求**: 
   - 不提供 `session_id` → 自动创建新会话
   - 提供 `session_id` → 如果会话不存在则创建新会话

2. **后续请求**: 
   - 使用相同的 `session_id` → 在同一会话中继续对话
   - 使用不同的 `session_id` → 创建新会话

3. **会话保持**: 
   - 系统自动管理会话ID和对话历史
   - 会话数据持久化到文件
   - 服务重启后自动恢复会话

### 完整示例

#### Python 客户端 - 多轮对话

```python
import requests

base_url = "http://localhost:8080"
session_id = "my-unique-session-id"

# 第一轮对话
response1 = requests.post(
    f"{base_url}/v1/chat/completions",
    json={
        "model": "wenxiaobai-deep-thought",
        "messages": [{"role": "user", "content": "我叫小明"}],
        "stream": false,
        "session_id": session_id
    }
)
print("AI:", response1.json()['choices'][0]['message']['content'])

# 第二轮对话（使用相同的 session_id，AI 会记住之前的对话）
response2 = requests.post(
    f"{base_url}/v1/chat/completions",
    json={
        "model": "wenxiaobai-deep-thought",
        "messages": [{"role": "user", "content": "我叫什么名字？"}],
        "stream": false,
        "session_id": session_id
    }
)
print("AI:", response2.json()['choices'][0]['message']['content'])
# AI 应该回答：你叫小明

# 第三轮对话
response3 = requests.post(
    f"{base_url}/v1/chat/completions",
    json={
        "model": "wenxiaobai-deep-thought",
        "messages": [{"role": "user", "content": "我刚才说了什么？"}],
        "stream": false,
        "session_id": session_id
    }
)
print("AI:", response3.json()['choices'][0]['message']['content'])
# AI 应该记得之前的对话内容
```

#### 使用 OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dummy"
)

session_id = "my-session-id"

# 第一轮对话
response1 = client.chat.completions.create(
    model="wenxiaobai-deep-thought",
    messages=[{"role": "user", "content": "我叫小红"}],
    stream=False,
    extra_body={"session_id": session_id}
)
print("AI:", response1.choices[0].message.content)

# 第二轮对话
response2 = client.chat.completions.create(
    model="wenxiaobai-deep-thought",
    messages=[{"role": "user", "content": "我叫什么名字？"}],
    stream=False,
    extra_body={"session_id": session_id}
)
print("AI:", response2.choices[0].message.content)
# AI 应该回答：你叫小红
```

### 会话数据存储

会话数据自动保存在 `SESSION_DATA_DIR` 目录（默认为 `./sessions`）：

```
sessions/
└── sessions.json
```

**数据格式**：
```json
{
  "session-id-1": {
    "conversation_id": "uuid-of-conversation",
    "turn_index": 3
  },
  "session-id-2": {
    "conversation_id": "uuid-of-conversation",
    "turn_index": 1
  }
}
```

**字段说明**：
- `conversation_id`: 文小白 API 的对话ID
- `turn_index`: 对话轮次计数

### 最佳实践

1. **长期对话**: 使用固定的 `session_id` 进行长期对话
2. **独立会话**: 为不同的对话场景使用不同的 `session_id`
3. **会话清理**: 定期清理不需要的会话数据
4. **并发会话**: 支持多个 `session_id` 并发使用

### 注意事项

1. **会话持久化**: 会话数据保存在服务器本地，重启服务后会自动恢复
2. **会话隔离**: 不同 `session_id` 的会话完全独立，不会互相影响
3. **会话限制**: 文小白 API 可能有对话轮次限制，达到限制后会自动创建新会话
4. **数据安全**: 会话数据包含对话历史，请妥善保管 `sessions.json` 文件

## 使用示例

### Python 客户端

```python
import requests

# 配置
base_url = "http://localhost:8080"
api_key = "dummy"  # 文小白不需要真实的 API key

# 发送请求
response = requests.post(
    f"{base_url}/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    json={
        "model": "wenxiaobai-deep-thought",
        "messages": [
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ],
        "stream": True
    },
    stream=True
)

# 处理流式响应
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data_str = line_str[6:]
            if data_str == '[DONE]':
                break
            try:
                data = json.loads(data_str)
                if 'choices' in data and len(data['choices']) > 0:
                    delta = data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        print(content, end='', flush=True)
            except json.JSONDecodeError:
                pass
```

### cURL 示例

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d '{
    "model": "wenxiaobai-deep-thought",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "stream": true
  }'
```

### 使用 OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dummy"  # 文小白不需要真实的 API key
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

## 测试

运行测试客户端：

```bash
python test_openai_client.py
```

测试客户端会自动执行以下测试：
1. 列出所有模型
2. 获取特定模型信息
3. 使用模型进行对话
4. 健康检查

## Docker 部署

### 使用 Docker Compose（推荐）

1. **创建 `.env` 文件**

```bash
cp .env.example .env
```

2. **编辑 `.env` 文件，只需填写 ACCESS_TOKEN**

```env
API_USERNAME=web.1.0.beta
API_SECRET_KEY=TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z
ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE
DEVICE_ID=
PORT=8080
SESSION_DATA_DIR=/app/sessions
```

3. **启动服务**

```bash
docker-compose up -d
```

服务将在 `http://localhost:8080` 启动。会话数据会自动持久化到 Docker 卷。

4. **查看日志**

```bash
docker-compose logs -f
```

5. **停止服务**

```bash
docker-compose down
```

### 手动 Docker 部署

1. **构建镜像**

```bash
docker build -t wenxiaobai-openai-proxy .
```

2. **运行容器（挂载会话数据卷）**

```bash
docker run -d \
  -p 8080:8080 \
  -e API_USERNAME="web.1.0.beta" \
  -e API_SECRET_KEY="TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z" \
  -e ACCESS_TOKEN="YOUR_ACCESS_TOKEN_HERE" \
  -e PORT="8080" \
  -e SESSION_DATA_DIR="/app/sessions" \
  -v wenxiaobai-sessions:/app/sessions \
  --name wenxiaobai-proxy \
  wenxiaobai-openai-proxy
```

3. **查看自动生成的 DEVICE_ID**

```bash
docker logs wenxiaobai-proxy
```

会看到类似输出：
```
[INFO] 自动生成 DEVICE_ID: 1234567890123456789_1234567890123_123456
```

### 数据持久化说明

- **会话数据保存路径**: `/app/sessions/sessions.json`
- **数据卷名称**: `wenxiaobai-sessions`（Docker Compose 自动创建）
- **容器重启后**: 会话数据会自动恢复

### Zeabur 部署

如果使用 Zeabur 部署：

1. 推送代码到 Git 仓库
2. 在 Zeabur 中创建新服务，选择 Dockerfile
3. 添加环境变量：
   ```
   ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE
   ```
4. Zeabur 会自动：
   - 生成 DEVICE_ID
   - 挂载持久化存储
   - 暴露端口

### 环境变量说明

| 变量名 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| `API_USERNAME` | 否 | HMAC 认证用户名 | `web.1.0.beta` |
| `API_SECRET_KEY` | 否 | HMAC 认证密钥 | `TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z` |
| `ACCESS_TOKEN` | **是** | 用户身份令牌 | - |
| `DEVICE_ID` | 否 | 设备ID（自动生成） | 自动生成 |
| `PORT` | 否 | 服务端口 | `8080` |
| `SESSION_DATA_DIR` | 否 | 会话数据存储目录 | `/app/sessions` |

## 项目结构

```
weixiaobai/
├── main.py                      # Flask 主应用
├── wenxiaobai_client.py         # 文小白 API 客户端
├── test_openai_client.py        # OpenAI 兼容测试客户端
├── requirements.txt             # Python 依赖
├── .env.example                # 环境变量示例
├── Dockerfile                  # Docker 配置
└── README.md                   # 项目文档
```

## 技术栈

- **Python 3.8+**
- **Flask** - Web 框架
- **Requests** - HTTP 客户端
- **python-dotenv** - 环境变量管理

## 注意事项

1. **API 密钥**: 文小白 API 不需要真实的 OpenAI API 密钥，但为了兼容性，客户端可以传递任意字符串作为 `api_key`。

2. **流式响应**: 默认使用流式响应，可以设置 `stream: false` 来获取非流式响应。

3. **模型选择**: 确保使用正确的模型名称，可用的模型列表可以通过 `/v1/models` 端点获取。

4. **错误处理**: API 返回的错误格式完全符合 OpenAI 规范，包含 `error.type`、`error.message` 等字段。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 Issue 或联系项目维护者。
