#!/usr/bin/env python3
"""
文小白任务系统模块
"""
import requests
import json
import hashlib
import base64
from datetime import datetime, date
import pytz
from typing import Optional, Dict, List
import logging
from database import db

logger = logging.getLogger(__name__)

class TaskSystem:
    def __init__(self):
        self.base_url = "https://api-bj.wenxiaobai.com"
        self.task_list_endpoint = "/rest/api/task/list2"
        self.task_execute_endpoint = "/rest/api/task/execute"
        
        # 任务限制
        self.daily_browse_limit = 200  # 每日浏览任务上限
        self.daily_checkin_limit = 1   # 每日签到任务上限
        self.balance_check_threshold = 50  # 调用50次后检查余额
        self.low_balance_threshold = 10   # 低余额阈值
        self.task_trigger_threshold = 50  # 执行任务的触发阈值
    
    def _get_rfc1123_date(self):
        """获取RFC1123格式的日期"""
        return datetime.now(pytz.timezone('GMT')).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    def _get_base_headers(self, token: str, device_id: str = None):
        """获取基础请求头"""
        headers = {
            'Connection': 'Keep-Alive',
            'accept': 'application/json',
            'accept-language': 'zh',
            'host': 'api-bj.wenxiaobai.com',
            'user-agent': 'wanyu/4.6.0/7040600 (Android 28)',
            'x-date': self._get_rfc1123_date(),
            'x-yuanshi-appname': 'wanyu',
            'x-yuanshi-appversionname': '4.6.0',
            'x-yuanshi-platform': 'android',
            'x-yuanshi-authorization': f'Bearer {token}'
        }
        
        if device_id:
            headers['x-yuanshi-deviceid'] = device_id
            
        return headers
    
    def get_task_list(self, token: str, device_id: str = None) -> Optional[Dict]:
        """获取任务列表"""
        try:
            headers = self._get_base_headers(token, device_id)
            
            response = requests.get(
                f"{self.base_url}{self.task_list_endpoint}?isOldVersion=false",
                headers=headers,
                timeout=10,
                verify=False
            )
            
            logger.info(f"Task list response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    tasks = data.get('data', [])
                    logger.info(f"Retrieved {len(tasks)} tasks")
                    return {
                        'success': True,
                        'tasks': tasks,
                        'count': len(tasks)
                    }
                else:
                    logger.error(f"Task list API error: {data.get('msg', 'Unknown error')}")
                    return {
                        'success': False,
                        'error': data.get('msg', 'API返回错误'),
                        'code': data.get('code')
                    }
            else:
                logger.error(f"Task list HTTP error: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP错误: {response.status_code}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("Task list request timeout")
            return {
                'success': False,
                'error': '请求超时'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Task list request error: {e}")
            return {
                'success': False,
                'error': f'网络请求错误: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Task list unexpected error: {e}")
            return {
                'success': False,
                'error': f'未知错误: {str(e)}'
            }
    
    def complete_task(self, token: str, task_id: str, device_id: str = None) -> Optional[Dict]:
        """完成任务"""
        try:
            headers = self._get_base_headers(token, device_id)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            
            data = f"taskId={task_id}"
            
            response = requests.post(
                f"{self.base_url}{self.task_execute_endpoint}",
                headers=headers,
                data=data,
                timeout=10,
                verify=False
            )
            
            logger.info(f"Task execute response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0 and result.get('data', {}).get('success'):
                    # 解析奖励
                    rewards_earned = 0
                    rewards = result.get('data', {}).get('rewards', [])
                    if rewards and len(rewards) > 0:
                        rewards_earned = float(rewards[0].get('rewardCount', 0))
                    
                    logger.info(f"Task completed successfully, earned: {rewards_earned}")
                    return {
                        'success': True,
                        'rewards_earned': rewards_earned,
                        'task_id': task_id
                    }
                else:
                    logger.error(f"Task execution failed: {result.get('msg', 'Unknown error')}")
                    return {
                        'success': False,
                        'error': result.get('msg', '任务执行失败'),
                        'code': result.get('code')
                    }
            else:
                logger.error(f"Task execute HTTP error: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP错误: {response.status_code}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("Task execute request timeout")
            return {
                'success': False,
                'error': '请求超时'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Task execute request error: {e}")
            return {
                'success': False,
                'error': f'网络请求错误: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Task execute unexpected error: {e}")
            return {
                'success': False,
                'error': f'未知错误: {str(e)}'
            }
    
    def get_daily_task_stats(self, token_id: int) -> Dict:
        """获取Token的每日任务统计"""
        today = date.today().isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    task_type,
                    COUNT(*) as count,
                    SUM(rewards_earned) as total_rewards
                FROM task_logs 
                WHERE token_id = ? AND DATE(created_at) = ?
                GROUP BY task_type
            ''', (token_id, today))
            
            results = cursor.fetchall()
            
            stats = {
                'browse_tasks': 0,
                'checkin_tasks': 0,
                'total_rewards': 0,
                'browse_rewards': 0,
                'checkin_rewards': 0
            }
            
            for row in results:
                task_type, count, rewards = row
                if task_type == 'browse':
                    stats['browse_tasks'] = count
                    stats['browse_rewards'] = float(rewards) if rewards else 0
                elif task_type == 'checkin':
                    stats['checkin_tasks'] = count
                    stats['checkin_rewards'] = float(rewards) if rewards else 0
                
                stats['total_rewards'] += float(rewards) if rewards else 0
            
            return stats
    
    def can_do_tasks(self, token_id: int) -> Dict:
        """检查Token是否可以执行任务"""
        stats = self.get_daily_task_stats(token_id)
        
        return {
            'can_browse': stats['browse_tasks'] < self.daily_browse_limit,
            'can_checkin': stats['checkin_tasks'] < self.daily_checkin_limit,
            'browse_remaining': max(0, self.daily_browse_limit - stats['browse_tasks']),
            'checkin_remaining': max(0, self.daily_checkin_limit - stats['checkin_tasks']),
            'stats': stats
        }
    
    def log_task_completion(self, token_id: int, task_type: str, task_id: str, rewards_earned: float):
        """记录任务完成情况"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_logs (token_id, task_type, task_id, rewards_earned)
                VALUES (?, ?, ?, ?)
            ''', (token_id, task_type, task_id, rewards_earned))
            conn.commit()
    
    def auto_complete_tasks_for_token(self, token_info: Dict) -> Dict:
        """为Token自动完成任务"""
        token_id = token_info['id']
        token = token_info['full_token']
        device_id = token_info.get('device_id')
        
        # 检查是否可以执行任务
        task_capability = self.can_do_tasks(token_id)
        if not task_capability['can_browse'] and not task_capability['can_checkin']:
            return {
                'success': False,
                'error': '今日任务已完成',
                'stats': task_capability['stats']
            }
        
        # 获取任务列表
        task_list_result = self.get_task_list(token, device_id)
        if not task_list_result or not task_list_result.get('success'):
            return {
                'success': False,
                'error': '获取任务列表失败',
                'details': task_list_result.get('error') if task_list_result else 'Unknown error'
            }
        
        tasks = task_list_result.get('tasks', [])
        completed_tasks = []
        total_rewards = 0
        
        # 执行浏览任务
        if task_capability['can_browse']:
            browse_tasks = [t for t in tasks if t.get('type') == 'browse' or 'browse' in t.get('name', '').lower()]
            browse_count = 0
            
            for task in browse_tasks:
                if browse_count >= task_capability['browse_remaining']:
                    break
                
                task_id = task.get('id') or task.get('taskId')
                if not task_id:
                    continue
                
                result = self.complete_task(token, task_id, device_id)
                if result and result.get('success'):
                    rewards = result.get('rewards_earned', 0)
                    self.log_task_completion(token_id, 'browse', task_id, rewards)
                    completed_tasks.append({
                        'type': 'browse',
                        'task_id': task_id,
                        'rewards': rewards
                    })
                    total_rewards += rewards
                    browse_count += 1
        
        # 执行签到任务
        if task_capability['can_checkin']:
            checkin_tasks = [t for t in tasks if t.get('type') == 'checkin' or 'checkin' in t.get('name', '').lower() or '签到' in t.get('name', '')]
            
            for task in checkin_tasks[:task_capability['checkin_remaining']]:
                task_id = task.get('id') or task.get('taskId')
                if not task_id:
                    continue
                
                result = self.complete_task(token, task_id, device_id)
                if result and result.get('success'):
                    rewards = result.get('rewards_earned', 0)
                    self.log_task_completion(token_id, 'checkin', task_id, rewards)
                    completed_tasks.append({
                        'type': 'checkin',
                        'task_id': task_id,
                        'rewards': rewards
                    })
                    total_rewards += rewards
        
        return {
            'success': True,
            'completed_tasks': completed_tasks,
            'total_rewards': total_rewards,
            'task_count': len(completed_tasks)
        }

# 全局任务系统实例
task_system = TaskSystem()