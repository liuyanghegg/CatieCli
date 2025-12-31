#!/usr/bin/env python3
"""
数据库管理模块
"""
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os

class DatabaseManager:
    def __init__(self, db_path: str = "wenxiaobai_users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    is_admin BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # API Key表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    api_key VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Token表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    token TEXT NOT NULL,
                    device_id VARCHAR(255),
                    balance DECIMAL(10,6) DEFAULT 0,
                    last_balance_check TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    auto_task_enabled BOOLEAN DEFAULT 0,
                    api_calls_today INTEGER DEFAULT 0,
                    last_call_date DATE,
                    wenxiaobai_username VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wenxiaobai_username),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # 使用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    api_key_id INTEGER NOT NULL,
                    token_id INTEGER NOT NULL,
                    model VARCHAR(100),
                    tokens_used INTEGER DEFAULT 0,
                    cost DECIMAL(10,6) DEFAULT 0,
                    request_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (api_key_id) REFERENCES api_keys (id),
                    FOREIGN KEY (token_id) REFERENCES tokens (id)
                )
            ''')
            
            # 任务记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id INTEGER NOT NULL,
                    task_type VARCHAR(50) NOT NULL,
                    task_id VARCHAR(255) NOT NULL,
                    rewards_earned DECIMAL(10,6) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (token_id) REFERENCES tokens (id)
                )
            ''')
            
            # Token每日统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    initial_balance DECIMAL(10,6) DEFAULT 0,
                    api_calls_count INTEGER DEFAULT 0,
                    tasks_completed INTEGER DEFAULT 0,
                    rewards_earned DECIMAL(10,6) DEFAULT 0,
                    is_disabled_today BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(token_id, date),
                    FOREIGN KEY (token_id) REFERENCES tokens (id)
                )
            ''')
            
            conn.commit()
            
        # 创建默认管理员账户
        self.create_default_admin()
    
    def create_default_admin(self):
        """创建默认管理员账户"""
        try:
            admin_password = "admin123"  # 默认密码，建议首次登录后修改
            self.create_user("admin", admin_password, is_admin=True, email="admin@example.com")
            print(f"[INFO] 默认管理员账户已创建: username=admin, password={admin_password}")
        except Exception:
            pass  # 管理员已存在
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_api_key(self) -> str:
        """生成API Key"""
        return f"wxb-{secrets.token_urlsafe(32)}"
    
    # 用户管理
    def create_user(self, username: str, password: str, email: str = None, is_admin: bool = False) -> int:
        """创建用户"""
        password_hash = self.hash_password(password)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, is_admin)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, email, is_admin))
            return cursor.lastrowid
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """用户认证"""
        password_hash = self.hash_password(password)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active
                FROM users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            ''', (username, password_hash))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'is_admin': row[3],
                    'is_active': row[4]
                }
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active, created_at
                FROM users WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'is_admin': row[3],
                    'is_active': row[4],
                    'created_at': row[5]
                }
        return None
    
    def get_all_users(self) -> List[Dict]:
        """获取所有用户（管理员功能）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active, created_at
                FROM users ORDER BY created_at DESC
            ''')
            
            return [{
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'is_admin': row[3],
                'is_active': row[4],
                'created_at': row[5]
            } for row in cursor.fetchall()]
    
    # API Key管理
    def create_api_key(self, user_id: int, name: str) -> str:
        """创建API Key"""
        api_key = self.generate_api_key()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO api_keys (user_id, api_key, name)
                VALUES (?, ?, ?)
            ''', (user_id, api_key, name))
        
        return api_key
    
    def get_user_api_keys(self, user_id: int) -> List[Dict]:
        """获取用户的API Keys"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, api_key, name, is_active, created_at
                FROM api_keys WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,))
            
            return [{
                'id': row[0],
                'api_key': row[1],
                'name': row[2],
                'is_active': row[3],
                'created_at': row[4]
            } for row in cursor.fetchall()]
    
    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """根据API Key获取用户信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.username, u.is_admin, ak.id as api_key_id
                FROM users u
                JOIN api_keys ak ON u.id = ak.user_id
                WHERE ak.api_key = ? AND ak.is_active = 1 AND u.is_active = 1
            ''', (api_key,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1],
                    'is_admin': row[2],
                    'api_key_id': row[3]
                }
        return None
    
    def toggle_api_key(self, api_key_id: int, user_id: int) -> bool:
        """切换API Key状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE api_keys 
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (api_key_id, user_id))
            return cursor.rowcount > 0
    
    def delete_api_key(self, api_key_id: int, user_id: int) -> bool:
        """删除API Key"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM api_keys WHERE id = ? AND user_id = ?
            ''', (api_key_id, user_id))
            return cursor.rowcount > 0
    
    # Token管理
    def create_token(self, user_id: int, name: str, token: str, device_id: str = None, wenxiaobai_username: str = None) -> int:
        """创建Token"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tokens (user_id, name, token, device_id, auto_task_enabled, wenxiaobai_username)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (user_id, name, token, device_id, wenxiaobai_username))
            return cursor.lastrowid
    
    def get_user_tokens(self, user_id: int) -> List[Dict]:
        """获取用户的Tokens"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, token, device_id, balance, last_balance_check, is_active, 
                       auto_task_enabled, api_calls_today, last_call_date, wenxiaobai_username, created_at
                FROM tokens WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,))
            
            return [{
                'id': row[0],
                'name': row[1],
                'token': row[2][:20] + '...' if len(row[2]) > 20 else row[2],  # 隐藏部分token
                'full_token': row[2],  # 完整token用于API调用
                'device_id': row[3],
                'balance': float(row[4]) if row[4] else 0,
                'last_balance_check': row[5],
                'is_active': row[6],
                'auto_task_enabled': row[7],
                'api_calls_today': row[8] or 0,
                'last_call_date': row[9],
                'wenxiaobai_username': row[10],
                'created_at': row[11]
            } for row in cursor.fetchall()]
    
    def get_active_token_for_user(self, user_id: int) -> Optional[Dict]:
        """获取用户的活跃Token（用于API调用）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, token, device_id, balance
                FROM tokens 
                WHERE user_id = ? AND is_active = 1 
                ORDER BY balance DESC, created_at DESC
                LIMIT 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'token': row[1],
                    'device_id': row[2],
                    'balance': float(row[3]) if row[3] else 0
                }
        return None
    
    def update_token_balance(self, token_id: int, balance: float) -> bool:
        """更新Token余额"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tokens 
                SET balance = ?, last_balance_check = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (balance, token_id))
            return cursor.rowcount > 0
    
    def toggle_token(self, token_id: int, user_id: int) -> bool:
        """切换Token状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tokens 
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (token_id, user_id))
            return cursor.rowcount > 0
    
    def delete_token(self, token_id: int, user_id: int) -> bool:
        """删除Token"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM tokens WHERE id = ? AND user_id = ?
            ''', (token_id, user_id))
            return cursor.rowcount > 0
    
    def batch_toggle_tokens(self, token_ids: List[int], user_id: int) -> int:
        """批量切换Token状态"""
        if not token_ids:
            return 0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in token_ids])
            cursor.execute(f'''
                UPDATE tokens 
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders}) AND user_id = ?
            ''', token_ids + [user_id])
            return cursor.rowcount
    
    def batch_delete_tokens(self, token_ids: List[int], user_id: int) -> int:
        """批量删除Token"""
        if not token_ids:
            return 0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in token_ids])
            cursor.execute(f'''
                DELETE FROM tokens WHERE id IN ({placeholders}) AND user_id = ?
            ''', token_ids + [user_id])
            return cursor.rowcount
    
    # 使用记录
    def log_usage(self, user_id: int, api_key_id: int, token_id: int, 
                  model: str, tokens_used: int = 0, cost: float = 0, request_id: str = None):
        """记录使用情况"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usage_logs (user_id, api_key_id, token_id, model, tokens_used, cost, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, api_key_id, token_id, model, tokens_used, cost, request_id))
    
    def get_user_usage_stats(self, user_id: int, days: int = 30) -> Dict:
        """获取用户使用统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(DISTINCT DATE(created_at)) as active_days
                FROM usage_logs 
                WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
            '''.format(days), (user_id,))
            
            row = cursor.fetchone()
            return {
                'total_requests': row[0] or 0,
                'total_tokens': row[1] or 0,
                'total_cost': float(row[2]) if row[2] else 0,
                'active_days': row[3] or 0
            }
    
    def toggle_auto_task(self, token_id: int, user_id: int) -> bool:
        """切换Token自动任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tokens 
                SET auto_task_enabled = NOT auto_task_enabled, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (token_id, user_id))
            return cursor.rowcount > 0
    
    def increment_api_calls(self, token_id: int) -> int:
        """增加Token的API调用次数"""
        today = datetime.now().date().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查是否是新的一天
            cursor.execute('''
                SELECT api_calls_today, last_call_date FROM tokens WHERE id = ?
            ''', (token_id,))
            
            row = cursor.fetchone()
            if row:
                current_calls, last_date = row
                
                # 如果是新的一天，重置计数
                if last_date != today:
                    current_calls = 0
                
                new_calls = current_calls + 1
                
                cursor.execute('''
                    UPDATE tokens 
                    SET api_calls_today = ?, last_call_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_calls, today, token_id))
                
                conn.commit()
                return new_calls
            
            return 0
    
    def get_tokens_for_auto_tasks(self) -> List[Dict]:
        """获取启用了自动任务的Token"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, name, token, device_id, balance, auto_task_enabled, 
                       api_calls_today, last_call_date
                FROM tokens 
                WHERE auto_task_enabled = 1 AND is_active = 1
            ''', ())
            
            return [{
                'id': row[0],
                'user_id': row[1],
                'name': row[2],
                'full_token': row[3],
                'device_id': row[4],
                'balance': float(row[5]) if row[5] else 0,
                'auto_task_enabled': row[6],
                'api_calls_today': row[7] or 0,
                'last_call_date': row[8]
            } for row in cursor.fetchall()]
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def check_wenxiaobai_username_exists(self, wenxiaobai_username: str) -> bool:
        """检查文小白用户名是否已存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM tokens WHERE wenxiaobai_username = ?
            ''', (wenxiaobai_username,))
            return cursor.fetchone()[0] > 0
    
    def get_all_tokens(self) -> List[Dict]:
        """获取所有Token（管理员功能）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.user_id, u.username, t.name, t.token, t.device_id, 
                       t.balance, t.last_balance_check, t.is_active, t.auto_task_enabled, 
                       t.api_calls_today, t.last_call_date, t.wenxiaobai_username, t.created_at
                FROM tokens t
                JOIN users u ON t.user_id = u.id
                ORDER BY t.created_at DESC
            ''', ())
            
            return [{
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'name': row[3],
                'token': row[4][:20] + '...' if len(row[4]) > 20 else row[4],
                'full_token': row[4],
                'device_id': row[5],
                'balance': float(row[6]) if row[6] else 0,
                'last_balance_check': row[7],
                'is_active': row[8],
                'auto_task_enabled': row[9],
                'api_calls_today': row[10] or 0,
                'last_call_date': row[11],
                'wenxiaobai_username': row[12],
                'created_at': row[13]
            } for row in cursor.fetchall()]
    
    def admin_toggle_token(self, token_id: int) -> bool:
        """管理员切换Token状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tokens 
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (token_id,))
            return cursor.rowcount > 0
    
    def admin_toggle_auto_task(self, token_id: int) -> bool:
        """管理员切换Token自动任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tokens 
                SET auto_task_enabled = NOT auto_task_enabled, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (token_id,))
            return cursor.rowcount > 0
    
    def admin_delete_token(self, token_id: int) -> bool:
        """管理员删除Token"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM tokens WHERE id = ?
            ''', (token_id,))
            return cursor.rowcount > 0
    
    def admin_batch_toggle_tokens(self, token_ids: List[int]) -> int:
        """管理员批量切换Token状态"""
        if not token_ids:
            return 0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in token_ids])
            cursor.execute(f'''
                UPDATE tokens 
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            ''', token_ids)
            return cursor.rowcount
    
    def admin_batch_toggle_auto_task(self, token_ids: List[int]) -> int:
        """管理员批量切换自动任务状态"""
        if not token_ids:
            return 0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in token_ids])
            cursor.execute(f'''
                UPDATE tokens 
                SET auto_task_enabled = NOT auto_task_enabled, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            ''', token_ids)
            return cursor.rowcount
    
    def admin_batch_delete_tokens(self, token_ids: List[int]) -> int:
        """管理员批量删除Token"""
        if not token_ids:
            return 0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in token_ids])
            cursor.execute(f'''
                DELETE FROM tokens WHERE id IN ({placeholders})
            ''', token_ids)
            return cursor.rowcount
    
    def admin_delete_user(self, user_id: int) -> bool:
        """管理员删除用户（级联删除相关数据）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM users WHERE id = ? AND is_admin = 0
            ''', (user_id,))
            return cursor.rowcount > 0
    
    def admin_toggle_user_status(self, user_id: int) -> bool:
        """管理员切换用户状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_admin = 0
            ''', (user_id,))
            return cursor.rowcount > 0

# 全局数据库实例
db = DatabaseManager()