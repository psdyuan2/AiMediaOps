#!/usr/bin/env python3
"""
测试指纹配置和页面导航
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from app.xhs_mcp.browser.pool import BrowserPool
from app.xhs_mcp.config.fingerprint_manager import FingerprintManager


async def test_fingerprint():
    """测试指纹配置和页面导航"""
    print("=== 测试指纹配置和页面导航 ===")

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
            name="test_fingerprint",
            fingerprint_name="windows_chrome",
            headless=False  # 设置为 False 以便观察页面
        )
        instance = await pool.create_instance(profile)
        print(f"   创建实例成功: {instance.instance_id}")

        # 获取页面
        print("3. 获取页面...")
        page = await pool.get_page(instance.instance_id)
        if not page:
            raise ValueError("无法获取页面")
        print("   页面获取成功")

        # 导航到小红书首页
        print("4. 导航到小红书首页...")
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="networkidle")
        print("   页面导航成功")

        # 等待页面加载
        await page.wait_for_timeout(3000)

        # 检查页面内容
        print("5. 检查页面内容...")
        title = await page.title()
        print(f"   页面标题: {title}")

        # 检查是否有二维码弹窗
        qrcode_element = await page.query_selector(".login-container .qrcode-img")
        if qrcode_element:
            print("   检测到二维码弹窗")
            src = await qrcode_element.get_attribute("src")
            print(f"   二维码图片地址: {src}")
        else:
            print("   未检测到二维码弹窗")

        # 检查是否已登录
        login_status = await page.query_selector(".main-container .user .link-wrapper .channel")
        if login_status:
            print("   检测到已登录状态")
        else:
            print("   未检测到登录状态")

        # 截图保存
        print("6. 保存页面截图...")
        await page.screenshot(path="test_fingerprint_screenshot.png", full_page=True)
        print("   截图已保存到 test_fingerprint_screenshot.png")

        print("=== 指纹配置测试完成 ===")

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
    print("开始测试指纹配置和页面导航...")
    print("注意：此测试会打开浏览器窗口，请观察页面内容")

    success = await test_fingerprint()

    if success:
        print("✅ 指纹配置测试完成")
    else:
        print("❌ 指纹配置测试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())