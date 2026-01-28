"""
帮助文档路由
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, FileResponse
from pathlib import Path
import os
import sys
from app.core.logger import logger

router = APIRouter()


@router.get("/help/images/{filename}", tags=["帮助文档"])
async def get_help_image(filename: str):
    """
    获取帮助文档中的图片
    
    Args:
        filename: 图片文件名（如 register1.png）
    
    Returns:
        FileResponse: 图片文件
    """
    try:
        # 获取图片文件路径
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller 环境 - 图片应该在 docs 目录或 frontend/public 目录
            # 先尝试从 docs 目录查找（打包时可能复制到这里）
            image_path = Path(sys._MEIPASS) / "docs" / filename
            if not image_path.exists():
                # 尝试从 frontend/public 目录查找
                image_path = Path(sys._MEIPASS) / "frontend" / "public" / filename
        else:
            # 开发环境
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            # 优先从 frontend/public 目录查找
            image_path = project_root / "frontend" / "public" / filename
            if not image_path.exists():
                # 尝试从 docs 目录查找
                image_path = project_root / "docs" / filename
        
        if not image_path.exists():
            logger.warning(f"帮助文档图片不存在: {filename}")
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"图片文件不存在: {filename}")
        
        # 根据文件扩展名确定媒体类型
        ext = image_path.suffix.lower()
        media_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
        }
        media_type = media_types.get(ext, 'application/octet-stream')
        
        return FileResponse(
            path=str(image_path),
            media_type=media_type,
            filename=filename
        )
    except Exception as e:
        logger.error(f"读取帮助文档图片失败: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"读取图片失败: {str(e)}")


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
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
             # PyInstaller 环境
             docs_path = Path(sys._MEIPASS) / "docs" / "help_guide.md"
        else:
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


@router.get("/help/license-purchase", response_class=PlainTextResponse, tags=["帮助文档"])
async def get_license_purchase_guide():
    """
    获取激活码购买说明文档
    """
    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
             # PyInstaller 环境
             project_root = Path(sys._MEIPASS)
        else:
             project_root = Path(__file__).resolve().parent.parent.parent.parent
             
        docs_path = project_root / "docs" / "license_purchase.md"
        public_path = project_root / "frontend" / "public" / "license_purchase.md"

        if docs_path.exists():
            doc_file = docs_path
        elif public_path.exists():
            doc_file = public_path
        else:
            logger.warning("激活码购买文档不存在，返回默认内容")
            return "# 激活码购买说明\n\n激活码购买文档未找到，请在 `docs/license_purchase.md` 或 `frontend/public/license_purchase.md` 中添加内容。"

        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read()

        return content
    except Exception as e:
        logger.error(f"读取激活码购买文档失败: {e}", exc_info=True)
        return f"# 激活码购买说明\n\n读取文档失败：{str(e)}\n\n请检查 `docs/license_purchase.md` 文件是否存在。"
