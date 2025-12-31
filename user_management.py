#!/usr/bin/env python3
"""
用户管理API端点
"""
from flask import Blueprint, request, jsonify, session, render_template_string
from functools import wraps
import logging
from database import db
from balance_checker import balance_checker
from task_system import task_system
from wenxiaobai_client import MODEL_ABILITIES

logger = logging.getLogger(__name__)

# 创建蓝图
user_bp = Blueprint('user_management', __name__)

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登录'}), 401
        
        user = db.get_user_by_id(session['user_id'])
        if not user or not user['is_admin']:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 认证相关端点
@user_bp.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    user = db.authenticate_user(username, password)
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        
        logger.info(f"User {username} logged in successfully")
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'is_admin': user['is_admin']
            }
        })
    else:
        logger.warning(f"Failed login attempt for username: {username}")
        return jsonify({'error': '用户名或密码错误'}), 401

@user_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    username = session.get('username', 'Unknown')
    session.clear()
    logger.info(f"User {username} logged out")
    return jsonify({'success': True})

@user_bp.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    try:
        user_id = db.create_user(username, password, email)
        logger.info(f"New user registered: {username} (ID: {user_id})")
        return jsonify({'success': True, 'user_id': user_id})
    except Exception as e:
        logger.error(f"Registration failed for {username}: {e}")
        return jsonify({'error': '注册失败，用户名可能已存在'}), 400

@user_bp.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前用户信息"""
    user = db.get_user_by_id(session['user_id'])
    if user:
        return jsonify({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'is_admin': user['is_admin'],
                'created_at': user['created_at']
            }
        })
    return jsonify({'error': '用户不存在'}), 404

# API Key管理
@user_bp.route('/api/keys', methods=['GET'])
@login_required
def get_api_keys():
    """获取用户的API Keys"""
    keys = db.get_user_api_keys(session['user_id'])
    return jsonify({'api_keys': keys})

@user_bp.route('/api/keys', methods=['POST'])
@login_required
def create_api_key():
    """创建新的API Key"""
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'API Key名称不能为空'}), 400
    
    try:
        api_key = db.create_api_key(session['user_id'], name)
        logger.info(f"User {session['username']} created API key: {name}")
        return jsonify({'success': True, 'api_key': api_key})
    except Exception as e:
        logger.error(f"Failed to create API key for user {session['username']}: {e}")
        return jsonify({'error': '创建API Key失败'}), 500

@user_bp.route('/api/keys/<int:key_id>/toggle', methods=['POST'])
@login_required
def toggle_api_key(key_id):
    """切换API Key状态"""
    success = db.toggle_api_key(key_id, session['user_id'])
    if success:
        logger.info(f"User {session['username']} toggled API key {key_id}")
        return jsonify({'success': True})
    return jsonify({'error': '操作失败'}), 400

@user_bp.route('/api/keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    """删除API Key"""
    success = db.delete_api_key(key_id, session['user_id'])
    if success:
        logger.info(f"User {session['username']} deleted API key {key_id}")
        return jsonify({'success': True})
    return jsonify({'error': '删除失败'}), 400

# Token管理
@user_bp.route('/api/tokens', methods=['GET'])
@login_required
def get_tokens():
    """获取用户的Tokens"""
    tokens = db.get_user_tokens(session['user_id'])
    return jsonify({'tokens': tokens})

@user_bp.route('/api/tokens', methods=['POST'])
@login_required
def create_token():
    """创建新的Token"""
    data = request.get_json()
    name = data.get('name')
    token = data.get('token')
    device_id = data.get('device_id')
    
    if not name or not token:
        return jsonify({'error': 'Token名称和内容不能为空'}), 400
    
    try:
        # 验证Token并获取用户信息
        balance_result = balance_checker.check_balance(token, device_id)
        
        if not balance_result or not balance_result.get('success'):
            return jsonify({'error': 'Token验证失败，请检查Token是否有效'}), 400
        
        # 提取文小白用户名
        user_info = balance_result.get('user_info', {})
        wenxiaobai_username = user_info.get('nickname')
        
        if not wenxiaobai_username:
            return jsonify({'error': '无法获取文小白用户名'}), 400
        
        # 检查用户名是否已存在
        if db.check_wenxiaobai_username_exists(wenxiaobai_username):
            return jsonify({'error': f'文小白用户 {wenxiaobai_username} 的Token已存在'}), 400
        
        # 创建Token
        token_id = db.create_token(session['user_id'], name, token, device_id, wenxiaobai_username)
        
        # 更新余额信息
        suanli_balance = balance_result.get('suanli_balance', 0)
        db.update_token_balance(token_id, suanli_balance)
        
        logger.info(f"User {session['username']} created token: {name} for {wenxiaobai_username}")
        return jsonify({
            'success': True, 
            'token_id': token_id,
            'wenxiaobai_username': wenxiaobai_username,
            'balance': suanli_balance
        })
    except Exception as e:
        logger.error(f"Failed to create token for user {session['username']}: {e}")
        return jsonify({'error': '创建Token失败'}), 500

@user_bp.route('/api/tokens/<int:token_id>/toggle', methods=['POST'])
@login_required
def toggle_token(token_id):
    """切换Token状态"""
    success = db.toggle_token(token_id, session['user_id'])
    if success:
        logger.info(f"User {session['username']} toggled token {token_id}")
        return jsonify({'success': True})
    return jsonify({'error': '操作失败'}), 400

@user_bp.route('/api/tokens/<int:token_id>', methods=['DELETE'])
@login_required
def delete_token(token_id):
    """删除Token"""
    success = db.delete_token(token_id, session['user_id'])
    if success:
        logger.info(f"User {session['username']} deleted token {token_id}")
        return jsonify({'success': True})
    return jsonify({'error': '删除失败'}), 400

@user_bp.route('/api/tokens/batch', methods=['POST'])
@login_required
def batch_manage_tokens():
    """批量管理Tokens"""
    data = request.get_json()
    action = data.get('action')  # 'toggle' 或 'delete'
    token_ids = data.get('token_ids', [])
    
    if not action or not token_ids:
        return jsonify({'error': '参数不完整'}), 400
    
    try:
        if action == 'toggle':
            affected = db.batch_toggle_tokens(token_ids, session['user_id'])
            logger.info(f"User {session['username']} batch toggled {affected} tokens")
        elif action == 'delete':
            affected = db.batch_delete_tokens(token_ids, session['user_id'])
            logger.info(f"User {session['username']} batch deleted {affected} tokens")
        else:
            return jsonify({'error': '无效的操作'}), 400
        
        return jsonify({'success': True, 'affected': affected})
    except Exception as e:
        logger.error(f"Batch token operation failed for user {session['username']}: {e}")
        return jsonify({'error': '批量操作失败'}), 500

# 余额查询
@user_bp.route('/api/tokens/balance/batch', methods=['POST'])
@login_required
def batch_check_balances():
    """查询单个Token余额"""
    # 获取token信息
    tokens = db.get_user_tokens(session['user_id'])
    token_info = next((t for t in tokens if t['id'] == token_id), None)
    
    if not token_info:
        return jsonify({'error': 'Token不存在'}), 404
    
    # 查询余额
    balance_result = balance_checker.check_balance(
        token_info['full_token'], 
        token_info['device_id']
    )
    
    if balance_result and balance_result.get('success'):
        # 更新数据库中的余额
        suanli_balance = balance_result.get('suanli_balance', 0)
        db.update_token_balance(token_id, suanli_balance)
        
        logger.info(f"Balance checked for token {token_id}: {suanli_balance}")
        return jsonify({
            'success': True,
            'balance': suanli_balance,
            'balance_info': balance_result
        })
    else:
        error_msg = balance_result.get('error', '查询失败') if balance_result else '查询失败'
        logger.error(f"Balance check failed for token {token_id}: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 400

@user_bp.route('/api/tokens/<int:token_id>/toggle-auto-task', methods=['POST'])
@login_required
def toggle_auto_task(token_id):
    """切换Token自动任务状态"""
    success = db.toggle_auto_task(token_id, session['user_id'])
    if success:
        logger.info(f"User {session['username']} toggled auto task for token {token_id}")
        return jsonify({'success': True})
    return jsonify({'error': '操作失败'}), 400

@user_bp.route('/api/tokens/<int:token_id>/test-api', methods=['POST'])
@login_required
def test_token_api(token_id):
    """测试Token的API调用"""
    # 获取token信息
    tokens = db.get_user_tokens(session['user_id'])
    token_info = next((t for t in tokens if t['id'] == token_id), None)
    
    if not token_info:
        return jsonify({'error': 'Token不存在'}), 404
    
    try:
        # 导入wenxiaobai_client来测试API调用
        from wenxiaobai_client import create_wenxiaobai_client
        import os
        
        # 创建测试客户端
        test_client = create_wenxiaobai_client(
            username=os.environ.get("API_USERNAME"),
            secret_key=os.environ.get("API_SECRET_KEY"),
            access_token=token_info['full_token'],
            device_id=token_info['device_id'] or "test-device"
        )
        
        # 发送测试请求
        response = test_client.chat(
            "你好，这是一个API测试",
            model="wenxiaobai-base",
            conversation_id=None,
            turn_index=0,
            is_new_conversation=True
        )
        
        if response and response.status_code == 200:
            logger.info(f"API test successful for token {token_id}")
            return jsonify({
                'success': True,
                'message': 'API测试成功，Token可正常使用'
            })
        else:
            error_msg = f'API测试失败: HTTP {response.status_code}' if response else 'API测试失败: 无响应'
            logger.error(f"API test failed for token {token_id}: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
    except Exception as e:
        logger.error(f"API test error for token {token_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'API测试异常: {str(e)}'
        }), 500

@user_bp.route('/api/models', methods=['GET'])
@login_required
def get_available_models():
    """获取所有可用模型"""
    models = []
    for model_name, model_config in MODEL_ABILITIES.items():
        models.append({
            'id': model_name,
            'name': model_name,
            'description': model_config.get('description', ''),
            'abilities': model_config.get('abilities', [])
        })
    
    return jsonify({'models': models})
    """批量查询Token余额"""
    data = request.get_json()
    token_ids = data.get('token_ids', [])
    
    if not token_ids:
        return jsonify({'error': 'Token ID列表不能为空'}), 400
    
    # 获取用户的tokens
    user_tokens = db.get_user_tokens(session['user_id'])
    
    # 筛选出要查询的tokens
    tokens_to_check = []
    for token in user_tokens:
        if token['id'] in token_ids:
            tokens_to_check.append({
                'id': token['id'],
                'token': token['full_token'],
                'device_id': token['device_id']
            })
    
    if not tokens_to_check:
        return jsonify({'error': '没有找到有效的Token'}), 400
    
    # 批量查询余额
    batch_result = balance_checker.batch_check_balances(tokens_to_check)
    
    # 更新数据库中的余额
    for result in batch_result['results']:
        if result['balance_result'].get('success'):
            balance = result['balance_result'].get('suanli_balance', 0)
            db.update_token_balance(result['token_id'], balance)
    
    logger.info(f"Batch balance check for user {session['username']}: {batch_result['success_count']} success, {batch_result['failed_count']} failed")
    
    return jsonify({
        'success': True,
        'results': batch_result
    })

# 管理员功能
@user_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """获取所有用户（管理员功能）"""
    users = db.get_all_users()
    return jsonify({'users': users})

@user_bp.route('/api/admin/users/<int:user_id>/tokens', methods=['GET'])
@admin_required
def get_user_tokens_admin(user_id):
    """获取指定用户的Tokens（管理员功能）"""
    tokens = db.get_user_tokens(user_id)
    user = db.get_user_by_id(user_id)
    return jsonify({
        'user': user,
        'tokens': tokens
    })

@user_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """获取系统统计信息（管理员功能）"""
    users = db.get_all_users()
    total_users = len(users)
    active_users = len([u for u in users if u['is_active']])
    admin_users = len([u for u in users if u['is_admin']])
    
    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'recent_users': users[:10]  # 最近10个用户
    })

# 使用统计
@user_bp.route('/api/stats/usage', methods=['GET'])
@login_required
def get_usage_stats():
    """获取用户使用统计"""
    days = request.args.get('days', 30, type=int)
    stats = db.get_user_usage_stats(session['user_id'], days)
    return jsonify({'stats': stats})

# 管理员Token管理
@user_bp.route('/api/admin/tokens', methods=['GET'])
@admin_required
def get_all_tokens():
    """获取所有Token（管理员功能）"""
    tokens = db.get_all_tokens()
    return jsonify({'tokens': tokens})

@user_bp.route('/api/admin/tokens', methods=['POST'])
@admin_required
def admin_create_token():
    """管理员创建Token"""
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    token = data.get('token')
    device_id = data.get('device_id')
    
    if not user_id or not name or not token:
        return jsonify({'error': '用户ID、Token名称和内容不能为空'}), 400
    
    try:
        # 验证Token并获取用户信息
        balance_result = balance_checker.check_balance(token, device_id)
        
        if not balance_result or not balance_result.get('success'):
            return jsonify({'error': 'Token验证失败，请检查Token是否有效'}), 400
        
        # 提取文小白用户名
        user_info = balance_result.get('user_info', {})
        wenxiaobai_username = user_info.get('nickname')
        
        if not wenxiaobai_username:
            return jsonify({'error': '无法获取文小白用户名'}), 400
        
        # 检查用户名是否已存在
        if db.check_wenxiaobai_username_exists(wenxiaobai_username):
            return jsonify({'error': f'文小白用户 {wenxiaobai_username} 的Token已存在'}), 400
        
        # 创建Token
        token_id = db.create_token(user_id, name, token, device_id, wenxiaobai_username)
        
        # 更新余额信息
        suanli_balance = balance_result.get('suanli_balance', 0)
        db.update_token_balance(token_id, suanli_balance)
        
        logger.info(f"Admin {session['username']} created token: {name} for user {user_id}")
        return jsonify({
            'success': True, 
            'token_id': token_id,
            'wenxiaobai_username': wenxiaobai_username,
            'balance': suanli_balance
        })
    except Exception as e:
        logger.error(f"Admin failed to create token: {e}")
        return jsonify({'error': '创建Token失败'}), 500

@user_bp.route('/api/admin/tokens/<int:token_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_token(token_id):
    """管理员切换Token状态"""
    success = db.admin_toggle_token(token_id)
    if success:
        logger.info(f"Admin {session['username']} toggled token {token_id}")
        return jsonify({'success': True})
    return jsonify({'error': '操作失败'}), 400

@user_bp.route('/api/admin/tokens/<int:token_id>/toggle-auto-task', methods=['POST'])
@admin_required
def admin_toggle_token_auto_task(token_id):
    """管理员切换Token自动任务状态"""
    success = db.admin_toggle_auto_task(token_id)
    if success:
        logger.info(f"Admin {session['username']} toggled auto task for token {token_id}")
        return jsonify({'success': True})
    return jsonify({'error': '操作失败'}), 400

@user_bp.route('/api/admin/tokens/<int:token_id>', methods=['DELETE'])
@admin_required
def admin_delete_token(token_id):
    """管理员删除Token"""
    success = db.admin_delete_token(token_id)
    if success:
        logger.info(f"Admin {session['username']} deleted token {token_id}")
        return jsonify({'success': True})
    return jsonify({'error': '删除失败'}), 400

@user_bp.route('/api/admin/tokens/batch', methods=['POST'])
@admin_required
def admin_batch_manage_tokens():
    """管理员批量管理Token"""
    data = request.get_json()
    action = data.get('action')  # 'toggle', 'toggle-auto-task', 'delete'
    token_ids = data.get('token_ids', [])
    
    if not action or not token_ids:
        return jsonify({'error': '参数不完整'}), 400
    
    try:
        if action == 'toggle':
            affected = db.admin_batch_toggle_tokens(token_ids)
            logger.info(f"Admin {session['username']} batch toggled {affected} tokens")
        elif action == 'toggle-auto-task':
            affected = db.admin_batch_toggle_auto_task(token_ids)
            logger.info(f"Admin {session['username']} batch toggled auto task for {affected} tokens")
        elif action == 'delete':
            affected = db.admin_batch_delete_tokens(token_ids)
            logger.info(f"Admin {session['username']} batch deleted {affected} tokens")
        else:
            return jsonify({'error': '无效的操作'}), 400
        
        return jsonify({'success': True, 'affected': affected})
    except Exception as e:
        logger.error(f"Admin batch token operation failed: {e}")
        return jsonify({'error': '批量操作失败'}), 500

# 管理员用户管理
@user_bp.route('/api/admin/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(user_id):
    """管理员切换用户状态"""
    success = db.admin_toggle_user_status(user_id)
    if success:
        logger.info(f"Admin {session['username']} toggled user {user_id}")
        return jsonify({'success': True})
    return jsonify({'error': '操作失败'}), 400

@user_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """管理员删除用户"""
    success = db.admin_delete_user(user_id)
    if success:
        logger.info(f"Admin {session['username']} deleted user {user_id}")
        return jsonify({'success': True})
    return jsonify({'error': '删除失败'}), 400