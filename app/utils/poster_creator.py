import asyncio
import os
import random

from jinja2 import Template
from multipart import file_path
from playwright.async_api import async_playwright
from app.data.poster_card_style import TEMPLATES
from app.core.logger import logger

class PosterGenerator:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def render_html(self, template_key, data):
        if template_key not in TEMPLATES:
            raise ValueError(f"模版 '{template_key}' 不存在。")

        template_str = TEMPLATES[template_key]
        template = Template(template_str)
        return template.render(**data)

    async def generate_image(self, template_key, data, filename):
        html_content = self.render_html(template_key, data)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # device_scale_factor=2 保证 Retina 级清晰度
            page = await browser.new_page(device_scale_factor=2)

            await page.set_content(html_content)

            # 定位到 #poster 元素截图
            poster_element = page.locator("#poster")
            await poster_element.wait_for()

            output_path = os.path.join(self.output_dir, filename)
            await poster_element.screenshot(path=output_path)

            print(f"✅ 生成成功: {output_path} [{template_key}]")
            await browser.close()


# ==========================================
# 3. 使用示例 (更新了数据结构)
# ==========================================
async def create_poster(data, task_id, output_dir="output"):
    generator = PosterGenerator(output_dir)
    tmp_key = random.choice(list(TEMPLATES.keys()))
    file_name = f"{task_id}_{tmp_key}.png"
    await generator.generate_image(tmp_key, data, file_name)
    logger.info(f"[{task_id}]-使用{tmp_key}模版生成了{file_name}")
    file_path = os.path.join(output_dir, file_name)
    return file_path



