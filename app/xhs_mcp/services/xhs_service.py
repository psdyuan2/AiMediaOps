"""
小红书操作服务

基于 Playwright 实现小红书的各种操作功能。
"""

import asyncio
import logging
import time
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

from playwright.async_api import Page

from app.xhs_mcp.core.models import BrowserInstance, XHSAccount
from app.xhs_mcp.browser.pool import BrowserPool


class XHSService:
    """小红书操作服务"""

    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.logger = logging.getLogger(__name__)

    async def login(
        self,
        instance_id: str
    ) -> XHSAccount:
        """小红书扫码登录"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 导航到小红书首页，这会触发二维码弹窗
            await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            # 检查是否已经登录
            if await self._check_logged_in(page):
                self.logger.info(f"实例 {instance_id} 已经登录")
                account_info = await self._get_account_info(page)
                account = XHSAccount(
                    username="已登录用户",
                    nickname=account_info.get("nickname"),
                    is_logged_in=True,
                    last_login=account_info.get("last_login"),
                )
                await self.browser_pool.assign_account(instance_id, account)
                return account

            # 如果未登录，获取二维码图片
            qrcode_src = await self._fetch_qrcode_image(page)
            if qrcode_src:
                self.logger.info(f"获取到二维码: {qrcode_src}")
                # 这里可以返回二维码给用户扫描
                # 在实际使用中，可以将二维码图片保存或显示给用户

            # 等待用户扫码登录
            self.logger.info("请使用小红书APP扫描二维码登录...")

            # 等待登录成功
            if await self._wait_for_login(page):
                account_info = await self._get_account_info(page)
                account = XHSAccount(
                    username="扫码登录用户",
                    nickname=account_info.get("nickname"),
                    is_logged_in=True,
                    last_login=account_info.get("last_login"),
                )
                await self.browser_pool.assign_account(instance_id, account)
                self.logger.info("扫码登录成功")
                return account
            else:
                raise Exception("扫码登录超时或失败")

        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            raise

    async def _check_logged_in(self, page: Page) -> bool:
        """检查是否已登录"""
        try:
            # 使用 Go 代码中的选择器检查登录状态
            login_status_element = await page.query_selector(".main-container .user .link-wrapper .channel")
            return login_status_element is not None
        except:
            return False

    async def _get_account_info(self, page: Page) -> Dict[str, Any]:
        """获取账户信息"""
        try:
            # 点击用户头像查看个人信息
            user_avatar = await page.query_selector(".avatar, [data-testid=\"user-avatar\"]")
            if user_avatar:
                await user_avatar.click()
                await page.wait_for_timeout(2000)

                # 获取昵称
                nickname_element = await page.query_selector(".nickname, [data-testid=\"user-nickname\"]")
                nickname = await nickname_element.text_content() if nickname_element else None

                return {
                    "nickname": nickname.strip() if nickname else None,
                    "last_login": time.time()
                }
        except Exception as e:
            self.logger.warning(f"获取账户信息失败: {e}")

        return {}

    async def _fetch_qrcode_image(self, page: Page) -> Optional[str]:
        """获取二维码图片"""
        try:
            # 检查是否已经登录
            if await self._check_logged_in(page):
                return None

            # 使用 Go 代码中的选择器获取二维码
            qrcode_img = await page.query_selector(".login-container .qrcode-img")
            if qrcode_img:
                src = await qrcode_img.get_attribute("src")
                if src:
                    return src

            return None
        except Exception as e:
            self.logger.warning(f"获取二维码失败: {e}")
            return None

    async def _wait_for_login(self, page: Page, timeout: int = 120) -> bool:
        """等待用户扫码登录"""
        import asyncio

        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self._check_logged_in(page):
                return True
            await asyncio.sleep(2)

        return False

    async def publish_note(
        self,
        instance_id: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """发布图文笔记 - 完全复制Go版本逻辑"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 完全复制Go版本逻辑
            publish_url = "https://creator.xiaohongshu.com/publish/publish?source=official"
            self.logger.info(f"导航到发布页面: {publish_url}")

            # 设置超时 - 完全复制Go版本
            page.set_default_timeout(300000)  # 300秒 = 5分钟

            # 导航到发布页面 - 完全复制Go版本
            await page.goto(publish_url)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)  # 完全复制 time.Sleep(1 * time.Second)

            # 检查是否登录
            if not await self._check_logged_in(page):
                raise Exception("请先登录")

            # 切换到"上传图文"TAB - 完全复制Go版本
            await self._must_click_publish_tab(page, "上传图文")
            await asyncio.sleep(1)  # 完全复制 time.Sleep(1 * time.Second)

            # 上传图片 - 完全复制Go版本
            if not images:
                raise Exception("图片不能为空")

            await self._upload_images_exact(page, images)

            # 限制标签数量 - 完全复制Go版本
            tags_list = tags or []
            if len(tags_list) >= 10:
                self.logger.warning("标签数量超过10，截取前10个标签")
                tags_list = tags_list[:10]

            # 使用内容前50字符作为标题 - 完全复制Go版本
            title = content[:50] if content else "默认标题"
            self.logger.info(f"发布内容: title={title}, images={len(images)}, tags={tags_list}")

            # 提交发布 - 完全复制Go版本
            await self._submit_publish_exact(page, title, content, tags_list)

            self.logger.info(f"发布成功: {content[:50]}...")
            return {"success": True, "message": "发布成功"}

        except Exception as e:
            self.logger.error(f"发布失败: {e}")
            raise

    async def _must_click_publish_tab(self, page, tabname: str):
        """完全复制Go版本的mustClickPublishTab"""
        # 等待上传内容区域 - 完全复制Go版本
        await page.wait_for_selector("div.upload-content")

        deadline = asyncio.get_event_loop().time() + 15  # 15秒超时

        while asyncio.get_event_loop().time() < deadline:
            tab, blocked, err = await self._get_tab_element(page, tabname)

            if err:
                self.logger.warning(f"获取发布 TAB 元素失败: {err}")
                await asyncio.sleep(0.2)  # 200ms
                continue

            if tab is None:
                await asyncio.sleep(0.2)  # 200ms
                continue

            if blocked:
                self.logger.info("发布 TAB 被遮挡，尝试移除遮挡")
                await self._remove_pop_cover(page)
                await asyncio.sleep(0.2)  # 200ms
                continue

            try:
                await tab.click()
                return
            except Exception as e:
                self.logger.warning(f"点击发布 TAB 失败: {e}")
                await asyncio.sleep(0.2)  # 200ms
                continue

        raise Exception(f"没有找到发布 TAB - {tabname}")

    async def _get_tab_element(self, page, tabname: str):
        """完全复制Go版本的getTabElement"""
        try:
            elems = await page.query_selector_all("div.creator-tab")

            for elem in elems:
                if not await self._is_element_visible(elem):
                    continue

                text = await elem.text_content()
                if text and text.strip() != tabname:
                    continue

                blocked, err = await self._is_element_blocked_exact(elem)
                if err:
                    return None, False, err

                return elem, blocked, None

            return None, False, None
        except Exception as e:
            return None, False, e

    async def _is_element_visible(self, elem):
        """完全复制Go版本的isElementVisible"""
        try:
            # 检查是否有隐藏样式
            style = await elem.get_attribute("style")
            if style:
                style_str = style
                if ("left: -9999px" in style_str or
                    "top: -9999px" in style_str or
                    "position: absolute; left: -9999px" in style_str or
                    "display: none" in style_str or
                    "visibility: hidden" in style_str):
                    return False

            visible = await elem.is_visible()
            if not visible:
                return False

            return True
        except:
            return True

    async def _is_element_blocked_exact(self, elem):
        """完全复制Go版本的isElementBlocked"""
        try:
            result = await elem.evaluate("""() => {
                const rect = this.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) {
                    return true;
                }
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                const target = document.elementFromPoint(x, y);
                return !(target === this || this.contains(target));
            }""")
            return bool(result), None
        except Exception as e:
            return False, e

    async def _remove_pop_cover(self, page):
        """完全复制Go版本的removePopCover"""
        # 先移除弹窗封面
        try:
            popover = await page.query_selector("div.d-popover")
            if popover:
                await popover.evaluate("elem => elem.remove()")
        except:
            pass

        # 兜底：点击一下空位置吧
        await self._click_empty_position(page)

    async def _click_empty_position(self, page):
        """完全复制Go版本的clickEmptyPosition"""
        import random
        x = 380 + random.randint(0, 100)
        y = 20 + random.randint(0, 60)
        await page.mouse.move(x, y)
        await page.mouse.click(x, y)

    async def _upload_images_exact(self, page, image_paths: List[str]):
        """完全复制Go版本的uploadImages"""
        # 设置超时 - 完全复制Go版本
        page.set_default_timeout(30000)  # 30秒

        # 验证文件路径有效性 - 完全复制Go版本
        valid_paths = []
        for path in image_paths:
            if os.path.exists(path):
                valid_paths.append(path)
                self.logger.info(f"获取有效图片：{path}")
            else:
                self.logger.warning(f"图片文件不存在: {path}")

        # 等待上传输入框出现 - 完全复制Go版本
        upload_input = await page.wait_for_selector(".upload-input")

        # 上传多个文件 - 完全复制Go版本
        await upload_input.set_input_files(valid_paths)

        # 等待并验证上传完成 - 完全复制Go版本
        await self._wait_for_upload_complete_exact(page, len(valid_paths))

    async def _wait_for_upload_complete_exact(self, page, expected_count: int):
        """完全复制Go版本的waitForUploadComplete"""
        max_wait_time = 60  # 60秒
        check_interval = 0.5  # 500ms
        start_time = asyncio.get_event_loop().time()

        self.logger.info(f"开始等待图片上传完成，期望数量: {expected_count}")

        while asyncio.get_event_loop().time() - start_time < max_wait_time:
            # 使用具体的pr类名检查已上传的图片 - 完全复制Go版本
            try:
                uploaded_images = await page.query_selector_all(".img-preview-area .pr")
                current_count = len(uploaded_images)

                self.logger.info(f"检测到已上传图片: {current_count}/{expected_count}")

                if current_count >= expected_count:
                    self.logger.info(f"所有图片上传完成: {current_count}")
                    return
            except Exception as e:
                self.logger.debug(f"未找到已上传图片元素: {e}")

            await asyncio.sleep(check_interval)

        raise Exception("上传超时，请检查网络连接和图片大小")

    async def _submit_publish_exact(self, page, title: str, content: str, tags: List[str]):
        """完全复制Go版本的submitPublish"""
        # 输入标题 - 完全复制Go版本
        title_elem = await page.wait_for_selector("div.d-input input")
        await title_elem.fill(title)
        await asyncio.sleep(1)  # time.Sleep(1 * time.Second)

        # 输入内容 - 完全复制Go版本
        content_elem, ok = await self._get_content_element_exact(page)
        if ok:
            await content_elem.fill(content)
            await self._input_tags_exact(content_elem, tags)
        else:
            raise Exception("没有找到内容输入框")

        await asyncio.sleep(1)  # time.Sleep(1 * time.Second)

        # 点击发布按钮 - 完全复制Go版本
        submit_button = await page.wait_for_selector("div.submit div.d-button-content")
        await submit_button.click()
        await asyncio.sleep(3)  # time.Sleep(3 * time.Second)

    async def _get_content_element_exact(self, page):
        """完全复制Go版本的getContentElement"""
        # 尝试第一种样式 - 完全复制Go版本
        try:
            elem = await page.query_selector("div.ql-editor")
            if elem:
                return elem, True
        except:
            pass

        # 尝试第二种样式 - 完全复制Go版本
        try:
            elem = await self._find_textbox_by_placeholder_exact(page)
            if elem:
                return elem, True
        except:
            pass

        self.logger.warning("没有找到内容输入框")
        return None, False

    async def _find_textbox_by_placeholder_exact(self, page):
        """完全复制Go版本的findTextboxByPlaceholder"""
        elements = await page.query_selector_all("p")
        if not elements:
            raise Exception("no p elements found")

        # 查找包含指定placeholder的元素
        placeholder_elem = await self._find_placeholder_element(elements, "输入正文描述")
        if not placeholder_elem:
            raise Exception("no placeholder element found")

        # 向上查找textbox父元素
        textbox_elem = await self._find_textbox_parent_exact(placeholder_elem)
        if not textbox_elem:
            raise Exception("no textbox parent found")

        return textbox_elem

    async def _find_placeholder_element(self, elements, search_text: str):
        """完全复制Go版本的findPlaceholderElement"""
        for elem in elements:
            placeholder = await elem.get_attribute("data-placeholder")
            if placeholder and search_text in placeholder:
                return elem
        return None

    async def _find_textbox_parent_exact(self, elem):
        """完全复制Go版本的findTextboxParent"""
        current_elem = elem
        for _ in range(5):
            try:
                parent = await current_elem.query_selector("xpath=..")
                if not parent:
                    break

                role = await parent.get_attribute("role")
                if role == "textbox":
                    return parent

                current_elem = parent
            except:
                break

        return None

    async def _input_tags_exact(self, content_elem, tags: List[str]):
        """完全复制Go版本的inputTags"""
        if not tags:
            return

        await asyncio.sleep(1)  # time.Sleep(1 * time.Second)

        # 向下移动光标 - 完全复制Go版本
        for _ in range(20):
            await content_elem.press("ArrowDown")
            await asyncio.sleep(0.01)  # 10ms

        # 换行 - 完全复制Go版本
        await content_elem.press("Enter")
        await content_elem.press("Enter")
        await asyncio.sleep(1)  # time.Sleep(1 * time.Second)

        # 输入标签 - 完全复制Go版本
        for tag in tags:
            tag = tag.lstrip("#")
            await self._input_tag_exact(content_elem, tag)

    async def _input_tag_exact(self, content_elem, tag: str):
        """完全复制Go版本的inputTag"""
        page = content_elem.page

        await content_elem.fill("#")
        await asyncio.sleep(0.2)  # 200ms

        # 输入标签内容 - 完全复制Go版本
        for char in tag:
            await content_elem.fill(char)
            await asyncio.sleep(0.05)  # 50ms

        await asyncio.sleep(1)  # time.Sleep(1 * time.Second)

        # 尝试点击标签联想选项 - 完全复制Go版本
        try:
            topic_container = await page.query_selector("#creator-editor-topic-container")
            if topic_container:
                first_item = await topic_container.query_selector(".item")
                if first_item:
                    await first_item.click()
                    self.logger.info(f"成功点击标签联想选项: {tag}")
                    await asyncio.sleep(0.2)  # 200ms
                else:
                    self.logger.warning(f"未找到标签联想选项，直接输入空格: {tag}")
                    await content_elem.fill(" ")
            else:
                self.logger.warning(f"未找到标签联想下拉框，直接输入空格: {tag}")
                await content_elem.fill(" ")
        except Exception as e:
            self.logger.warning(f"标签输入失败: {e}")
            await content_elem.fill(" ")

        await asyncio.sleep(0.5)  # 500ms

    async def search(
        self,
        instance_id: str,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索内容"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 导航到搜索页面
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)

            # 等待页面稳定和JavaScript加载
            await page.wait_for_timeout(2000)

            # 等待 __INITIAL_STATE__ 加载完成，使用更宽松的条件
            try:
                await page.wait_for_function("() => window.__INITIAL_STATE__ !== undefined", timeout=10000)
            except:
                # 如果等待超时，继续尝试获取数据
                self.logger.warning("等待 __INITIAL_STATE__ 超时，尝试继续执行")

            # 从 JavaScript 中获取 Feed 数据（参考 Go 项目实现）
            feeds_data = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ &&
                    window.__INITIAL_STATE__.search &&
                    window.__INITIAL_STATE__.search.feeds) {
                    const feeds = window.__INITIAL_STATE__.search.feeds;
                    const feedsData = feeds.value !== undefined ? feeds.value : feeds._value;
                    if (feedsData) {
                        return JSON.stringify(feedsData);
                    }
                }
                return "";
            }""")

            if not feeds_data:
                self.logger.warning("无法从 __INITIAL_STATE__ 获取 Feed 数据")
                return []

            # 解析 Feed 数据
            import json
            feeds = json.loads(feeds_data)

            # 格式化结果
            results = []
            for i, feed in enumerate(feeds[:limit]):
                try:
                    note_card = feed.get("noteCard", {})
                    user = note_card.get("user", {})
                    interact_info = note_card.get("interactInfo", {})

                    results.append({
                        "index": i + 1,
                        "feed_id": feed.get("id", ""),
                        "title": note_card.get("displayTitle", ""),
                        "content": "",  # 搜索结果的 Feed 通常没有内容
                        "author": user.get("nickname", user.get("nickName", "")),
                        "likes": interact_info.get("likedCount", "0"),
                        "comments": interact_info.get("commentCount", "0"),
                        "collected": interact_info.get("collected", False),
                        "liked": interact_info.get("liked", False),
                    })
                except Exception as e:
                    self.logger.warning(f"解析搜索结果 {i} 失败: {e}")

            self.logger.info(f"搜索完成: {keyword}, 找到 {len(results)} 个结果")
            return results

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            raise

    async def get_user_profile(
        self,
        instance_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户资料"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            if user_id:
                # 访问指定用户主页
                profile_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
                await page.goto(profile_url, wait_until="networkidle")
            else:
                # 访问当前用户主页
                await page.goto("https://www.xiaohongshu.com/user", wait_until="networkidle")

            # 获取用户信息
            nickname_element = await page.query_selector(".nickname, [data-testid=\"user-nickname\"]")
            bio_element = await page.query_selector(".bio, [data-testid=\"user-bio\"]")
            fans_element = await page.query_selector(".fans-count, [data-testid=\"fans-count\"]")
            following_element = await page.query_selector(".following-count, [data-testid=\"following-count\"]")

            profile = {
                "nickname": await nickname_element.text_content() if nickname_element else None,
                "bio": await bio_element.text_content() if bio_element else None,
                "fans_count": await fans_element.text_content() if fans_element else None,
                "following_count": await following_element.text_content() if following_element else None,
            }

            # 清理数据
            for key, value in profile.items():
                if value:
                    profile[key] = value.strip()

            self.logger.info(f"获取用户资料成功: {profile.get('nickname', 'Unknown')}")
            return profile

        except Exception as e:
            self.logger.error(f"获取用户资料失败: {e}")
            raise

    async def logout(self, instance_id: str) -> bool:
        """退出登录"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            return False

        try:
            # 点击用户头像
            user_avatar = await page.query_selector(".avatar, [data-testid=\"user-avatar\"]")
            if user_avatar:
                await user_avatar.click()
                await page.wait_for_timeout(1000)

                # 点击退出登录
                logout_button = await page.query_selector("text=退出登录, text=Logout")
                if logout_button:
                    await logout_button.click()
                    await page.wait_for_timeout(2000)

                    # 更新账户状态
                    instance = await self.browser_pool.get_instance(instance_id)
                    if instance and instance.account:
                        instance.account.is_logged_in = False
                        instance.account.last_login = None

                    self.logger.info(f"退出登录成功: {instance_id}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"退出登录失败: {e}")
            return False

    async def post_comment(
        self,
        instance_id: str,
        feed_id: str,
        content: str
    ) -> Dict[str, Any]:
        """发表评论到指定笔记"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 构建详情页 URL
            url = f"https://www.xiaohongshu.com/explore/{feed_id}"
            self.logger.info(f"打开笔记详情页: {url}")

            # 导航到详情页，使用更宽松的等待条件
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            # 等待页面稳定
            await page.wait_for_load_state("networkidle")

            # 点击评论输入框
            comment_input = await page.query_selector("div.input-box div.content-edit span")
            if comment_input:
                await comment_input.click()
                await page.wait_for_timeout(1000)

            # 输入评论内容
            content_input = await page.query_selector("div.input-box div.content-edit p.content-input")
            if content_input:
                await content_input.fill(content)
                await page.wait_for_timeout(1000)

            # 点击提交按钮
            submit_button = await page.query_selector("div.bottom button.submit")
            if submit_button:
                await submit_button.click()
                await page.wait_for_timeout(2000)

            self.logger.info(f"评论发表成功: {feed_id}")
            return {"success": True, "feed_id": feed_id, "message": "评论发表成功"}

        except Exception as e:
            self.logger.error(f"发表评论失败: {e}")
            raise

    async def like_feed(
        self,
        instance_id: str,
        feed_id: str,
        unlike: bool = False
    ) -> Dict[str, Any]:
        """点赞/取消点赞指定笔记"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 构建详情页 URL
            url = f"https://www.xiaohongshu.com/explore/{feed_id}"
            self.logger.info(f"打开笔记详情页进行{'取消点赞' if unlike else '点赞'}: {url}")

            # 导航到详情页
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # 获取当前点赞状态
            current_liked = await self._get_interact_state(page, feed_id, "liked")

            # 如果目标状态与当前状态一致，直接返回
            if current_liked == (not unlike):
                action = "取消点赞" if unlike else "点赞"
                self.logger.info(f"笔记 {feed_id} 已经{action}，跳过点击")
                return {"success": True, "feed_id": feed_id, "message": f"已经{action}"}

            # 点击点赞按钮
            like_button = await page.query_selector(".interact-container .left .like-lottie")
            if like_button:
                await like_button.click()
                await page.wait_for_timeout(3000)

            # 验证状态变化
            new_liked = await self._get_interact_state(page, feed_id, "liked")

            if new_liked == (not unlike):
                action = "取消点赞" if unlike else "点赞"
                self.logger.info(f"{action}成功: {feed_id}")
                return {"success": True, "feed_id": feed_id, "message": f"{action}成功"}
            else:
                # 如果状态未变化，尝试再次点击
                retry_action = "取消点赞" if unlike else "点赞"
                self.logger.warning(f"{retry_action}可能未成功，尝试再次点击")
                if like_button:
                    await like_button.click()
                    await page.wait_for_timeout(2000)

                final_liked = await self._get_interact_state(page, feed_id, "liked")
                if final_liked == (not unlike):
                    self.logger.info(f"第二次点击{retry_action}成功: {feed_id}")
                    return {"success": True, "feed_id": feed_id, "message": f"{retry_action}成功"}

            return {"success": True, "feed_id": feed_id, "message": "操作完成"}

        except Exception as e:
            self.logger.error(f"点赞操作失败: {e}")
            raise

    async def favorite_feed(
        self,
        instance_id: str,
        feed_id: str,
        unfavorite: bool = False
    ) -> Dict[str, Any]:
        """收藏/取消收藏指定笔记"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 构建详情页 URL
            url = f"https://www.xiaohongshu.com/explore/{feed_id}"
            self.logger.info(f"打开笔记详情页进行{'取消收藏' if unfavorite else '收藏'}: {url}")

            # 导航到详情页
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # 获取当前收藏状态
            current_collected = await self._get_interact_state(page, feed_id, "collected")

            # 如果目标状态与当前状态一致，直接返回
            if current_collected == (not unfavorite):
                action = "取消收藏" if unfavorite else "收藏"
                self.logger.info(f"笔记 {feed_id} 已经{action}，跳过点击")
                return {"success": True, "feed_id": feed_id, "message": f"已经{action}"}

            # 点击收藏按钮
            favorite_button = await page.query_selector(".interact-container .left .reds-icon.collect-icon")
            if favorite_button:
                await favorite_button.click()
                await page.wait_for_timeout(3000)

            # 验证状态变化
            new_collected = await self._get_interact_state(page, feed_id, "collected")

            if new_collected == (not unfavorite):
                action = "取消收藏" if unfavorite else "收藏"
                self.logger.info(f"{action}成功: {feed_id}")
                return {"success": True, "feed_id": feed_id, "message": f"{action}成功"}
            else:
                # 如果状态未变化，尝试再次点击
                retry_action = "取消收藏" if unfavorite else "收藏"
                self.logger.warning(f"{retry_action}可能未成功，尝试再次点击")
                if favorite_button:
                    await favorite_button.click()
                    await page.wait_for_timeout(2000)

                final_collected = await self._get_interact_state(page, feed_id, "collected")
                if final_collected == (not unfavorite):
                    self.logger.info(f"第二次点击{retry_action}成功: {feed_id}")
                    return {"success": True, "feed_id": feed_id, "message": f"{retry_action}成功"}

            return {"success": True, "feed_id": feed_id, "message": "操作完成"}

        except Exception as e:
            self.logger.error(f"收藏操作失败: {e}")
            raise

    async def _get_interact_state(
        self,
        page: Page,
        feed_id: str,
        state_type: str
    ) -> bool:
        """获取笔记的交互状态（点赞/收藏）"""
        try:
            # 执行 JavaScript 获取笔记详情
            result = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ &&
                    window.__INITIAL_STATE__.note &&
                    window.__INITIAL_STATE__.note.noteDetailMap) {
                    return JSON.stringify(window.__INITIAL_STATE__.note.noteDetailMap);
                }
                return "";
            }""")

            if not result:
                self.logger.warning("无法获取笔记详情")
                return False

            # 解析笔记详情
            note_detail_map = json.loads(result)

            if feed_id not in note_detail_map:
                self.logger.warning(f"笔记 {feed_id} 不在详情映射中")
                return False

            note_detail = note_detail_map[feed_id]
            interact_info = note_detail.get("note", {}).get("interactInfo", {})

            if state_type == "liked":
                return interact_info.get("liked", False)
            elif state_type == "collected":
                return interact_info.get("collected", False)
            else:
                return False

        except Exception as e:
            self.logger.warning(f"获取交互状态失败: {e}")
            return False

    async def list_feeds(
        self,
        instance_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取 Feed 列表"""
        page = await self.browser_pool.get_page(instance_id)
        if not page:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        try:
            # 导航到首页
            await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            # 执行 JavaScript 获取 Feed 数据
            feeds_data = await page.evaluate("""() => {
                if (window.__INITIAL_STATE__ &&
                    window.__INITIAL_STATE__.home &&
                    window.__INITIAL_STATE__.home.feedList) {
                    return JSON.stringify(window.__INITIAL_STATE__.home.feedList);
                }
                return "";
            }""")

            if not feeds_data:
                self.logger.warning("无法获取 Feed 列表")
                return []

            # 解析 Feed 数据
            feed_list = json.loads(feeds_data)

            # 格式化结果
            feeds = []
            for i, feed in enumerate(feed_list[:limit]):
                try:
                    feed_info = {
                        "index": i + 1,
                        "feed_id": feed.get("id", ""),
                        "title": feed.get("title", ""),
                        "content": feed.get("desc", ""),
                        "author": feed.get("user", {}).get("nickname", ""),
                        "likes": feed.get("likes", 0),
                        "comments": feed.get("comments", 0),
                        "collected": feed.get("collected", False),
                        "liked": feed.get("liked", False),
                    }
                    feeds.append(feed_info)
                except Exception as e:
                    self.logger.warning(f"解析 Feed {i} 失败: {e}")

            self.logger.info(f"获取到 {len(feeds)} 个 Feed")
            return feeds

        except Exception as e:
            self.logger.error(f"获取 Feed 列表失败: {e}")
            raise