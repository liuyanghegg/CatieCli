import hashlib
import base64
import json
import requests
from datetime import datetime
import pytz

# 模型名称到模型ID的映射 - 完整的模型组合
MODEL_MAP = {
    # ===== deepseekV3_2 系列 =====
    "wenxiaobai-base": "deepseekV3_2",
    "wenxiaobai-v3_2-base": "deepseekV3_2",
    "wenxiaobai-search": "deepseekV3_2",
    "wenxiaobai-v3_2-search": "deepseekV3_2",
    "wenxiaobai-deep-thought": "deepseekV3_2",
    "wenxiaobai-v3_2-deep-thought": "deepseekV3_2",
    "wenxiaobai-search-deep-thought": "deepseekV3_2",
    "wenxiaobai-v3_2-search-deep-thought": "deepseekV3_2",
    
    # ===== deepseekV3 系列 =====
    "deepseek-v3": "deepseekV3",
    "deepseek-v3-base": "deepseekV3",
    "deepseek-v3-search": "deepseekV3",
    "deepseek-v3-deep-thought": "deepseekV3",
    "deepseek-v3-search-deep-thought": "deepseekV3",
    
    # ===== xiaobai5 系列 =====
    "xiaobai-5": "xiaobai5",
    "xiaobai-5-base": "xiaobai5",
    "xiaobai-5-search": "xiaobai5",
    "xiaobai-5-deep-thought": "xiaobai5",
    "xiaobai-5-search-deep-thought": "xiaobai5",
    
    # ===== 直接使用模型ID的选项 =====
    "deepseekV3": "deepseekV3",
    "xiaobai5": "xiaobai5",
    "deepseekV3_2": "deepseekV3_2",
}

# 模型能力配置
MODEL_ABILITIES = {
    # ===== deepseekV3_2 系列 =====
    "wenxiaobai-base": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "基础模型（deepseekV3_2），无搜索和深度思考功能"
    },
    "wenxiaobai-v3_2-base": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "DeepSeek V3_2 基础模型，无搜索和深度思考功能"
    },
    "wenxiaobai-search": {
        "enable_search": True,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "搜索模型（deepseekV3_2），具备联网搜索能力"
    },
    "wenxiaobai-v3_2-search": {
        "enable_search": True,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "DeepSeek V3_2 搜索模型，具备联网搜索能力"
    },
    "wenxiaobai-deep-thought": {
        "enable_search": False,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "深度思考模型（deepseekV3_2），具备深度推理能力"
    },
    "wenxiaobai-v3_2-deep-thought": {
        "enable_search": False,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "DeepSeek V3_2 深度思考模型，具备深度推理能力"
    },
    "wenxiaobai-search-deep-thought": {
        "enable_search": True,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "搜索+深度思考模型（deepseekV3_2），同时具备联网搜索和深度推理能力"
    },
    "wenxiaobai-v3_2-search-deep-thought": {
        "enable_search": True,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "DeepSeek V3_2 搜索+深度思考模型，同时具备联网搜索和深度推理能力"
    },
    
    # ===== deepseekV3 系列 =====
    "deepseek-v3": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": True,
        "description": "DeepSeek V3 模型，具备深度搜索能力"
    },
    "deepseek-v3-base": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "DeepSeek V3 基础模型，无额外功能"
    },
    "deepseek-v3-search": {
        "enable_search": True,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "DeepSeek V3 搜索模型，具备联网搜索能力"
    },
    "deepseek-v3-deep-thought": {
        "enable_search": False,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "DeepSeek V3 深度思考模型，具备深度推理能力"
    },
    "deepseek-v3-search-deep-thought": {
        "enable_search": True,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "DeepSeek V3 搜索+深度思考模型，同时具备联网搜索和深度推理能力"
    },
    
    # ===== xiaobai5 系列 =====
    "xiaobai-5": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "小白5模型，基础对话模型"
    },
    "xiaobai-5-base": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "小白5基础模型，无额外功能"
    },
    "xiaobai-5-search": {
        "enable_search": True,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "小白5搜索模型，具备联网搜索能力"
    },
    "xiaobai-5-deep-thought": {
        "enable_search": False,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "小白5深度思考模型，具备深度推理能力"
    },
    "xiaobai-5-search-deep-thought": {
        "enable_search": True,
        "enable_deep_thought": True,
        "enable_deep_search": False,
        "description": "小白5搜索+深度思考模型，同时具备联网搜索和深度推理能力"
    },
    
    # ===== 直接使用模型ID的选项 =====
    "deepseekV3": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": True,
        "description": "DeepSeek V3 原始模型"
    },
    "xiaobai5": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "小白5 原始模型"
    },
    "deepseekV3_2": {
        "enable_search": False,
        "enable_deep_thought": False,
        "enable_deep_search": False,
        "description": "DeepSeek V3_2 原始模型"
    },
}

class CryptoJS_HMAC:
    """
    模拟 CryptoJS 的 HMAC 算法实现
    """
    def __init__(self, hash_algorithm, key):
        self.hash_name = hash_algorithm.__name__.split('_')[-1].lower()
        self.block_size = 64
        
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        if len(key) > self.block_size:
            key = hashlib.new(self.hash_name, key).digest()
        
        if len(key) < self.block_size:
            key = key.ljust(self.block_size, b'\x00')
        
        self.i_key = bytes(x ^ y for x, y in zip(key, b'\x36' * self.block_size))
        self.o_key = bytes(x ^ y for x, y in zip(key, b'\x5c' * self.block_size))
        
        self.reset()
    
    def reset(self):
        self.inner_hash = hashlib.new(self.hash_name)
        self.inner_hash.update(self.i_key)
    
    def update(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.inner_hash.update(data)
        return self
    
    def finalize(self, data=None):
        if data:
            self.update(data)
        
        inner_result = self.inner_hash.digest()
        
        outer_hash = hashlib.new(self.hash_name)
        outer_hash.update(self.o_key)
        outer_hash.update(inner_result)
        
        return outer_hash.digest()

    def finalize_base64(self, data=None):
        return base64.b64encode(self.finalize(data)).decode('utf-8')

def hmac_sha1(key, message):
    hmac = CryptoJS_HMAC(hashlib.sha1, key)
    return hmac.update(message).finalize_base64()

class WenXiaoBaiAPI:
    def __init__(self, username, secret_key, access_token, device_id):
        self.username = username
        self.secret_key = secret_key
        self.access_token = access_token
        self.device_id = device_id
        self.base_url = "https://api-bj.wenxiaobai.com/api/v1.0/core/conversation/chat/v3"

    def _get_rfc1123_date(self):
        return datetime.now(pytz.timezone('GMT')).strftime('%a, %d %b %Y %H:%M:%S GMT')

    def _calculate_digest(self, body):
        body_str = json.dumps(body, separators=(',', ':'))
        sha256_hash = hashlib.sha256(body_str.encode('utf-8')).digest()
        digest_base64 = base64.b64encode(sha256_hash).decode('utf-8')
        return f"SHA-256={digest_base64}"

    def _calculate_hmac_sha1_signature(self, date_str, digest):
        signing_string = f"x-date: {date_str}\ndigest: {digest}"
        signature = hmac_sha1(self.secret_key, signing_string)
        return signature

    def chat(self, query, model="wenxiaobai-deep-thought", conversation_id=None, user_id=128122134, turn_index=0, is_new_conversation=None, **kwargs):
        # 使用 MODEL_MAP 将模型名称转换为模型 ID
        model_id = MODEL_MAP.get(model, MODEL_MAP["wenxiaobai-deep-thought"])
        
        # 获取模型能力配置
        model_config = MODEL_ABILITIES.get(model, MODEL_ABILITIES["wenxiaobai-deep-thought"])
        
        # 根据模型配置设置 abilities
        abilities = []
        if model_config.get("enable_search", False):
            abilities.append({"id": "web_search"})
        if model_config.get("enable_deep_thought", False):
            abilities.append({"id": "deep_thought"})
        if model_config.get("enable_deep_search", False):
            abilities.append({"id": "deep_search"})

        request_body = {
            "userId": user_id,
            "botAlias": "custom",
            "query": query,
            "isRetry": False,
            "breakingStrategy": 0,
            "isNewConversation": is_new_conversation if is_new_conversation is not None else (conversation_id is None),
            "isAnonymousChat": False,
            "mediaInfos": [],
            "turnIndex": turn_index,  # 使用传入的 turn_index 参数
            "rewriteQuery": "",
            "conversationId": conversation_id or "",
            "attachmentInfo": {"url": {"infoList": []}},
            "inputWay": "proactive",
            "agentId": "200006",
            "modelId": model_id,
            "aiAbility": {"id": ""},
            "abilities": abilities,  # 使用配置的 abilities
            "pureQuery": "",
            "isPublic": 0,
            **kwargs
        }
        
        date_str = self._get_rfc1123_date()
        digest = self._calculate_digest(request_body)
        signature = self._calculate_hmac_sha1_signature(date_str, digest)
        
        authorization_header = (
            f'hmac username="{self.username}", '
            f'algorithm="hmac-sha1", '
            f'headers="x-date digest", '
            f'signature="{signature}"'
        )
        
        headers = {
            'Accept': 'text/event-stream, application/json, text/event-stream',
            'Authorization': authorization_header,
            'Content-Type': 'application/json',
            'Digest': digest,
            'Host': 'api-bj.wenxiaobai.com',
            'Origin': 'https://www.wenxiaobai.com',
            'Referer': 'https://www.wenxiaobai.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Core/1.116.597.400 QQBrowser/19.9.7033.400',
            'X-Yuanshi-Authorization': f'Bearer {self.access_token}',
            'X-Yuanshi-Channel': 'browser',
            'X-Yuanshi-DeviceId': self.device_id,
            'X-Yuanshi-Platform': 'web',
            'x-date': date_str,
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=request_body,
                stream=True,
                timeout=30,
                verify=False  # 禁用 SSL 证书验证
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request to WenXiaoBai API failed: {e}")
            return None

def create_wenxiaobai_client(username, secret_key, access_token, device_id):
    return WenXiaoBaiAPI(username, secret_key, access_token, device_id)
