import os
import time
import random
import logging
from dataclasses import dataclass
from typing import List, Optional

from playwright.sync_api import Page, Locator, expect, TimeoutError as PlaywrightTimeoutError

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义常量
URL_OF_PUBLIC = "https://creator.xiaohongshu.com/publish/publish?source=official"


@dataclass
class PublishImageContent:
    """发布内容的数据结构"""
    title: str
    content: str
    tags: List[str]
    image_paths: List[str]


class PublishAction:
    def __init__(self, page: Page):
        self.page = page
        # 设置全局默认超时时间，对应 Go 中的 page.Timeout
        self.page.set_default_timeout(30000)  # 30秒，Go代码里虽然写了300秒，但在具体步骤里有更短的超时

    @classmethod
    def new_publish_image_action(cls, page: Page) -> 'PublishAction':
        """初始化发布动作，导航并点击Tab"""
        # 增加页面导航超时设置
        page.goto(URL_OF_PUBLIC, timeout=60000)
        page.wait_for_load_state('networkidle')  # 等待网络空闲
        page.wait_for_load_state('domcontentloaded')

        time.sleep(1)

        if not cls._must_click_publish_tab(page, "上传图文"):
            raise Exception("点击上传图文 TAB 失败")

        time.sleep(1)
        return cls(page)

    def publish(self, content: PublishImageContent):
        """执行发布流程"""
        if not content.image_paths:
            raise ValueError("图片不能为空")

        # 1. 上传图片
        self._upload_images(content.image_paths)

        # 2. 处理标签数量
        tags = content.tags
        if len(tags) >= 10:
            logger.warning("标签数量超过10，截取前10个标签")
            tags = tags[:10]

        logger.info(f"发布内容: title={content.title}, images={len(content.image_paths)}, tags={tags}")

        # 3. 填写内容并提交
        self._submit_publish(content.title, content.content, tags)

    @staticmethod
    def _remove_pop_cover(page: Page):
        """移除遮挡的弹窗"""
        popover = page.locator("div.d-popover")
        if popover.count() > 0 and popover.is_visible():
            # 尝试通过 JS 移除
            page.evaluate("document.querySelector('div.d-popover')?.remove()")

        # 兜底：点击空位置
        PublishAction._click_empty_position(page)

    @staticmethod
    def _click_empty_position(page: Page):
        """点击空白处"""
        x = 380 + random.randint(0, 100)
        y = 20 + random.randint(0, 60)
        page.mouse.move(x, y)
        page.mouse.click()

    @classmethod
    def _must_click_publish_tab(cls, page: Page, tabname: str) -> bool:
        """点击指定的发布Tab"""
        try:
            page.wait_for_selector("div.upload-content", state="visible", timeout=15000)
        except PlaywrightTimeoutError:
            logger.error("未找到 div.upload-content")
            return False

        deadline = time.time() + 15
        while time.time() < deadline:
            tab_element = cls._get_tab_element(page, tabname)

            if not tab_element:
                time.sleep(0.2)
                continue

            # 检查遮挡 (Playwright 自动处理大部分遮挡，但为了还原逻辑我们手动检查)
            # 在 Playwright 中，click(force=False) 会检查遮挡。
            # 如果被遮挡，我们捕获错误并处理
            try:
                # 尝试点击，如果被遮挡 Playwright 会报错（除非设置 force=True）
                # 这里我们模拟 Go 代码逻辑：先判断遮挡，移除遮挡，再点击
                if cls._is_element_blocked(tab_element):
                    logger.info("发布 TAB 被遮挡，尝试移除遮挡")
                    cls._remove_pop_cover(page)
                    time.sleep(0.2)
                    continue

                tab_element.click()
                return True
            except Exception as e:
                logger.warning(f"点击发布 TAB 失败: {e}")
                time.sleep(0.2)
                continue

        logger.error(f"没有找到发布 TAB - {tabname}")
        return False

    @staticmethod
    def _get_tab_element(page: Page, tabname: str) -> Optional[Locator]:
        """获取对应文本的Tab元素"""
        tabs = page.locator("div.creator-tab").all()
        for tab in tabs:
            if not tab.is_visible():
                continue

            text = tab.inner_text()
            if text.strip() != tabname:
                continue

            return tab
        return None

    @staticmethod
    def _is_element_blocked(locator: Locator) -> bool:
        """检查元素是否被遮挡 (JS Eval)"""
        return locator.evaluate("""(element) => {
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return true;
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;
            const target = document.elementFromPoint(x, y);
            return !(target === element || element.contains(target));
        }""")

    def _upload_images(self, image_paths: List[str]):
        """上传图片"""
        # 验证文件路径
        valid_paths = []
        for path in image_paths:
            if not os.path.exists(path):
                logger.warning(f"图片文件不存在: {path}")
                continue
            valid_paths.append(path)
            logger.info(f"获取有效图片：{path}")

        if not valid_paths:
            raise ValueError("没有有效的图片文件")

        # 上传文件
        upload_input = self.page.locator(".upload-input")
        upload_input.set_input_files(valid_paths)

        # 等待上传完成
        self._wait_for_upload_complete(len(valid_paths))

    def _wait_for_upload_complete(self, expected_count: int):
        """等待上传完成"""
        max_wait_time = 60
        check_interval = 0.5
        start_time = time.time()

        logger.info(f"开始等待图片上传完成, expected_count={expected_count}")

        while time.time() - start_time < max_wait_time:
            uploaded_images = self.page.locator(".img-preview-area .pr").all()
            current_count = len(uploaded_images)

            # 这里打印的内容对应 Go 代码中的 slog
            # logger.info(f"uploadedImages count: {current_count}")

            if current_count >= expected_count:
                logger.info(f"所有图片上传完成, count={current_count}")
                return
            else:
                logger.debug("未找到已上传图片元素或数量不足")

            time.sleep(check_interval)

        raise Exception("上传超时，请检查网络连接和图片大小")

    def _submit_publish(self, title: str, content: str, tags: List[str]):
        """填写信息并提交"""
        # 填写标题
        title_elem = self.page.locator("div.d-input input")
        title_elem.fill(title)
        time.sleep(1)

        # 获取并填写内容
        content_elem = self._get_content_element()
        if content_elem:
            # fill 会直接覆盖，Go 代码中使用的是 Input，Playwright 对应 fill 或 type
            content_elem.fill(content)
            self._input_tags(content_elem, tags)
        else:
            raise Exception("没有找到内容输入框")

        time.sleep(1)

        # 提交按钮
        submit_button = self.page.locator("div.submit div.d-button-content")
        submit_button.click()

        time.sleep(3)

    def _get_content_element(self) -> Optional[Locator]:
        """查找内容输入框，模拟 Go 的 Race 逻辑"""
        # 策略1: div.ql-editor
        elem1 = self.page.locator("div.ql-editor")
        if elem1.count() > 0 and elem1.is_visible():
            return elem1

        # 策略2: 通过 placeholder 查找
        elem2 = self._find_textbox_by_placeholder()
        if elem2:
            return elem2

        logger.warning("no content element found by any method")
        return None

    def _find_textbox_by_placeholder(self) -> Optional[Locator]:
        """通过 placeholder 向上查找 textbox"""
        # 查找包含特定 placeholder 的 p 标签
        # Playwright 有更强大的 locator，可以直接定位属性
        placeholder_elem = self.page.locator("p[data-placeholder*='输入正文描述']").first

        if placeholder_elem.count() == 0:
            return None

        # 向上查找 role=textbox 的父元素
        current_locator = placeholder_elem
        # Playwright locator 也是 lazy 的，这里需要通过 locator 构建父级定位
        # 简单起见，我们使用 XPath 或者定位器的 parent 属性
        # 这里模拟 Go 循环 5 次向上查

        try:
            # 这里的逻辑在 Playwright 中可以通过 locator("xpath=..") 实现
            # 或者更简单的：使用 Playwright 的 filters
            return self.page.locator("div[role='textbox']").filter(has=placeholder_elem).first
        except:
            return None

    def _input_tags(self, content_elem: Locator, tags: List[str]):
        """输入标签"""
        if not tags:
            return

        time.sleep(1)

        # 移动光标到底部 (模拟 Go 代码的 20 次 ArrowDown)
        # 注意：content_elem 需要 focus
        content_elem.click()
        for _ in range(20):
            content_elem.press("ArrowDown")
            time.sleep(0.01)

        content_elem.press("Enter")
        content_elem.press("Enter")
        time.sleep(1)

        for tag in tags:
            tag = tag.lstrip("#")
            self._input_single_tag(content_elem, tag)

    def _input_single_tag(self, content_elem: Locator, tag: str):
        """输入单个标签并处理联想"""
        content_elem.type("#")
        time.sleep(0.2)

        # 逐字输入
        content_elem.type(tag, delay=50)  # Playwright type 自带 delay 参数，单位毫秒
        time.sleep(1)

        # 查找联想词
        topic_container = self.page.locator("#creator-editor-topic-container")

        # 检查容器是否存在
        if topic_container.count() > 0 and topic_container.is_visible():
            first_item = topic_container.locator(".item").first
            if first_item.count() > 0:
                first_item.click()
                logger.info(f"成功点击标签联想选项: {tag}")
                time.sleep(0.2)
                return
            else:
                logger.warning(f"未找到标签联想选项，直接输入空格: {tag}")
        else:
            logger.warning(f"未找到标签联想下拉框，直接输入空格: {tag}")

        # 兜底：输入空格
        content_elem.type(" ")
        time.sleep(0.5)


# --- 使用示例 ---
def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # 启动浏览器，headless=False 可以看到界面，方便调试
        # 需要确保你已经登录过，或者使用 user_data_dir 加载已有登录状态的 Profile
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        try:
            # 1. 初始化 Action
            # 注意：实际使用时需要确保浏览器已经处于登录状态，
            # 否则进入页面会跳转登录页，导致找不到 Tab 元素
            action = PublishAction.new_publish_image_action(page)

            # 2. 准备数据
            content = PublishImageContent(
                title="Python 脚本发布测试",
                content="这是由 Python Playwright 脚本自动发布的内容。\n测试换行。",
                tags=["测试", "Python", "自动化"],
                image_paths=[
                    "/Users/ds/PycharmProjects/AiMediaOps/xhs_mcp/openai.jpeg",  # 替换为实际路径
                    # "/Users/yourname/Pictures/test2.jpg"
                ]
            )

            # 3. 发布
            action.publish(content)

            logger.info("流程结束")

        except Exception as e:
            logger.error(f"发生错误: {e}")
            # 截图保存错误现场
            page.screenshot(path="error.png")
        finally:
            time.sleep(5)  # 观察一下
            browser.close()


if __name__ == "__main__":
    main()