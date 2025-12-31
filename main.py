import os
import json
import time
import uuid
import requests
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify, Response, g, session
from dotenv import load_dotenv
from wenxiaobai_client import create_wenxiaobai_client, MODEL_MAP, MODEL_ABILITIES
from pathlib import Path
from logging_system import RequestLogger, APIDebugLogger
from user_management import user_bp
from database import db
from functools import wraps

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")

# 注册用户管理蓝图
app.register_blueprint(user_bp)

# Initialize logging system
request_logger = RequestLogger()
api_debug_logger = APIDebugLogger()

# API Key验证装饰器
def require_api_key(f):
    """API Key验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取Authorization头
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify(format_openai_error_response(
                "invalid_request_error",
                "Missing Authorization header",
                request_id=getattr(g, 'request_id', 'unknown')
            )), 401
        
        # 解析Bearer token
        if not auth_header.startswith('Bearer '):
            return jsonify(format_openai_error_response(
                "invalid_request_error",
                "Invalid Authorization header format",
                request_id=getattr(g, 'request_id', 'unknown')
            )), 401
        
        api_key = auth_header[7:]  # 移除 "Bearer " 前缀
        
        # 验证API Key
        user_info = db.get_user_by_api_key(api_key)
        if not user_info:
            return jsonify(format_openai_error_response(
                "invalid_request_error",
                "Invalid API key",
                request_id=getattr(g, 'request_id', 'unknown')
            )), 401
        
        # 获取用户的活跃token
        token_info = db.get_active_token_for_user(user_info['user_id'])
        if not token_info:
            return jsonify(format_openai_error_response(
                "invalid_request_error",
                "No active token found for user",
                request_id=getattr(g, 'request_id', 'unknown')
            )), 400
        
        # 将用户信息和token信息存储到g对象中
        g.user_info = user_info
        g.token_info = token_info
        g.api_key = api_key
        
        return f(*args, **kwargs)
    return decorated_function
@app.before_request
def log_request_start():
    """Log incoming request and generate correlation ID."""
    # Get client IP (handle proxy headers)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    # Generate request ID and store in Flask's g object for request duration
    request_id = request_logger.log_incoming_request(
        request=request,
        endpoint=request.endpoint or request.path,
        client_ip=client_ip or 'unknown'
    )
    
    # Store request metadata in Flask's g object
    g.request_id = request_id
    g.request_start_time = time.time()
    g.client_ip = client_ip or 'unknown'
    
    # Log request parameters for POST requests
    if request.method == 'POST' and request.is_json:
        try:
            request_data = request.get_json()
            request_logger.log_request_parameters(
                data=request_data or {},
                headers=dict(request.headers),
                request_id=request_id
            )
        except Exception as e:
            # Log error but don't fail the request
            request_logger.logger.warning(f"[{request_id}] Failed to log request parameters: {e}")

@app.after_request
def log_request_end(response):
    """Log request completion and timing."""
    if hasattr(g, 'request_id') and hasattr(g, 'request_start_time'):
        end_time = time.time()
        request_logger.log_request_timing(
            start_time=g.request_start_time,
            end_time=end_time,
            request_id=g.request_id
        )
        
        # Log response status
        request_logger.logger.info(
            f"[{g.request_id}] Response sent - Status: {response.status_code}, "
            f"Content-Type: {response.headers.get('Content-Type', 'unknown')}"
        )
    
    return response

@app.errorhandler(Exception)
def log_request_error(error):
    """Log request errors with correlation ID."""
    if hasattr(g, 'request_id'):
        request_logger.logger.error(
            f"[{g.request_id}] Request failed with error: {str(error)}"
        )
        
        # Log detailed error in debug mode
        if request_logger.logger.isEnabledFor(logging.DEBUG):
            import traceback
            request_logger.logger.debug(
                f"[{g.request_id}] Error traceback: {traceback.format_exc()}"
            )
    
    # Return appropriate error response
    return jsonify({
        "error": {
            "message": "Internal server error",
            "type": "internal_server_error",
            "request_id": getattr(g, 'request_id', 'unknown')
        }
    }), 500

# 从环境变量中读取系统配置
try:
    api_username = os.environ.get("API_USERNAME", "web.1.0.beta")
    api_secret_key = os.environ.get("API_SECRET_KEY", "TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z")
    
    # DEVICE_ID 自动生成（如果未设置）
    device_id = os.environ.get("DEVICE_ID")
    if not device_id:
        random_num = str(random.randint(1000000000000000000, 9999999999999999999))
        timestamp = str(int(datetime.now().timestamp() * 1000))
        device_id = f"{random_num}_{timestamp}_{str(random.randint(100000, 999999))}"
        print(f"[INFO] 自动生成 DEVICE_ID: {device_id}")
        
    print(f"[INFO] 系统配置加载完成")
    print(f"[INFO] API_USERNAME: {api_username}")
    print(f"[INFO] DEVICE_ID: {device_id}")
    
except Exception as e:
    print(f"[ERROR] 系统配置加载失败: {e}")
    # 使用默认配置
    api_username = "web.1.0.beta"
    api_secret_key = "TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z"
    device_id = f"{random.randint(1000000000000000000, 9999999999999999999)}_{int(datetime.now().timestamp() * 1000)}_{random.randint(100000, 999999)}"

# 目录配置
SESSION_DATA_DIR = os.environ.get("SESSION_DATA_DIR", "./sessions")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "./wenxiaobai_users.db")
LOG_DIR = os.environ.get("LOG_DIR", "./logs")

# 创建必要的目录
Path(SESSION_DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# 确保数据库目录存在
database_dir = os.path.dirname(DATABASE_PATH)
if database_dir:
    Path(database_dir).mkdir(parents=True, exist_ok=True)

session_storage_file = os.path.join(SESSION_DATA_DIR, "sessions.json")

def load_sessions():
    """从文件加载会话数据"""
    try:
        if os.path.exists(session_storage_file):
            with open(session_storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARNING] 加载会话数据失败: {e}")
    return {}

def save_sessions(sessions_data):
    """保存会话数据到文件"""
    try:
        with open(session_storage_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARNING] 保存会话数据失败: {e}")

# 会话管理：加载已保存的会话数据
# 格式: {session_id: {"conversation_id": str, "turn_index": int}}
sessions = load_sessions()

# 默认会话ID：当客户端不传递session_id时使用
DEFAULT_SESSION_ID = "default-session"

# 当前默认会话ID（当达到对话上限时会自动更新）
current_default_session_id = DEFAULT_SESSION_ID

def update_session(session_id, conversation_id, turn_index):
    """更新会话数据并保存到文件"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Log session update operation
    request_logger.logger.info(
        f"[{request_id}] Session update - ID: {session_id}, "
        f"ConvID: {conversation_id}, Turn: {turn_index}"
    )
    
    old_session = sessions.get(session_id, {})
    old_conv_id = old_session.get("conversation_id")
    old_turn = old_session.get("turn_index", 0)
    
    sessions[session_id] = {
        "conversation_id": conversation_id,
        "turn_index": turn_index
    }
    
    try:
        save_sessions(sessions)
        request_logger.logger.debug(
            f"[{request_id}] Session saved successfully - "
            f"Changed from ConvID: {old_conv_id}, Turn: {old_turn} "
            f"to ConvID: {conversation_id}, Turn: {turn_index}"
        )
    except Exception as e:
        request_logger.logger.error(
            f"[{request_id}] Failed to save session {session_id}: {e}"
        )
        raise
    
    print(f"[SESSION] 更新会话: session_id={session_id}, conversation_id={conversation_id}, turn_index={turn_index}")

# --- OpenAI 格式化辅助函数 ---
def format_openai_stream_chunk(chat_id, model, content, finish_reason=None):
    """格式化 OpenAI 兼容的流式响应块"""
    chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content else {},
            "finish_reason": finish_reason
        }]
    }
    return f"data: {json.dumps(chunk)}\n\n"

def format_openai_stream_stop_chunk(chat_id, model):
    """格式化 OpenAI 兼容的流式响应结束块"""
    return format_openai_stream_chunk(chat_id, model, None, "stop") + "data: [DONE]\n\n"

def format_openai_non_streaming_response(chat_id, model, content):
    """格式化 OpenAI 兼容的非流式响应"""
    response = {
        "id": chat_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
    return response

def format_openai_error_response(error_type, message, code=None, request_id=None):
    """格式化 OpenAI 兼容的错误响应"""
    error_response = {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": code
        }
    }
    
    # Add request ID if available for correlation
    if request_id:
        error_response["request_id"] = request_id
    
    return error_response

def extract_query_from_messages(messages):
    """从 OpenAI 格式的 messages 中提取查询内容"""
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Log query extraction process
    request_logger.logger.debug(f"[{request_id}] Extracting query from {len(messages) if messages else 0} messages")
    
    if not messages or not isinstance(messages, list):
        request_logger.logger.warning(f"[{request_id}] Invalid messages format: {type(messages)}")
        return None
    
    # 获取最后一条消息
    last_message = messages[-1]
    request_logger.logger.debug(f"[{request_id}] Processing last message: {type(last_message)}")
    
    # 处理不同的消息格式
    if isinstance(last_message, dict):
        content = last_message.get("content")
        
        # 如果 content 是字符串，直接返回
        if isinstance(content, str):
            query_preview = content[:100] + "..." if len(content) > 100 else content
            request_logger.logger.info(f"[{request_id}] Extracted text query: '{query_preview}'")
            return content
        
        # 如果 content 是列表（多模态消息），提取文本内容
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            
            result = "".join(text_parts) if text_parts else None
            if result:
                query_preview = result[:100] + "..." if len(result) > 100 else result
                request_logger.logger.info(f"[{request_id}] Extracted multimodal query: '{query_preview}'")
            else:
                request_logger.logger.warning(f"[{request_id}] No text content found in multimodal message")
            return result
    
    request_logger.logger.warning(f"[{request_id}] Could not extract query from message format")
    return None

@app.route('/v1/chat/completions', methods=['POST'])
@require_api_key
def chat_completions_endpoint():
    """
    兼容标准 OpenAI 的聊天 API 端点
    完全符合 OpenAI Chat Completions API 规范
    """
    global current_default_session_id  # 声明使用全局变量
    
    # 解析请求
    data = request.get_json()
    if not data:
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            "请求体必须是有效的 JSON"
        )), 400
    
    # 获取参数
    model = data.get("model", "wenxiaobai-deep-thought")
    messages = data.get("messages", [])
    stream = data.get("stream", True)
    temperature = data.get("temperature", 1.0)
    max_tokens = data.get("max_tokens", None)
    top_p = data.get("top_p", 1.0)
    
    # Log request parameters
    request_id = getattr(g, 'request_id', 'unknown')
    request_logger.logger.info(
        f"[{request_id}] Chat request parameters - Model: {model}, "
        f"Messages: {len(messages)}, Stream: {stream}, Temp: {temperature}"
    )
    
    # 模型兼容性处理：如果模型不在MODEL_MAP中，使用默认模型deepseekV3_2
    DEFAULT_MODEL_ID = "deepseekV3_2"  # 设置默认模型为ds3.2
    original_model = model
    if model not in MODEL_MAP:
        model = next((k for k, v in MODEL_MAP.items() if v == DEFAULT_MODEL_ID), "wenxiaobai-deep-thought")
        request_logger.logger.warning(
            f"[{request_id}] Model fallback - '{original_model}' not found, "
            f"using '{model}' (mapped to {MODEL_MAP.get(model, 'unknown')})"
        )
        print(f"[MODEL] 模型 '{original_model}' 不存在，自动回退到默认模型 '{DEFAULT_MODEL_ID}'")
    else:
        request_logger.logger.info(
            f"[{request_id}] Model validation passed - '{model}' "
            f"(mapped to {MODEL_MAP.get(model, 'unknown')})"
        )
    
    # 会话管理：尝试复用已有会话
    # 如果客户端不传递session_id，使用当前默认session_id，这样所有请求都在同一会话中
    provided_session_id = data.get("session_id")
    if provided_session_id:
        session_id = provided_session_id
        request_logger.logger.info(f"[{request_id}] Using provided session ID: {session_id}")
    else:
        # 使用当前默认会话ID
        session_id = current_default_session_id
        request_logger.logger.info(f"[{request_id}] Using default session ID: {session_id}")
    
    session_info = sessions.get(session_id, {"conversation_id": None, "turn_index": 0})
    conversation_id = session_info["conversation_id"]
    turn_index = session_info["turn_index"]
    
    request_logger.logger.debug(
        f"[{request_id}] Session state - ID: {session_id}, "
        f"ConvID: {conversation_id}, Turn: {turn_index}"
    )
    
    # 检测会话是否可能达到上限（turn_index >= 10时自动创建新会话）
    if conversation_id is not None and turn_index >= 10:
        request_logger.logger.warning(
            f"[{request_id}] Session limit reached - Turn index {turn_index} >= 10, "
            f"creating new session"
        )
        print(f"[AUTO_NEW] 会话可能达到上限（turn_index={turn_index}），自动创建新会话")
        conversation_id = None
        turn_index = 0
        
        # 如果是默认会话，生成新的默认会话ID
        if session_id == current_default_session_id:
            new_default_session_id = f"default-session-{int(time.time())}"
            request_logger.logger.info(
                f"[{request_id}] Default session rotation - "
                f"{current_default_session_id} -> {new_default_session_id}"
            )
            print(f"[AUTO_NEW] 默认会话切换: {current_default_session_id} -> {new_default_session_id}")
            current_default_session_id = new_default_session_id
            session_id = new_default_session_id
    
    # 决定是否需要新建会话
    is_new_conversation = conversation_id is None
    
    request_logger.logger.info(
        f"[{request_id}] Session decision - ID: {session_id}, "
        f"ConvID: {conversation_id}, Turn: {turn_index}, New: {is_new_conversation}"
    )
    
    print(f"[REQUEST] 收到请求: session_id={session_id}, conversation_id={conversation_id}, turn_index={turn_index}, is_new={is_new_conversation}, model={model}")
    
    # 验证消息
    if not messages:
        error_msg = "请求中缺少 'messages' 字段"
        request_logger.logger.error(
            f"[{request_id}] Validation error - {error_msg}"
        )
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            error_msg
        )), 400
    
    # 提取查询内容
    query = extract_query_from_messages(messages)
    if not query:
        error_msg = "无法从消息中提取有效的查询内容"
        request_logger.logger.error(
            f"[{request_id}] Query extraction error - {error_msg}, "
            f"Messages format: {type(messages)}, Count: {len(messages)}"
        )
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            error_msg
        )), 400
    
    try:
        # 使用用户的token创建客户端
        user_token = g.token_info['token']
        user_device_id = g.token_info['device_id'] or device_id
        
        # 创建用户专用的API客户端
        user_client = create_wenxiaobai_client(
            username=api_username,
            secret_key=api_secret_key,
            access_token=user_token,
            device_id=user_device_id
        )
        
        # 调用 API，传递 conversation_id 和 turn_index（会话复用逻辑在客户端处理）
        # is_new_conversation 决定是否新建对话
        api_call_id = api_debug_logger.log_api_call_parameters(
            model=model,
            query=query,
            conversation_id=conversation_id,
            abilities=MODEL_ABILITIES.get(model, {}).get("abilities", []),
            request_id=request_id,
            turn_index=turn_index,
            is_new_conversation=is_new_conversation
        )
        
        print(f"[API] 调用文小白API: query='{query[:50]}...', model={model}, conversation_id={conversation_id}, turn_index={turn_index}, is_new_conversation={is_new_conversation}")
        
        start_time = time.time()
        response = user_client.chat(
            query,
            model=model,
            conversation_id=conversation_id,
            turn_index=turn_index,
            is_new_conversation=is_new_conversation
        )
        api_timing = time.time() - start_time
        
        # 记录使用情况和API调用计数
        db.log_usage(
            user_id=g.user_info['user_id'],
            api_key_id=g.user_info['api_key_id'],
            token_id=g.token_info['id'],
            model=model,
            request_id=request_id
        )
        
        # 增加API调用计数
        api_calls_today = db.increment_api_calls(g.token_info['id'])
        
        # 检查是否需要触发任务系统
        if api_calls_today % 50 == 0:  # 每50次调用检查一次
            from task_system import task_system
            from balance_checker import balance_checker
            
            # 检查余额
            balance_result = balance_checker.check_balance(
                g.token_info['token'], 
                g.token_info['device_id']
            )
            
            if balance_result and balance_result.get('success'):
                current_balance = balance_result.get('suanli_balance', 0)
                db.update_token_balance(g.token_info['id'], current_balance)
                
                # 如果余额低于10且启用了自动任务
                tokens = db.get_user_tokens(g.user_info['user_id'])
                token_info = next((t for t in tokens if t['id'] == g.token_info['id']), None)
                
                if (token_info and token_info.get('auto_task_enabled') and 
                    current_balance < 10):
                    
                    logger.info(f"Triggering auto tasks for token {g.token_info['id']} due to low balance: {current_balance}")
                    
                    # 异步执行任务（避免阻塞API响应）
                    import threading
                    def run_tasks():
                        try:
                            task_result = task_system.auto_complete_tasks_for_token(token_info)
                            if task_result.get('success'):
                                logger.info(f"Auto tasks completed for token {g.token_info['id']}: {task_result.get('task_count')} tasks, {task_result.get('total_rewards')} rewards")
                        except Exception as e:
                            logger.error(f"Auto task execution failed for token {g.token_info['id']}: {e}")
                    
                    threading.Thread(target=run_tasks, daemon=True).start()
        
        print(f"[API] API响应状态: {response.status_code if response else 'None'}")
        
        if response is None:
            error_msg = "API 请求失败，无响应"
            api_debug_logger.log_api_error(
                error_details=error_msg,
                request_id=request_id
            )
            request_logger.logger.error(f"[{request_id}] {error_msg}")
            return jsonify(format_openai_error_response(
                "api_error",
                error_msg
            )), 502
        
        # Log API response
        api_debug_logger.log_api_response(
            status_code=response.status_code,
            headers=dict(response.headers),
            request_id=request_id,
            timing=api_timing
        )
        
        # 检查响应状态
        if response.status_code != 200:
            error_details = response.text if response.text else "无错误详情"
            api_debug_logger.log_api_error(
                error_details=f"API returned status {response.status_code}: {error_details}",
                status_code=response.status_code,
                request_id=request_id
            )
            request_logger.logger.error(
                f"[{request_id}] API error - Status: {response.status_code}, "
                f"Details: {error_details[:200]}..."
            )
            print(f"[ERROR] API返回错误: status={response.status_code}, details={error_details[:500]}")
            
            # 检查是否为对话上限错误，如果是则尝试新建会话重试
            if response.status_code == 400 and conversation_id is not None:
                request_logger.logger.warning(
                    f"[{request_id}] Detected conversation limit error, attempting retry with new session"
                )
                print(f"[RETRY] 检测到400错误（对话上限），尝试新建会话重试...")
                
                # 如果是默认会话，生成新的默认会话ID
                if session_id == current_default_session_id:
                    new_default_session_id = f"default-session-{int(time.time())}"
                    request_logger.logger.info(
                        f"[{request_id}] Session limit retry - "
                        f"{current_default_session_id} -> {new_default_session_id}"
                    )
                    print(f"[RETRY] 默认会话达到上限，切换到新会话: {current_default_session_id} -> {new_default_session_id}")
                    current_default_session_id = new_default_session_id
                    session_id = new_default_session_id
                
                # 重置会话，新建对话
                conversation_id = None
                turn_index = 0
                
                # Retry API call
                retry_start_time = time.time()
                response = client.chat(
                    query,
                    model=deployment_name,
                    conversation_id=None,
                    turn_index=0,
                    is_new_conversation=True
                )
                retry_timing = time.time() - retry_start_time
                
                print(f"[RETRY] 重试后状态: {response.status_code if response else 'None'}")
                
                if response is None:
                    error_msg = "API 重试请求失败，无响应"
                    api_debug_logger.log_api_error(
                        error_details=error_msg,
                        request_id=request_id
                    )
                    request_logger.logger.error(f"[{request_id}] {error_msg}")
                    return jsonify(format_openai_error_response(
                        "api_error",
                        error_msg
                    )), 502
                
                # Log retry response
                api_debug_logger.log_api_response(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    request_id=request_id,
                    timing=retry_timing
                )
                
                if response.status_code != 200:
                    retry_error = response.text if response.text else "无错误详情"
                    api_debug_logger.log_api_error(
                        error_details=f"API retry failed with status {response.status_code}: {retry_error}",
                        status_code=response.status_code,
                        request_id=request_id
                    )
                    request_logger.logger.error(
                        f"[{request_id}] API retry failed - Status: {response.status_code}"
                    )
                    return jsonify(format_openai_error_response(
                        "api_error",
                        f"上游 API 返回错误: {response.status_code}",
                        str(response.status_code)
                    )), 502
            else:
                return jsonify(format_openai_error_response(
                    "api_error",
                    f"上游 API 返回错误: {response.status_code}",
                    str(response.status_code)
                )), 502
        
        # 检查内容类型
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' not in content_type:
            return jsonify(format_openai_error_response(
                "api_error",
                "上游 API 未返回事件流",
                "invalid_content_type"
            )), 502
        
        # 根据 stream 参数决定返回流式响应还是非流式响应
        if stream:
            # 生成流式响应
            def generate_stream():
                chat_id = f"chatcmpl-{uuid.uuid4()}"
                received_conversation_id = False
                current_turn_index = turn_index
                
                try:
                    for line_bytes in response.iter_lines():
                        if line_bytes:
                            line = line_bytes.decode('utf-8')
                            
                            # 处理 SSE 事件格式
                            if line.startswith('event:'):
                                current_event = line[6:].strip()
                                continue
                            
                            if line.startswith('data:'):
                                json_str = line[5:].strip()
                                
                                # 跳过空行和 [DONE]
                                if not json_str or json_str == '[DONE]':
                                    continue
                                
                                try:
                                    event_data = json.loads(json_str)
                                    
                                    # 调试：打印所有事件数据
                                    if any(key in event_data for key in ['conversationId', 'conversationId', 'id']):
                                        print(f"[DEBUG] Event data: {json.dumps(event_data, ensure_ascii=False)[:200]}")
                                    
                                    # 从事件中提取 conversationId（尝试多种可能的字段名）
                                    conv_id = event_data.get('conversationId') or event_data.get('conversationId') or event_data.get('id')
                                    if conv_id and not received_conversation_id:
                                        print(f"[STREAM] 收到conversationId: {conv_id}")
                                        if conv_id:
                                            # 更新会话信息（使用当前 turn_index + 1，因为这是新的对话轮次）
                                            current_turn_index += 1
                                            update_session(session_id, conv_id, current_turn_index)
                                        received_conversation_id = True
                                    
                                    content = event_data.get('content')
                                    
                                    if isinstance(content, str) and content:
                                        yield format_openai_stream_chunk(chat_id, model, content)
                                except json.JSONDecodeError:
                                    continue
                                except Exception:
                                    continue
                except Exception as e:
                    print(f"[ERROR] 流式响应生成器错误: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 对话结束后更新 turn_index（如果还没更新）
                if session_id in sessions and not received_conversation_id:
                    old_turn = sessions[session_id]["turn_index"]
                    sessions[session_id]["turn_index"] += 1
                    save_sessions(sessions)
                    print(f"[SESSION] 对话结束更新turn_index: {old_turn} -> {sessions[session_id]['turn_index']}")
                
                # 发送结束标记
                yield format_openai_stream_stop_chunk(chat_id, model)
            
            return Response(generate_stream(), content_type='text/event-stream')
        else:
            # 非流式响应：收集所有内容并返回完整响应
            chat_id = f"chatcmpl-{uuid.uuid4()}"
            full_content = []
            received_conversation_id = False
            current_turn_index = turn_index  # 保存当前 turn_index 用于更新
            
            for line_bytes in response.iter_lines():
                if line_bytes:
                    line = line_bytes.decode('utf-8')
                    
                    # 处理 SSE 事件格式
                    if line.startswith('event:'):
                        continue
                    
                    if line.startswith('data:'):
                        json_str = line[5:].strip()
                        
                        # 跳过空行和 [DONE]
                        if not json_str or json_str == '[DONE]':
                            continue
                        
                        try:
                            event_data = json.loads(json_str)
                            
                            # 从事件中提取 conversationId
                            if 'conversationId' in event_data and not received_conversation_id:
                                new_conversation_id = event_data['conversationId']
                                if new_conversation_id:
                                    # 更新会话信息
                                    current_turn_index += 1
                                    update_session(session_id, new_conversation_id, current_turn_index)
                                received_conversation_id = True
                            
                            content = event_data.get('content')
                            
                            if isinstance(content, str) and content:
                                full_content.append(content)
                        except json.JSONDecodeError:
                            continue
                        except Exception:
                            continue
            
            # 对话结束后更新 turn_index（如果还没更新）
            if session_id in sessions and not received_conversation_id:
                sessions[session_id]["turn_index"] += 1
                save_sessions(sessions)
            
            # 组合所有内容
            complete_response = format_openai_non_streaming_response(
                chat_id, 
                model, 
                ''.join(full_content)
            )
            
            return jsonify(complete_response)
    
    except Exception as e:
        # Enhanced error logging with correlation ID
        request_id = getattr(g, 'request_id', 'unknown')
        api_debug_logger.log_api_error(
            error_details=f"Internal server error: {str(e)}",
            request_id=request_id,
            exception=e
        )
        request_logger.logger.error(
            f"[{request_id}] Internal server error in chat completions: {str(e)}"
        )
        
        # Log stack trace in debug mode
        if request_logger.logger.isEnabledFor(logging.DEBUG):
            import traceback
            request_logger.logger.debug(
                f"[{request_id}] Stack trace: {traceback.format_exc()}"
            )
        
        return jsonify(format_openai_error_response(
            "internal_server_error",
            f"内部服务器错误: {str(e)}",
            request_id
        )), 500

@app.route('/v1/deployments/<deployment_name>/chat/completions', methods=['POST'])
@require_api_key
def azure_chat_completions_endpoint(deployment_name):
    """
    兼容 Azure OpenAI 的聊天 API 端点
    完全符合 Azure OpenAI Chat Completions API 规范
    """
    global current_default_session_id  # 声明使用全局变量
    
    # 解析请求
    data = request.get_json()
    if not data:
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            "请求体必须是有效的 JSON"
        )), 400
    
    # 获取参数
    messages = data.get("messages", [])
    stream = data.get("stream", True)
    temperature = data.get("temperature", 1.0)
    max_tokens = data.get("max_tokens", None)
    top_p = data.get("top_p", 1.0)
    
    # 模型兼容性处理：如果模型不在MODEL_MAP中，使用默认模型deepseekV3_2
    DEFAULT_MODEL_ID = "deepseekV3_2"  # 设置默认模型为ds3.2
    if deployment_name not in MODEL_MAP:
        print(f"[MODEL] 部署名称 '{deployment_name}' 不存在，自动回退到默认模型 '{DEFAULT_MODEL_ID}'")
        deployment_name = next((k for k, v in MODEL_MAP.items() if v == DEFAULT_MODEL_ID), "wenxiaobai-deep-thought")
    
    # 会话管理：尝试复用已有会话
    # 如果客户端不传递session_id，使用当前默认session_id，这样所有请求都在同一会话中
    provided_session_id = data.get("session_id")
    if provided_session_id:
        session_id = provided_session_id
    else:
        # 使用当前默认会话ID
        session_id = current_default_session_id
    
    session_info = sessions.get(session_id, {"conversation_id": None, "turn_index": 0})
    conversation_id = session_info["conversation_id"]
    turn_index = session_info["turn_index"]
    
    # 检测会话是否可能达到上限（turn_index >= 10时自动创建新会话）
    if conversation_id is not None and turn_index >= 10:
        print(f"[AUTO_NEW] 会话可能达到上限（turn_index={turn_index}），自动创建新会话")
        conversation_id = None
        turn_index = 0
        
        # 如果是默认会话，生成新的默认会话ID
        if session_id == current_default_session_id:
            new_default_session_id = f"default-session-{int(time.time())}"
            print(f"[AUTO_NEW] 默认会话切换: {current_default_session_id} -> {new_default_session_id}")
            current_default_session_id = new_default_session_id
            session_id = new_default_session_id
    
    # 决定是否需要新建会话
    is_new_conversation = conversation_id is None
    
    # 验证消息
    if not messages:
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            "请求中缺少 'messages' 字段"
        )), 400
    
    # 提取查询内容
    query = extract_query_from_messages(messages)
    if not query:
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            "无法从消息中提取有效的查询内容"
        )), 400
    
    try:
        # 使用用户的token创建客户端
        user_token = g.token_info['token']
        user_device_id = g.token_info['device_id'] or device_id
        
        # 创建用户专用的API客户端
        user_client = create_wenxiaobai_client(
            username=api_username,
            secret_key=api_secret_key,
            access_token=user_token,
            device_id=user_device_id
        )
        
        # 调用 API，传递 conversation_id 和 turn_index（会话复用逻辑在客户端处理）
        response = user_client.chat(
            query,
            model=deployment_name,
            conversation_id=conversation_id,
            turn_index=turn_index,
            is_new_conversation=is_new_conversation
        )
        
        if response is None:
            return jsonify(format_openai_error_response(
                "api_error",
                "API 请求失败，无响应"
            )), 502
        
        # 检查响应状态
        if response.status_code != 200:
            error_details = response.text if response.text else "无错误详情"
            
            # 检查是否为对话上限错误，如果是则尝试新建会话重试
            if response.status_code == 400 and conversation_id is not None:
                print(f"[RETRY] 检测到400错误（对话上限），尝试新建会话重试...")
                
                # 如果是默认会话，生成新的默认会话ID
                if session_id == current_default_session_id:
                    new_default_session_id = f"default-session-{int(time.time())}"
                    print(f"[RETRY] 默认会话达到上限，切换到新会话: {current_default_session_id} -> {new_default_session_id}")
                    current_default_session_id = new_default_session_id
                    session_id = new_default_session_id
                
                # 重置会话，新建对话
                conversation_id = None
                turn_index = 0
                response = user_client.chat(
                    query,
                    model=deployment_name,
                    conversation_id=None,
                    turn_index=0,
                    is_new_conversation=True
                )
                
                if response is None:
                    return jsonify(format_openai_error_response(
                        "api_error",
                        "API 请求失败，无响应"
                    )), 502
                
                if response.status_code != 200:
                    return jsonify(format_openai_error_response(
                        "api_error",
                        f"上游 API 返回错误: {response.status_code}",
                        str(response.status_code)
                    )), 502
            else:
                return jsonify(format_openai_error_response(
                    "api_error",
                    f"上游 API 返回错误: {response.status_code}",
                    str(response.status_code)
                )), 502
        
        # 检查内容类型
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' not in content_type:
            return jsonify(format_openai_error_response(
                "api_error",
                "上游 API 未返回事件流",
                "invalid_content_type"
            )), 502
        
        # 根据 stream 参数决定返回流式响应还是非流式响应
        if stream:
            # 生成流式响应
            def generate_stream():
                chat_id = f"chatcmpl-{uuid.uuid4()}"
                received_conversation_id = False
                current_turn_index = turn_index  # 保存当前 turn_index 用于更新
                
                for line_bytes in response.iter_lines():
                    if line_bytes:
                        line = line_bytes.decode('utf-8')
                        
                        # 处理 SSE 事件格式
                        if line.startswith('event:'):
                            continue
                        
                        if line.startswith('data:'):
                            json_str = line[5:].strip()
                            
                            # 跳过空行和 [DONE]
                            if not json_str or json_str == '[DONE]':
                                continue
                            
                            try:
                                event_data = json.loads(json_str)
                                
                                # 从事件中提取 conversationId
                                if 'conversationId' in event_data and not received_conversation_id:
                                    new_conversation_id = event_data['conversationId']
                                    if new_conversation_id:
                                        # 更新会话信息
                                        current_turn_index += 1
                                        update_session(session_id, new_conversation_id, current_turn_index)
                                    received_conversation_id = True
                                
                                content = event_data.get('content')
                                
                                if isinstance(content, str) and content:
                                    yield format_openai_stream_chunk(chat_id, deployment_name, content)
                            except json.JSONDecodeError:
                                continue
                            except Exception:
                                continue
                
                # 对话结束后更新 turn_index（如果还没更新）
                if session_id in sessions and not received_conversation_id:
                    sessions[session_id]["turn_index"] += 1
                    save_sessions(sessions)
                
                # 发送结束标记
                yield format_openai_stream_stop_chunk(chat_id, deployment_name)
            
            return Response(generate_stream(), content_type='text/event-stream')
        else:
            # 非流式响应：收集所有内容并返回完整响应
            chat_id = f"chatcmpl-{uuid.uuid4()}"
            full_content = []
            received_conversation_id = False
            current_turn_index = turn_index  # 保存当前 turn_index 用于更新
            
            for line_bytes in response.iter_lines():
                if line_bytes:
                    line = line_bytes.decode('utf-8')
                    
                    # 处理 SSE 事件格式
                    if line.startswith('event:'):
                        continue
                    
                    if line.startswith('data:'):
                        json_str = line[5:].strip()
                        
                        # 跳过空行和 [DONE]
                        if not json_str or json_str == '[DONE]':
                            continue
                        
                        try:
                            event_data = json.loads(json_str)
                            
                            # 从事件中提取 conversationId
                            if 'conversationId' in event_data and not received_conversation_id:
                                new_conversation_id = event_data['conversationId']
                                if new_conversation_id:
                                    # 更新会话信息
                                    current_turn_index += 1
                                    update_session(session_id, new_conversation_id, current_turn_index)
                                received_conversation_id = True
                            
                            content = event_data.get('content')
                            
                            if isinstance(content, str) and content:
                                full_content.append(content)
                        except json.JSONDecodeError:
                            continue
                        except Exception:
                            continue
            
            # 对话结束后更新 turn_index（如果还没更新）
            if session_id in sessions and not received_conversation_id:
                sessions[session_id]["turn_index"] += 1
                save_sessions(sessions)
            
            # 组合所有内容
            complete_response = format_openai_non_streaming_response(
                chat_id,
                deployment_name,
                ''.join(full_content)
            )
            
            return jsonify(complete_response)
    
    except Exception as e:
        return jsonify(format_openai_error_response(
            "internal_server_error",
            f"内部服务器错误: {str(e)}"
        )), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    """
    列出所有可用模型
    完全符合 OpenAI Models API 规范
    """
    model_data = []
    
    for model_name, model_config in MODEL_ABILITIES.items():
        model_info = {
            "id": model_name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "wenxiaobai",
            "permission": [],
            "root": model_name,
            "parent": None,
            "description": model_config.get("description", "")
        }
        model_data.append(model_info)
    
    return jsonify({
        "object": "list",
        "data": model_data
    })

@app.route('/v1/models/<model_id>', methods=['GET'])
def get_model(model_id):
    """
    获取特定模型信息
    完全符合 OpenAI Models API 规范
    """
    if model_id not in MODEL_ABILITIES:
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            f"模型 '{model_id}' 不存在"
        )), 404
    
    model_config = MODEL_ABILITIES[model_id]
    model_info = {
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "wenxiaobai",
        "permission": [],
        "root": model_id,
        "parent": None,
        "description": model_config.get("description", "")
    }
    
    return jsonify(model_info)

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": "wenxiaobai-openai-proxy",
        "version": "1.0.0"
    }), 200

@app.route('/', methods=['GET'])
def root():
    """根路径，重定向到登录页面"""
    return app.send_static_file('login.html')

@app.route('/login.html', methods=['GET'])
def login_page():
    """登录页面"""
    return app.send_static_file('login.html')

@app.route('/register.html', methods=['GET'])
def register_page():
    """注册页面"""
    return app.send_static_file('register.html')

@app.route('/dashboard.html', methods=['GET'])
def dashboard_page():
    """用户控制台页面"""
    return app.send_static_file('dashboard.html')

@app.route('/admin.html', methods=['GET'])
def admin_page():
    """管理员控制台页面"""
    return app.send_static_file('admin.html')

@app.route('/debug_frontend.html', methods=['GET'])
def debug_page():
    """调试页面"""
    return app.send_static_file('debug_frontend.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
