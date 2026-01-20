"""
帮助文档路由
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pathlib import Path
import os
from app.core.logger import logger

router = APIRouter()


@router.get("/help/guide", response_class=PlainTextResponse, tags=["帮助文档"])
async def get_help_guide():
    """
    获取帮助文档内容
    
    Returns:
        str: Markdown 格式的帮助文档内容
    """
    try:
        # 获取帮助文档文件路径
        # 优先从 docs 目录读取，如果不存在则从 frontend/public 读取
        docs_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "help_guide.md"
        public_path = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "public" / "help_guide.md"
        
        # 优先使用 docs 目录的文件（便于后端编辑）
        if docs_path.exists():
            help_file = docs_path
        elif public_path.exists():
            help_file = public_path
        else:
            # 如果都不存在，返回默认内容
            logger.warning("帮助文档文件不存在，返回默认内容")
            return "# AIMediaOps 使用指南\n\n帮助文档文件未找到，请检查文件路径。\n\n帮助文档应位于 `docs/help_guide.md` 或 `frontend/public/help_guide.md`。"
        
        # 读取文件内容
        with open(help_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
    except Exception as e:
        logger.error(f"读取帮助文档失败: {e}", exc_info=True)
        return f"# AIMediaOps 使用指南\n\n读取帮助文档失败：{str(e)}\n\n请检查帮助文档文件是否存在：`docs/help_guide.md`。"
