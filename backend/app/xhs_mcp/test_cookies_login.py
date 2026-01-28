#!/usr/bin/env python3
"""
测试使用 cookies 登录小红书
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
from app.xhs_mcp.core.models import XHSAccount


async def test_cookies_login():
    """测试使用 cookies 登录"""
    print("=== 测试使用 cookies 登录小红书 ===")

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
            name="test_cookies_login",
            fingerprint_name="windows_chrome",
            headless=False
        )
        instance = await pool.create_instance(profile)
        print(f"   创建实例成功: {instance.instance_id}")

        # 测试小红书服务
        print("3. 测试登录状态...")
        service = XHSService(pool)

        # 获取页面
        page = await pool.get_page(instance.instance_id)
        if not page:
            raise ValueError("无法获取页面")

        # 导航到小红书首页
        print("4. 导航到小红书首页...")
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=10000)
        await page.wait_for_timeout(2000)

        # 检查页面内容
        title = await page.title()
        print(f"   页面标题: {title}")

        # 检查是否已登录
        is_logged_in = await service._check_logged_in(page)
        print(f"   登录状态: {'已登录' if is_logged_in else '未登录'}")

        if is_logged_in:
            print("   ✅ 使用 cookies 登录成功")

            # 获取账户信息
            account_info = await service._get_account_info(page)
            print(f"   账户昵称: {account_info.get('nickname', '未知')}")

            # 直接创建账户对象，不需要再次调用 login()
            account = XHSAccount(
                username="已登录用户",
                nickname=account_info.get("nickname"),
                is_logged_in=True,
                last_login=account_info.get("last_login"),
            )
            await pool.assign_account(instance.instance_id, account)
            print(f"   登录账户: {account.nickname}")
        else:
            print("   ❌ 使用 cookies 登录失败")

            # 检查是否有二维码
            qrcode_src = await service._fetch_qrcode_image(page)
            if qrcode_src:
                print(f"   检测到二维码: {qrcode_src}")
                print("   请使用小红书APP扫描二维码登录...")
            else:
                print("   未检测到二维码")

        # 截图保存
        await page.screenshot(path="test_cookies_login_screenshot.png", full_page=True)
        print("   截图已保存到 test_cookies_login_screenshot.png")

        print("=== cookies 登录测试完成 ===")

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
    print("开始测试使用 cookies 登录小红书...")
    print("注意：此测试会使用现有的 cookies 文件")

    success = await test_cookies_login()

    if success:
        print("✅ cookies 登录测试完成")
    else:
        print("❌ cookies 登录测试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())