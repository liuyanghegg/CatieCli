#!/usr/bin/env python3
"""
WenXiaoBai API Proxy 启动脚本
"""
import os
import sys
from pathlib import Path

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("❌ Python 版本过低，需要 Python 3.8+")
        return False
    
    print(f"✅ Python 版本: {sys.version}")
    
    # 检查必要的目录
    dirs_to_create = ["sessions", "logs", "data"]
    for dir_name in dirs_to_create:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        print(f"✅ 目录已创建: {dir_name}/")
    
    # 检查环境变量
    env_vars = {
        "API_USERNAME": "web.1.0.beta",
        "API_SECRET_KEY": "TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z",
        "PORT": "8080",
        "FLASK_ENV": "production"
    }
    
    for var, default in env_vars.items():
        value = os.environ.get(var, default)
        os.environ[var] = value
        print(f"✅ {var}: {value}")
    
    return True

def main():
    """主函数"""
    print("🚀 WenXiaoBai API Proxy 启动中...")
    print("=" * 50)
    
    if not check_environment():
        print("❌ 环境检查失败")
        sys.exit(1)
    
    print("\n📋 系统信息:")
    print("   - 多用户支持: ✅")
    print("   - 管理员控制台: ✅") 
    print("   - Token 重复检测: ✅")
    print("   - 自动任务系统: ✅")
    print("   - OpenAI API 兼容: ✅")
    
    print("\n🌐 访问地址:")
    port = os.environ.get("PORT", "8080")
    print(f"   - API 服务: http://localhost:{port}")
    print(f"   - 用户控制台: http://localhost:{port}/dashboard.html")
    print(f"   - 管理员控制台: http://localhost:{port}/admin.html")
    
    print("\n🔑 默认账户:")
    print("   - 管理员: admin / admin123")
    print("   - 用户可自行注册")
    
    print("\n" + "=" * 50)
    print("🎉 启动 Flask 应用...")
    
    # 导入并启动应用
    try:
        from main import app
        app.run(
            host="0.0.0.0",
            port=int(port),
            debug=os.environ.get("FLASK_ENV") != "production"
        )
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()