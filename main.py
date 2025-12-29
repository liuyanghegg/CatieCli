import os
import json
import time
import uuid
import requests
import random
from datetime import datetime
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from wenxiaobai_client import create_wenxiaobai_client, MODEL_MAP, MODEL_ABILITIES
from pathlib import Path

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__)

# 从环境变量中读取凭据
try:
    api_username = os.environ["API_USERNAME"]
    api_secret_key = os.environ["API_SECRET_KEY"]
    access_token = os.environ["ACCESS_TOKEN"]
    
    # DEVICE_ID 自动生成（如果未设置）
    device_id = os.environ.get("DEVICE_ID")
    if not device_id:
        random_num = str(random.randint(1000000000000000000, 9999999999999999999))
        timestamp = str(int(datetime.now().timestamp() * 1000))
        device_id = f"{random_num}_{timestamp}_{str(random.randint(100000, 999999))}"
        print(f"[INFO] 自动生成 DEVICE_ID: {device_id}")
except KeyError as e:
    raise ValueError(f"缺少必要的环境变量: {e.args[0]}")

# 会话存储配置
SESSION_DATA_DIR = os.environ.get("SESSION_DATA_DIR", "./sessions")
Path(SESSION_DATA_DIR).mkdir(parents=True, exist_ok=True)
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

# 创建 API 客户端实例
client = create_wenxiaobai_client(
    username=api_username,
    secret_key=api_secret_key,
    access_token=access_token,
    device_id=device_id
)

# 会话管理：加载已保存的会话数据
# 格式: {session_id: {"conversation_id": str, "turn_index": int}}
sessions = load_sessions()

# 默认会话ID：当客户端不传递session_id时使用
DEFAULT_SESSION_ID = "default-session"

# 当前默认会话ID（当达到对话上限时会自动更新）
current_default_session_id = DEFAULT_SESSION_ID

def update_session(session_id, conversation_id, turn_index):
    """更新会话数据并保存到文件"""
    sessions[session_id] = {
        "conversation_id": conversation_id,
        "turn_index": turn_index
    }
    save_sessions(sessions)
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

def format_openai_error_response(error_type, message, code=None):
    """格式化 OpenAI 兼容的错误响应"""
    error_response = {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": code
        }
    }
    return error_response

def extract_query_from_messages(messages):
    """从 OpenAI 格式的 messages 中提取查询内容"""
    if not messages or not isinstance(messages, list):
        return None
    
    # 获取最后一条消息
    last_message = messages[-1]
    
    # 处理不同的消息格式
    if isinstance(last_message, dict):
        content = last_message.get("content")
        
        # 如果 content 是字符串，直接返回
        if isinstance(content, str):
            return content
        
        # 如果 content 是列表（多模态消息），提取文本内容
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts) if text_parts else None
    
    return None

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions_endpoint():
    """
    兼容标准 OpenAI 的聊天 API 端点
    完全符合 OpenAI Chat Completions API 规范
    """
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
    
    # 决定是否需要新建会话
    is_new_conversation = conversation_id is None
    
    print(f"[REQUEST] 收到请求: session_id={session_id}, conversation_id={conversation_id}, turn_index={turn_index}, is_new={is_new_conversation}")

    # 验证模型
    if model not in MODEL_MAP:
        return jsonify(format_openai_error_response(
            "invalid_request_error",
            f"模型 '{model}' 不存在。可用模型: {', '.join(MODEL_MAP.keys())}"
        )), 400
    
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
        # 调用 API，传递 conversation_id 和 turn_index（会话复用逻辑在客户端处理）
        # is_new_conversation 决定是否新建对话
        print(f"[API] 调用文小白API: query='{query[:50]}...', model={model}, conversation_id={conversation_id}, turn_index={turn_index}, is_new_conversation={is_new_conversation}")
        response = client.chat(
            query,
            model=model,
            conversation_id=conversation_id,
            turn_index=turn_index,
            is_new_conversation=is_new_conversation
        )
        print(f"[API] API响应状态: {response.status_code if response else 'None'}")
        
        if response is None:
            return jsonify(format_openai_error_response(
                "api_error",
                "API 请求失败，无响应"
            )), 502
        
        # 检查响应状态
        if response.status_code != 200:
            error_details = response.text if response.text else "无错误详情"
            print(f"[ERROR] API返回错误: status={response.status_code}, details={error_details[:200]}")
            
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
                response = client.chat(
                    query,
                    model=model,
                    conversation_id=None,
                    turn_index=0,
                    is_new_conversation=True
                )
                print(f"[RETRY] 重试后状态: {response.status_code if response else 'None'}")
                
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
                current_turn_index = turn_index
                
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
        return jsonify(format_openai_error_response(
            "internal_server_error",
            f"内部服务器错误: {str(e)}"
        )), 500

@app.route('/v1/deployments/<deployment_name>/chat/completions', methods=['POST'])
def azure_chat_completions_endpoint(deployment_name):
    """
    兼容 Azure OpenAI 的聊天 API 端点
    完全符合 Azure OpenAI Chat Completions API 规范
    """
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
        # 使用部署名称作为模型
        model = deployment_name if deployment_name in MODEL_MAP else "wenxiaobai-deep-thought"
        
        # 调用 API，传递 conversation_id 和 turn_index（会话复用逻辑在客户端处理）
        response = client.chat(
            query,
            model=model,
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
                response = client.chat(
                    query,
                    model=model,
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
    """根路径，返回 API 信息"""
    return jsonify({
        "name": "WenXiaoBai OpenAI Compatible API",
        "version": "1.0.0",
        "description": "OpenAI 兼容的文小白 API 代理服务",
        "endpoints": {
            "chat_completions": "/v1/chat/completions",
            "models": "/v1/models",
            "health": "/health"
        },
        "available_models": list(MODEL_MAP.keys())
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
