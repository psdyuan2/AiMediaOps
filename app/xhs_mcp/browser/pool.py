"""
浏览器实例池管理

基于 Playwright 的多浏览器实例管理，支持沙盒隔离和指纹配置。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.xhs_mcp.core.models import (
    BrowserInstance,
    BrowserProfile,
    XHSAccount,
    BrowserInstanceStatus,
)


class BrowserPool:
    """浏览器实例池"""

    def __init__(self, max_instances: int = 10):
        self.max_instances = max_instances
        self.instances: Dict[str, BrowserInstance] = {}
        self.browsers: Dict[str, Browser] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}

        self.playwright = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """初始化浏览器池"""
        self.playwright = await async_playwright().start()
        self.logger.info("浏览器池初始化完成")

    async def create_instance(self, profile: BrowserProfile) -> BrowserInstance:
        """创建新的浏览器实例"""
        if len(self.instances) >= self.max_instances:
            raise RuntimeError(f"已达到最大实例数限制: {self.max_instances}")

        instance = BrowserInstance(profile=profile)

        try:
            # 启动浏览器
            browser = await self._launch_browser(profile)
            self.browsers[instance.instance_id] = browser

            # 创建上下文
            context = await self._create_context(browser, profile)
            self.contexts[instance.instance_id] = context

            # 创建页面
            page = await context.new_page()
            self.pages[instance.instance_id] = page

            # 设置指纹
            await self._set_fingerprint(page, profile.fingerprint)

            # 更新实例状态
            instance.status = BrowserInstanceStatus.RUNNING
            instance.start_time = datetime.now()
            self.instances[instance.instance_id] = instance

            self.logger.info(f"创建浏览器实例成功: {instance.instance_id}")
            return instance

        except Exception as e:
            self.logger.error(f"创建浏览器实例失败: {e}")
            instance.status = BrowserInstanceStatus.ERROR
            raise

    async def _launch_browser(self, profile: BrowserProfile) -> Browser:
        """启动浏览器"""
        launch_options = {
            "headless": profile.headless,
            "slow_mo": profile.slow_mo,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-web-security",
                "--disable-features=TranslateUI",
                "--disable-component-extensions-with-background-pages",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-translate",
                "--mute-audio",
                "--no-default-browser-check",
                "--no-first-run",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-back-forward-cache",
                "--disable-hang-monitor",
                "--disable-ipc-flooding-protection",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-background-timer-throttling",
                "--disable-client-side-phishing-detection",
                "--disable-cookie-encryption",
            ]
        }

        if profile.user_data_dir:
            launch_options["user_data_dir"] = profile.user_data_dir

        if profile.proxy:
            launch_options["proxy"] = profile.proxy

        browser = await self.playwright.chromium.launch(**launch_options)
        return browser

    async def _create_context(self, browser: Browser, profile: BrowserProfile) -> BrowserContext:
        """创建浏览器上下文"""
        context_options = {
            "viewport": profile.fingerprint.viewport,
            "user_agent": profile.fingerprint.user_agent,
            "locale": profile.fingerprint.language,
            "timezone_id": profile.fingerprint.timezone,
        }

        context = await browser.new_context(**context_options)

        # 加载 cookies
        await self._load_cookies(context)

        return context

    async def _load_cookies(self, context: BrowserContext) -> None:
        """加载 cookies"""
        import json
        import os

        # 检查 cookies 文件是否存在
        cookies_path = "xhs_mcp/cookies.json"
        if os.path.exists(cookies_path):
            try:
                with open(cookies_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)

                # 设置 cookies
                await context.add_cookies(cookies)
                self.logger.info(f"已加载 {len(cookies)} 个 cookies")

            except Exception as e:
                self.logger.warning(f"加载 cookies 失败: {e}")

    async def _set_fingerprint(self, page: Page, fingerprint) -> None:
        """设置浏览器指纹"""
        # 设置视口
        await page.set_viewport_size(fingerprint.viewport)

        # 注入 JavaScript 修改指纹和隐藏自动化特征
        await page.add_init_script("""
        // 修改硬件信息
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => %d
        });
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => %d
        });
        Object.defineProperty(navigator, 'platform', {
            get: () => '%s'
        });

        // 隐藏自动化特征
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['%s']
        });

        // 修改 Chrome 运行时特征
        window.chrome = {
            runtime: {},
            loadTimes: function(){},
            csi: function(){},
            app: {}
        };

        // 修改插件信息
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });

        // 修改 mimeTypes
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [1, 2, 3, 4, 5]
        });

        // 删除自动化痕迹
        delete navigator.__proto__.webdriver;
        """ % (
            fingerprint.hardware_concurrency,
            fingerprint.device_memory,
            fingerprint.platform,
            fingerprint.language
        ))

    async def get_instance(self, instance_id: str) -> Optional[BrowserInstance]:
        """获取浏览器实例"""
        return self.instances.get(instance_id)

    async def get_page(self, instance_id: str) -> Optional[Page]:
        """获取浏览器页面"""
        return self.pages.get(instance_id)

    async def pause_instance(self, instance_id: str) -> bool:
        """暂停浏览器实例"""
        if instance_id not in self.instances:
            return False

        instance = self.instances[instance_id]
        if instance.status != BrowserInstanceStatus.RUNNING:
            return False

        # 暂停页面活动
        page = self.pages.get(instance_id)
        if page:
            await page.pause()

        instance.status = BrowserInstanceStatus.PAUSED
        instance.updated_at = datetime.now()

        self.logger.info(f"暂停浏览器实例: {instance_id}")
        return True

    async def resume_instance(self, instance_id: str) -> bool:
        """恢复浏览器实例"""
        if instance_id not in self.instances:
            return False

        instance = self.instances[instance_id]
        if instance.status != BrowserInstanceStatus.PAUSED:
            return False

        # 在Playwright中，暂停/恢复是通过重新创建页面来实现的
        # 这里我们只是更新状态，因为实际的暂停/恢复需要更复杂的实现

        instance.status = BrowserInstanceStatus.RUNNING
        instance.updated_at = datetime.now()

        self.logger.info(f"恢复浏览器实例: {instance_id}")
        return True

    async def stop_instance(self, instance_id: str) -> bool:
        """停止浏览器实例"""
        if instance_id not in self.instances:
            return False

        instance = self.instances[instance_id]

        # 关闭页面
        if instance_id in self.pages:
            page = self.pages[instance_id]
            await page.close()
            del self.pages[instance_id]

        # 关闭上下文
        if instance_id in self.contexts:
            context = self.contexts[instance_id]
            await context.close()
            del self.contexts[instance_id]

        # 关闭浏览器
        if instance_id in self.browsers:
            browser = self.browsers[instance_id]
            await browser.close()
            del self.browsers[instance_id]

        instance.status = BrowserInstanceStatus.STOPPED
        instance.updated_at = datetime.now()

        self.logger.info(f"停止浏览器实例: {instance_id}")
        return True

    async def assign_account(self, instance_id: str, account: XHSAccount) -> bool:
        """为实例分配账户"""
        if instance_id not in self.instances:
            return False

        instance = self.instances[instance_id]
        instance.account = account
        account.browser_instance_id = instance_id
        instance.updated_at = datetime.now()

        self.logger.info(f"为实例 {instance_id} 分配账户: {account.username}")
        return True

    async def get_all_instances(self) -> List[BrowserInstance]:
        """获取所有浏览器实例"""
        return list(self.instances.values())

    async def get_running_instances(self) -> List[BrowserInstance]:
        """获取运行中的实例"""
        return [
            instance for instance in self.instances.values()
            if instance.status == BrowserInstanceStatus.RUNNING
        ]

    async def cleanup(self):
        """清理所有资源"""
        # 停止所有实例
        for instance_id in list(self.instances.keys()):
            await self.stop_instance(instance_id)

        # 关闭 Playwright
        if self.playwright:
            await self.playwright.stop()

        self.logger.info("浏览器池清理完成")

