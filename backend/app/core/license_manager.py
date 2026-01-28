"""
注册码管理器

负责：
- 调用注册机服务验证注册码
- 加密存储/读取激活配置
- 对外提供统一的激活状态与限制查询接口
"""

from __future__ import annotations

import json
import os  # Added import
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.core.logger import logger
from app.utils.encryption import encrypt_dict, decrypt_dict


LICENSE_CONFIG_FILENAME = "license_config.encrypted"
LICENSE_VERIFY_URL = "http://175.24.40.127/api/licenses/verify"
LICENSE_PRODUCT_ID = 1


@dataclass
class LicenseConfig:
    product_id: int
    license_code: str
    activated_at: str
    config: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LicenseConfig":
        return cls(
            product_id=data.get("product_id", LICENSE_PRODUCT_ID),
            license_code=data.get("license_code", ""),
            activated_at=data.get("activated_at", ""),
            config=data.get("config") or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "license_code": self.license_code,
            "activated_at": self.activated_at,
            "config": self.config,
        }


class LicenseManager:
    """注册码管理器"""

    def __init__(self, config_file_path: Optional[str] = None):
        # 配置文件路径
        if config_file_path:
            self._config_path = Path(config_file_path)
            logger.debug(f"Using provided config path: {self._config_path}")
        else:
            # 优先使用 APP_DATA_DIR 环境变量（由启动脚本设置）
            app_data_dir = os.getenv("APP_DATA_DIR")
            if app_data_dir:
                self._config_path = Path(app_data_dir) / LICENSE_CONFIG_FILENAME
                logger.debug(f"Using APP_DATA_DIR ({app_data_dir}) for license config: {self._config_path}")
            else:
                # 回退到项目根目录（开发环境）
                project_root = Path(__file__).resolve().parent.parent.parent
                self._config_path = project_root / LICENSE_CONFIG_FILENAME
                logger.warning(f"APP_DATA_DIR not set. Using project root: {self._config_path}")
            
        logger.info(f"License config path resolved to: {self._config_path.absolute()}")

        self._license: Optional[LicenseConfig] = None
        self._load_config_safely()

    # ---------------- 远程验证与激活 ----------------

    async def verify_license(self, license_code: str) -> Dict[str, Any]:
        """验证注册码并获取配置（调用注册机服务）"""
        payload = {"product_id": LICENSE_PRODUCT_ID, "license_code": license_code}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(LICENSE_VERIFY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.RequestError as e:
            logger.error(f"验证注册码网络错误: {e}")
            raise RuntimeError("无法连接到注册机服务，请检查网络连接") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"验证注册码失败，HTTP状态码: {e.response.status_code}, body={e.response.text}")
            raise RuntimeError("注册码验证服务返回错误响应") from e
        except json.JSONDecodeError as e:
            logger.error(f"注册机返回数据解析失败: {e}")
            raise RuntimeError("注册码验证服务返回了无效数据") from e

        if not data.get("success"):
            # 注册机返回业务失败
            msg = data.get("error") or "注册码无效或已过期"
            raise ValueError(msg)

        if "config" not in data or not isinstance(data["config"], dict):
            raise RuntimeError("注册码验证成功，但未返回有效的配置数据")

        return data

    async def activate(self, license_code: str) -> Dict[str, Any]:
        """激活注册码并保存配置"""
        data = await self.verify_license(license_code)
        config = data["config"]

        activated_at = datetime.now(timezone.utc).isoformat()
        license_obj = LicenseConfig(
            product_id=LICENSE_PRODUCT_ID,
            license_code=license_code,
            activated_at=activated_at,
            config=config,
        )

        if not self.save_config(license_obj):
            raise RuntimeError("激活成功但保存配置失败，请检查服务器文件权限")

        self._license = license_obj
        logger.info("✅ 注册码激活成功并已保存配置")
        return {
            "success": True,
            "config": config,
        }

    # ---------------- 本地配置读写 ----------------

    def _load_config_safely(self) -> None:
        try:
            self._license = self.load_config()
        except Exception as e:
            logger.error(f"加载注册码配置失败，将视为未激活: {e}", exc_info=True)
            self._license = None

    def load_config(self) -> Optional[LicenseConfig]:
        """从加密文件加载配置"""
        logger.debug(f"Attempting to load license config from: {self._config_path}")
        if not self._config_path.exists():
            logger.warning(f"License config file does not exist at: {self._config_path}")
            return None

        try:
            token = self._config_path.read_bytes()
            logger.debug(f"Read {len(token)} bytes from license config file")
            data = decrypt_dict(token)
            logger.debug("License config decrypted successfully")
            return LicenseConfig.from_dict(data)
        except Exception as e:
            logger.error(f"解密注册码配置失败: {e}", exc_info=True)
            return None

    def save_config(self, license_obj: LicenseConfig) -> bool:
        """加密保存配置到文件"""
        try:
            logger.debug(f"Saving license config to: {self._config_path}")
            # Ensure parent directory exists
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            
            token = encrypt_dict(license_obj.to_dict())
            self._config_path.write_bytes(token)
            try:
                self._config_path.chmod(0o600)
            except Exception:
                # 某些系统不支持 chmod，忽略
                pass
            
            logger.info(f"✅ License config saved. Exists: {self._config_path.exists()}, Size: {self._config_path.stat().st_size}")
            return True
        except Exception as e:
            logger.error(f"保存注册码配置失败: {e}", exc_info=True)
            return False

    # ---------------- 状态与限制查询 ----------------

    def get_config(self) -> Optional[Dict[str, Any]]:
        """获取当前配置（仅返回注册机返回的 config 字段）"""
        if not self._license:
            return None
        return self._license.config

    def is_activated(self) -> bool:
        """检查是否已激活"""
        return self._license is not None

    def is_expired(self) -> bool:
        """检查是否已过期（仅对已激活用户生效）"""
        config = self.get_config()
        if not config:
            return False

        end_time_str = config.get("end_time")
        if not end_time_str:
            return False

        try:
            # 允许无时区信息，按本地/UTC 时间解析
            if end_time_str.endswith("Z"):
                dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(end_time_str)
        except Exception:
            logger.warning(f"无法解析注册码过期时间: {end_time_str}")
            return False

        # 统一使用有时区的时间进行比较，避免 naive/aware 混用报错
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return now > dt

    def get_max_tasks(self) -> int:
        """
        获取最大任务数量

        - 未激活或已过期：1（免费试用）
        - 已激活且未过期：使用配置中的 task_num，缺省为 0
        """
        # 未激活或已过期，统一视为免费试用模式
        if not self.is_activated() or self.is_expired():
            return 1

        config = self.get_config() or {}
        return int(config.get("task_num") or 0)

    def get_interval_limit(self) -> Optional[int]:
        """
        获取执行间隔限制

        - 未激活或已过期：返回 7200（2 小时）
        - 已激活且未过期：返回 None（由业务逻辑自行校验）
        """
        if not self.is_activated() or self.is_expired():
            return 7200
        return None

    def can_execute_immediately(self) -> bool:
        """
        检查是否可以立即执行任务

        - 未激活：False
        - 已激活但过期：False
        - 已激活且未过期：True
        """
        if not self.is_activated():
            return False
        if self.is_expired():
            return False
        return True


# ---------------- 全局单例访问 ----------------

_LICENSE_MANAGER: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """获取全局 LicenseManager 单例"""
    global _LICENSE_MANAGER
    if _LICENSE_MANAGER is None:
        _LICENSE_MANAGER = LicenseManager()
    return _LICENSE_MANAGER

