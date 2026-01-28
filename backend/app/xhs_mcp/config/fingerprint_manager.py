"""
指纹配置管理器

管理浏览器指纹配置，支持预定义指纹和自定义指纹。
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from app.xhs_mcp.core.models import BrowserFingerprint, BrowserProfile
from app.core.config import APP_DATA_DIR


class FingerprintManager:
    """指纹配置管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = APP_DATA_DIR / "xhs_mcp" / "fingerprints"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self.predefined_fingerprints: Dict[str, BrowserFingerprint] = {}

        self._load_predefined_fingerprints()

    def _load_predefined_fingerprints(self):
        """加载预定义指纹配置"""
        # Windows Chrome 指纹
        self.predefined_fingerprints["windows_chrome"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            language="zh-CN",
            timezone="Asia/Shanghai",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8,
            webgl_vendor="Google Inc.",
            webgl_renderer="ANGLE (Intel, Intel(R) UHD Graphics 630 (0x000059A2) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        )

        # macOS Chrome 指纹
        self.predefined_fingerprints["macos_chrome"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            language="zh-CN",
            timezone="Asia/Shanghai",
            platform="MacIntel",
            hardware_concurrency=8,
            device_memory=8,
            webgl_vendor="Apple Inc.",
            webgl_renderer="Apple GPU",
        )

        # Windows Edge 指纹
        self.predefined_fingerprints["windows_edge"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            viewport={"width": 1920, "height": 1080},
            language="zh-CN",
            timezone="Asia/Shanghai",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8,
            webgl_vendor="Google Inc.",
            webgl_renderer="ANGLE (Intel, Intel(R) UHD Graphics 630 (0x000059A2) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        )

        # macOS Safari 指纹
        self.predefined_fingerprints["macos_safari"] = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            viewport={"width": 1440, "height": 900},
            language="zh-CN",
            timezone="Asia/Shanghai",
            platform="MacIntel",
            hardware_concurrency=8,
            device_memory=8,
            webgl_vendor="Apple Inc.",
            webgl_renderer="Apple GPU",
        )

        self.logger.info(f"加载了 {len(self.predefined_fingerprints)} 个预定义指纹配置")

    def get_predefined_fingerprint(self, name: str) -> Optional[BrowserFingerprint]:
        """获取预定义指纹配置"""
        return self.predefined_fingerprints.get(name)

    def list_predefined_fingerprints(self) -> List[str]:
        """列出所有预定义指纹名称"""
        return list(self.predefined_fingerprints.keys())

    def create_custom_fingerprint(
        self,
        name: str,
        user_agent: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        language: str = "zh-CN",
        timezone: str = "Asia/Shanghai",
        platform: str = "Win32",
        hardware_concurrency: int = 8,
        device_memory: int = 8,
        webgl_vendor: str = "Google Inc.",
        webgl_renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics 630 (0x000059A2) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ) -> BrowserFingerprint:
        """创建自定义指纹配置"""
        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            viewport={"width": viewport_width, "height": viewport_height},
            language=language,
            timezone=timezone,
            platform=platform,
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
        )

        # 保存到文件
        self._save_fingerprint(name, fingerprint)
        return fingerprint

    def _save_fingerprint(self, name: str, fingerprint: BrowserFingerprint):
        """保存指纹配置到文件"""
        file_path = self.config_dir / f"{name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(fingerprint.model_dump(), f, indent=2, ensure_ascii=False)

        self.logger.info(f"保存指纹配置: {name}")

    def load_fingerprint(self, name: str) -> Optional[BrowserFingerprint]:
        """从文件加载指纹配置"""
        file_path = self.config_dir / f"{name}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return BrowserFingerprint(**data)
        except Exception as e:
            self.logger.error(f"加载指纹配置失败 {name}: {e}")
            return None

    def delete_fingerprint(self, name: str) -> bool:
        """删除指纹配置"""
        file_path = self.config_dir / f"{name}.json"
        if file_path.exists():
            file_path.unlink()
            self.logger.info(f"删除指纹配置: {name}")
            return True
        return False

    def list_custom_fingerprints(self) -> List[str]:
        """列出所有自定义指纹配置"""
        custom_fingerprints = []
        for file_path in self.config_dir.glob("*.json"):
            if file_path.stem not in self.predefined_fingerprints:
                custom_fingerprints.append(file_path.stem)
        return custom_fingerprints

    def create_browser_profile(
        self,
        name: str,
        fingerprint_name: str,
        headless: bool = False,
        slow_mo: int = 100,
        user_data_dir: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
    ) -> BrowserProfile:
        """创建浏览器配置文件"""
        # 获取指纹配置
        fingerprint = self.get_predefined_fingerprint(fingerprint_name)
        if not fingerprint:
            fingerprint = self.load_fingerprint(fingerprint_name)

        if not fingerprint:
            raise ValueError(f"指纹配置不存在: {fingerprint_name}")

        profile = BrowserProfile(
            name=name,
            fingerprint=fingerprint,
            headless=headless,
            slow_mo=slow_mo,
            user_data_dir=user_data_dir,
            proxy=proxy,
        )

        return profile

    def get_all_fingerprints(self) -> Dict[str, BrowserFingerprint]:
        """获取所有指纹配置（预定义 + 自定义）"""
        all_fingerprints = self.predefined_fingerprints.copy()

        # 加载自定义指纹
        for name in self.list_custom_fingerprints():
            fingerprint = self.load_fingerprint(name)
            if fingerprint:
                all_fingerprints[name] = fingerprint

        return all_fingerprints