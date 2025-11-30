#!/usr/bin/env python3
"""
测试修复后的扫码登录功能
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from app.xhs_mcp.browser.pool import BrowserPool
from app.xhs_mcp.config.fingerprint_manager import FingerprintManager
from app.xhs_mcp.services.xhs_service import XHSService


async def test_qrcode_login():
    """测试扫码登录"""
    print("=== 测试小红书扫码登录 ===")

    try:
        # 初始化浏览器池
        print("1. 初始化浏览器池...")
        pool = BrowserPool(max_instances=5)
        await pool.initialize()
        print("   浏览器池初始化成功")

        # 创建浏览器实例
        print("2. 创建浏览器实例...")
        manager = FingerprintManager()
        profile = manager.create_browser_profile(
            name="test_login",
            fingerprint_name="windows_chrome",
            headless=False  # 设置为 False 以便观察登录过程
        )
        instance = await pool.create_instance(profile)
        print(f"   创建实例成功: {instance.instance_id}")

        # 测试小红书服务
        print("3. 测试扫码登录...")
        service = XHSService(pool)

        # 尝试登录（会显示二维码）
        print("   请使用小红书APP扫描二维码登录...")
        print("   注意：登录过程需要人工操作，请观察浏览器窗口")

        # 设置超时时间较短，避免长时间等待
        account = await service.login(instance.instance_id)

        print(f"   登录成功: {account.nickname}")
        print("=== 扫码登录测试完成 ===")

        # 清理资源
        await pool.cleanup()

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """主函数"""
    print("开始测试修复后的扫码登录功能...")
    print("注意：此测试需要人工扫码登录，请准备好小红书APP")

    success = await test_qrcode_login()

    if success:
        print("✅ 扫码登录功能测试完成")
    else:
        print("❌ 扫码登录功能测试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())