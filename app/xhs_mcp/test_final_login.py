#!/usr/bin/env python3
"""
测试完整的登录流程
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


async def test_login_workflow():
    """测试完整的登录流程"""
    print("=== 测试完整的登录流程 ===")

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
            name="test_login_workflow",
            fingerprint_name="windows_chrome",
            headless=False
        )
        instance = await pool.create_instance(profile)
        print(f"   创建实例成功: {instance.instance_id}")

        # 测试小红书服务
        print("3. 测试登录流程...")
        service = XHSService(pool)

        # 测试登录
        print("4. 调用登录方法...")
        account = await service.login(instance.instance_id)

        print(f"   登录结果:")
        print(f"   - 用户名: {account.username}")
        print(f"   - 昵称: {account.nickname or '未知'}")
        print(f"   - 登录状态: {'已登录' if account.is_logged_in else '未登录'}")
        print(f"   - 最后登录: {account.last_login or '未知'}")

        # 验证实例状态
        print("5. 验证实例状态...")
        updated_instance = await pool.get_instance(instance.instance_id)
        if updated_instance and updated_instance.account:
            print(f"   实例账户: {updated_instance.account.username}")
            print(f"   实例状态: {updated_instance.status}")
        else:
            print("   实例状态验证失败")

        print("=== 登录流程测试完成 ===")

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
    print("开始测试完整的登录流程...")
    print("注意：此测试会使用现有的 cookies 文件")
    print("如果 cookies 有效，会直接登录；否则会显示二维码")

    success = await test_login_workflow()

    if success:
        print("✅ 登录流程测试完成")
    else:
        print("❌ 登录流程测试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())