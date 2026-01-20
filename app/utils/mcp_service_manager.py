"""
MCP 服务管理器

负责检查和管理 xiaohongshu-mcp 服务的运行状态
"""

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional
import socket
import requests
from app.core.logger import logger
from app.data.constants import SYS_TYPE
from app.data.config import XHS_MCP_SERVICE_URL


class MCPServiceManager:
    """MCP 服务管理器"""
    
    def __init__(self, mcp_service_url: str = XHS_MCP_SERVICE_URL):
        """
        初始化 MCP 服务管理器
        
        Args:
            mcp_service_url: MCP 服务 URL，默认为 http://localhost:18060/mcp
        """
        self.mcp_service_url = mcp_service_url
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.xhs_mcp_dir = self.project_root / "xhs_mcp"
        
    def _get_mcp_binary_name(self, sys_type: str) -> Optional[str]:
        """
        根据系统类型获取对应的 MCP 二进制文件名
        
        Args:
            sys_type: 系统类型 (SYS_TYPE 枚举值)
            
        Returns:
            二进制文件名，如果不支持则返回 None
        """
        system = platform.system()
        machine = platform.machine()
        
        # 根据系统类型和架构确定二进制文件名
        if system == "Darwin":  # macOS
            if sys_type == SYS_TYPE.MAC_SILICON.value:
                return "xiaohongshu-mcp-darwin-arm64"
            elif sys_type == SYS_TYPE.MAC_INTEL.value:
                return "xiaohongshu-mcp-darwin-amd64"
            else:
                # 自动检测架构
                if machine == "arm64":
                    return "xiaohongshu-mcp-darwin-arm64"
                elif machine in ("x86_64", "amd64"):
                    return "xiaohongshu-mcp-darwin-amd64"
        elif system == "Linux":
            return "xiaohongshu-mcp-linux-amd64"
        elif system == "Windows":
            return "xiaohongshu-mcp-windows-amd64.exe"
        
        return None
    
    def _get_mcp_binary_path(self, sys_type: str) -> Optional[Path]:
        """
        获取 MCP 二进制文件的完整路径
        
        Args:
            sys_type: 系统类型
            
        Returns:
            二进制文件路径，如果不存在则返回 None
        """
        binary_name = self._get_mcp_binary_name(sys_type)
        if not binary_name:
            logger.warning(f"不支持的系统类型: {sys_type}")
            return None
        
        binary_path = self.xhs_mcp_dir / binary_name
        
        if binary_path.exists() and binary_path.is_file():
            return binary_path
        
        logger.warning(f"MCP 二进制文件不存在: {binary_path}")
        return None
    
    def is_service_running(self) -> bool:
        """
        检查 MCP 服务是否正在运行
        
        Returns:
            True 如果服务正在运行，False 否则
        """
        try:
            # 方法1: 检查端口是否被监听
            host = "localhost"
            port = 18060
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                # 端口被占用，进一步检查是否是 MCP 服务
                try:
                    response = requests.post(
                        self.mcp_service_url,
                        json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
                        timeout=2
                    )
                    if response.status_code == 200:
                        logger.debug("MCP 服务正在运行")
                        return True
                except requests.RequestException:
                    pass
            
            return False
        except Exception as e:
            logger.debug(f"检查 MCP 服务状态时出错: {e}")
            return False
    
    def start_service(self, sys_type: str, headless: bool = True) -> bool:
        """
        启动 MCP 服务
        
        Args:
            sys_type: 系统类型
            headless: 是否无头模式运行，默认为 True
            
        Returns:
            True 如果启动成功，False 否则
        """
        binary_path = self._get_mcp_binary_path(sys_type)
        if not binary_path:
            logger.error(f"无法找到 MCP 二进制文件，系统类型: {sys_type}")
            return False
        
        # 确保二进制文件有执行权限
        os.chmod(binary_path, 0o755)
        
        # 构建启动命令
        cmd = [str(binary_path)]
        if not headless:
            cmd.append("-headless=false")
        
        try:
            # 检查是否已经在运行
            if self.is_service_running():
                logger.info("MCP 服务已经在运行")
                return True
            
            # 启动服务（后台运行）
            # 使用 nohup 或 subprocess 在后台启动
            # 注意：需要切换到 xhs_mcp 目录，因为服务需要在该目录下运行（cookies.json 等文件）
            working_dir = self.xhs_mcp_dir
            
            logger.info(f"正在启动 MCP 服务: {binary_path}")
            logger.info(f"工作目录: {working_dir}")
            
            # 使用 subprocess.Popen 在后台启动
            process = subprocess.Popen(
                cmd,
                cwd=str(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # 创建新的会话，使进程独立
            )
            
            # 等待几秒，检查服务是否启动成功
            time.sleep(3)
            
            if self.is_service_running():
                logger.info(f"MCP 服务启动成功 (PID: {process.pid})")
                return True
            else:
                # 检查进程是否还在运行
                if process.poll() is None:
                    logger.warning("MCP 服务进程已启动，但服务尚未就绪，请稍后重试")
                else:
                    # 进程已退出，读取错误信息
                    _, stderr = process.communicate()
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "未知错误"
                    logger.error(f"MCP 服务启动失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"启动 MCP 服务时出错: {e}", exc_info=True)
            return False
    
    def ensure_service_running(self, sys_type: str, headless: bool = True) -> bool:
        """
        确保 MCP 服务正在运行，如果没有运行则启动
        
        Args:
            sys_type: 系统类型
            headless: 是否无头模式运行
            
        Returns:
            True 如果服务正在运行，False 否则
        """
        if self.is_service_running():
            logger.debug("MCP 服务已经在运行")
            return True
        
        logger.info("MCP 服务未运行，正在启动...")
        return self.start_service(sys_type, headless)
