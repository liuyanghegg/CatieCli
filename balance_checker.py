#!/usr/bin/env python3
"""
文小白余额查询模块
"""
import requests
import json
import hashlib
import base64
from datetime import datetime
import pytz
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class BalanceChecker:
    def __init__(self):
        self.base_url = "https://api-bj.wenxiaobai.com"
        self.balance_endpoint = "/rest/api/asset/summary"
    
    def _get_rfc1123_date(self):
        """获取RFC1123格式的日期"""
        return datetime.now(pytz.timezone('GMT')).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    def check_balance(self, token: str, device_id: str = None) -> Optional[Dict]:
        """
        查询文小白账户余额
        
        Args:
            token: 用户的access token
            device_id: 设备ID（可选）
            
        Returns:
            Dict: 包含余额信息的字典，失败时返回None
        """
        try:
            # 构建请求头
            headers = {
                'Connection': 'Keep-Alive',
                'Host': 'api-bj.wenxiaobai.com',
                'accept': 'application/json',
                'accept-language': 'zh',
                'user-agent': 'wanyu/5.0.1/7050001 (Android 28)',
                'x-date': self._get_rfc1123_date(),
                'x-yuanshi-appname': 'wanyu',
                'x-yuanshi-appversioncode': '7050001',
                'x-yuanshi-appversionname': '5.0.1',
                'x-yuanshi-authorization': f'Bearer {token}',
                'x-yuanshi-platform': 'android',
                'x-yuanshi-rnversion': '5.0.2',
                'x-yuanshi-timezone': 'Asia/Shanghai',
                'x-yuanshi-timezonesecfromcmt': '28800'
            }
            
            # 如果提供了device_id，添加到请求头
            if device_id:
                headers['x-yuanshi-deviceid'] = device_id
            
            # 发送请求
            response = requests.get(
                f"{self.base_url}{self.balance_endpoint}",
                headers=headers,
                timeout=10,
                verify=False  # 禁用SSL验证
            )
            
            logger.info(f"Balance check response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    # 解析余额信息
                    assets = data.get('data', {}).get('assets', [])
                    user_info = data.get('data', {}).get('userInfo', {})
                    
                    balance_info = {
                        'success': True,
                        'user_info': {
                            'nickname': user_info.get('nickname', ''),
                            'avatar': user_info.get('avatar', ''),
                            'vip_flag': user_info.get('vipFlag', 0),
                            'expired': user_info.get('expired', False)
                        },
                        'balances': {}
                    }
                    
                    # 提取各种资产余额
                    for asset in assets:
                        asset_type = asset.get('type', '')
                        asset_name = asset.get('name', '')
                        amount = asset.get('amount', '0')
                        display_amount = asset.get('displayAmount', amount)
                        
                        balance_info['balances'][asset_type] = {
                            'name': asset_name,
                            'amount': float(amount) if amount else 0,
                            'display_amount': display_amount
                        }
                    
                    # 获取蒜粒余额（主要关注的余额）
                    suanli_balance = balance_info['balances'].get('suanli', {}).get('amount', 0)
                    balance_info['suanli_balance'] = suanli_balance
                    
                    logger.info(f"Balance check successful: {suanli_balance} 蒜粒")
                    return balance_info
                else:
                    logger.error(f"Balance check API error: {data.get('msg', 'Unknown error')}")
                    return {
                        'success': False,
                        'error': data.get('msg', 'API返回错误'),
                        'code': data.get('code')
                    }
            else:
                logger.error(f"Balance check HTTP error: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP错误: {response.status_code}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("Balance check timeout")
            return {
                'success': False,
                'error': '请求超时'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Balance check request error: {e}")
            return {
                'success': False,
                'error': f'网络请求错误: {str(e)}'
            }
        except json.JSONDecodeError as e:
            logger.error(f"Balance check JSON decode error: {e}")
            return {
                'success': False,
                'error': '响应数据格式错误'
            }
        except Exception as e:
            logger.error(f"Balance check unexpected error: {e}")
            return {
                'success': False,
                'error': f'未知错误: {str(e)}'
            }
    
    def batch_check_balances(self, tokens_info: list) -> Dict:
        """
        批量查询余额
        
        Args:
            tokens_info: 包含token信息的列表，每个元素包含 {'id', 'token', 'device_id'}
            
        Returns:
            Dict: 批量查询结果
        """
        results = {
            'success_count': 0,
            'failed_count': 0,
            'results': []
        }
        
        for token_info in tokens_info:
            token_id = token_info.get('id')
            token = token_info.get('token')
            device_id = token_info.get('device_id')
            
            logger.info(f"Checking balance for token ID: {token_id}")
            
            balance_result = self.check_balance(token, device_id)
            
            result_item = {
                'token_id': token_id,
                'balance_result': balance_result
            }
            
            if balance_result and balance_result.get('success'):
                results['success_count'] += 1
                result_item['balance'] = balance_result.get('suanli_balance', 0)
            else:
                results['failed_count'] += 1
                result_item['error'] = balance_result.get('error', '未知错误') if balance_result else '查询失败'
            
            results['results'].append(result_item)
        
        logger.info(f"Batch balance check completed: {results['success_count']} success, {results['failed_count']} failed")
        return results

# 全局余额查询实例
balance_checker = BalanceChecker()