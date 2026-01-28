#!/usr/bin/env python3
"""
调试浏览器配置和页面加载
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from app.xhs_mcp.browser.pool import BrowserPool
from app.xhs_mcp.config.fingerprint_manager import FingerprintManager


async def debug_browser():
    """调试浏览器配置"""
    print("=== 调试浏览器配置和页面加载 ===")

    try:
        # 初始化浏览器池
        print("1. 初始化浏览器池...")
        pool = BrowserPool(max_instances=5)
        await pool.initialize()
        print("   浏览器池初始化成功")

        # 创建浏览器实例
        print("2. 创建浏览器实例...")
        manager = FingerprintManager()

        # 查看可用的指纹配置
        fingerprints = manager.get_all_fingerprints()
        print(f"   可用的指纹配置: {list(fingerprints.keys())}")

        profile = manager.create_browser_profile(
            name="debug_browser",
            fingerprint_name="windows_chrome",
            headless=False
        )
        print(f"   浏览器配置: {profile}")

        instance = await pool.create_instance(profile)
        print(f"   创建实例成功: {instance.instance_id}")

        # 获取页面
        print("3. 获取页面...")
        page = await pool.get_page(instance.instance_id)
        if not page:
            raise ValueError("无法获取页面")
        print("   页面获取成功")

        # 测试导航到简单页面
        print("4. 导航到百度首页测试...")
        await page.goto("https://www.baidu.com", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        title = await page.title()
        print(f"   百度页面标题: {title}")

        # 截图保存
        await page.screenshot(path="debug_baidu_screenshot.png", full_page=True)
        print("   百度截图已保存")

        # 测试导航到小红书
        print("5. 导航到小红书首页...")
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="networkidle")
        await page.wait_for_timeout(5000)  # 等待更长时间

        title = await page.title()
        print(f"   小红书页面标题: {title}")

        # 检查页面内容
        content = await page.content()
        print(f"   页面内容长度: {len(content)}")

        # 检查是否有错误信息
        error_element = await page.query_selector("body")
        if error_element:
            body_text = await error_element.text_content()
            if body_text:
                print(f"   页面正文前100字符: {body_text[:100]}")

        # 检查网络请求
        print("6. 检查网络请求...")
        try:
            response = await page.goto("https://www.xiaohongshu.com/explore", wait_until="networkidle")
            if response:
                print(f"   响应状态码: {response.status}")
                print(f"   响应URL: {response.url}")
        except Exception as e:
            print(f"   导航错误: {e}")

        # 截图保存
        await page.screenshot(path="debug_xhs_screenshot.png", full_page=True)
        print("   小红书截图已保存")

        print("=== 浏览器调试完成 ===")

        # 清理资源
        await pool.cleanup()

    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """主函数"""
    print("开始调试浏览器配置...")
    print("注意：此测试会打开浏览器窗口，请观察页面内容")

    success = await debug_browser()

    if success:
        print("✅ 浏览器调试完成")
    else:
        print("❌ 浏览器调试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())