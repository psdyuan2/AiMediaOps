"""
路径工具模块

提供用户任务数据目录的创建、管理和路径构建功能。
"""

import os
import shutil
from typing import Optional

# 从 constants 导入常量
from app.data.constants import (
    TASK_DATA_BASE_PATH,
    USER_COOKIES_DIR,
    USER_IMAGES_DIR,
    USER_NOTES_DIR,
    USER_SOURCES_DIR,
    DEFAULT_KNOWLEDGE_PATH,
    DEFAULT_NOTES_PATH
)


def build_user_path(user_id: str, *path_parts: str) -> str:
    """
    构建用户路径的通用函数

    Args:
        user_id: 用户ID
        *path_parts: 路径部分，可以是一个或多个

    Returns:
        完整的用户路径

    Examples:
        >>> build_user_path('123456', USER_SOURCES_DIR, 'text.md')
        './app/data/task_data/123456/sources/text.md'

        >>> build_user_path('123456', USER_IMAGES_DIR)
        './app/data/task_data/123456/images/'
    """
    # 构建基础用户路径
    user_base_path = os.path.join(TASK_DATA_BASE_PATH, user_id)

    # 如果有额外的路径部分，拼接上
    if path_parts:
        return os.path.join(user_base_path, *path_parts)
    return user_base_path


def get_user_task_data_path(user_id: str) -> str:
    """
    获取用户任务数据根目录路径

    Args:
        user_id: 用户ID

    Returns:
        用户任务数据根目录路径
    """
    return build_user_path(user_id)


def get_user_cookies_path(user_id: str) -> str:
    """
    获取用户cookies目录路径

    Args:
        user_id: 用户ID

    Returns:
        用户cookies目录路径
    """
    return build_user_path(user_id, USER_COOKIES_DIR)


def get_user_images_path(user_id: str) -> str:
    """
    获取用户images目录路径

    Args:
        user_id: 用户ID

    Returns:
        用户images目录路径
    """
    return build_user_path(user_id, USER_IMAGES_DIR)


def get_user_notes_path(user_id: str) -> str:
    """
    获取用户notes目录路径

    Args:
        user_id: 用户ID

    Returns:
        用户notes目录路径
    """
    return build_user_path(user_id, USER_NOTES_DIR)


def get_user_sources_path(user_id: str) -> str:
    """
    获取用户sources目录路径

    Args:
        user_id: 用户ID

    Returns:
        用户sources目录路径
    """
    return build_user_path(user_id, USER_SOURCES_DIR)


def get_user_source_file_path(user_id: str, filename: str = 'text.md') -> str:
    """
    获取用户源文件路径

    Args:
        user_id: 用户ID
        filename: 文件名，默认为'text.md'

    Returns:
        用户源文件完整路径
    """
    # 新结构路径
    new_path = build_user_path(user_id, USER_SOURCES_DIR, filename)

    # 旧结构路径（向后兼容）
    old_path = os.path.join(DEFAULT_KNOWLEDGE_PATH, user_id, filename)

    # 如果新路径不存在但旧路径存在，进行自动迁移
    if not os.path.exists(new_path) and os.path.exists(old_path):
        # 确保目标目录存在
        os.makedirs(os.path.dirname(new_path), exist_ok=True)

        # 复制文件
        try:
            shutil.copy2(old_path, new_path)
            print(f"📦 自动迁移源文件: {old_path} -> {new_path}")
        except Exception as e:
            print(f"❌ 自动迁移源文件失败: {e}")
            # 迁移失败，回退到旧路径
            return old_path

    return new_path


def get_user_notes_file_path(user_id: str, filename: Optional[str] = None) -> str:
    """
    获取用户笔记文件路径

    Args:
        user_id: 用户ID
        filename: 文件名，如果为None则使用 f"{user_id}.jsonl"

    Returns:
        用户笔记文件完整路径
    """
    if filename is None:
        filename = f"{user_id}.jsonl"

    # 新结构路径
    new_path = build_user_path(user_id, USER_NOTES_DIR, filename)

    # 旧结构路径（向后兼容）
    old_path = os.path.join(DEFAULT_NOTES_PATH, filename)

    # 如果新路径不存在但旧路径存在，进行自动迁移
    if not os.path.exists(new_path) and os.path.exists(old_path):
        # 确保目标目录存在
        os.makedirs(os.path.dirname(new_path), exist_ok=True)

        # 复制文件
        try:
            shutil.copy2(old_path, new_path)
            print(f"📄 自动迁移笔记文件: {old_path} -> {new_path}")
        except Exception as e:
            print(f"❌ 自动迁移笔记文件失败: {e}")
            # 迁移失败，回退到旧路径
            return old_path

    return new_path


def init_user_task_dirs(user_id: str) -> bool:
    """
    初始化用户任务目录结构

    创建以下目录结构：
    app/data/task_data/{user_id}/
    ├── cookies/
    ├── images/
    ├── notes/
    └── sources/

    Args:
        user_id: 用户ID

    Returns:
        如果所有目录创建成功返回True，否则返回False
    """
    try:
        # 需要创建的目录列表
        dirs_to_create = [
            get_user_cookies_path(user_id),
            get_user_images_path(user_id),
            get_user_notes_path(user_id),
            get_user_sources_path(user_id)
        ]

        # 创建所有目录
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)

        print(f"✅ 用户 {user_id} 任务目录初始化完成")
        return True

    except Exception as e:
        print(f"❌ 初始化用户 {user_id} 任务目录失败: {e}")
        return False


def ensure_user_task_dirs(user_id: str) -> bool:
    """
    确保用户任务目录存在，如果不存在则创建

    Args:
        user_id: 用户ID

    Returns:
        如果目录存在或创建成功返回True，否则返回False
    """
    user_base_path = get_user_task_data_path(user_id)

    # 检查目录是否存在
    if os.path.exists(user_base_path):
        # 检查子目录是否都存在
        required_dirs = [
            USER_COOKIES_DIR,
            USER_IMAGES_DIR,
            USER_NOTES_DIR,
            USER_SOURCES_DIR
        ]

        # 验证所有子目录都存在
        for dir_name in required_dirs:
            dir_path = os.path.join(user_base_path, dir_name)
            if not os.path.exists(dir_path):
                # 如果某个子目录不存在，重新初始化
                return init_user_task_dirs(user_id)

        return True
    else:
        # 目录不存在，初始化
        return init_user_task_dirs(user_id)


# 向后兼容的函数（可选，用于迁移旧数据）
def migrate_old_structure(user_id: str) -> bool:
    """
    迁移旧目录结构到新结构（可选）

    将旧的平铺结构迁移到用户隔离结构

    Args:
        user_id: 用户ID

    Returns:
        迁移成功返回True，否则返回False
    """
    try:
        # 确保新目录结构存在
        if not ensure_user_task_dirs(user_id):
            return False

        # 迁移 sources（如果旧目录存在且新目录为空）
        old_sources_dir = os.path.join(DEFAULT_KNOWLEDGE_PATH, user_id)
        new_sources_dir = get_user_sources_path(user_id)

        if os.path.exists(old_sources_dir):
            # 检查新目录是否为空
            if not os.path.exists(new_sources_dir) or not os.listdir(new_sources_dir):
                print(f"📦 迁移 sources 数据: {old_sources_dir} -> {new_sources_dir}")
                # 这里可以添加具体的文件复制逻辑

        # 迁移 notes
        old_notes_file = os.path.join(DEFAULT_NOTES_PATH, f"{user_id}.jsonl")
        new_notes_file = get_user_notes_file_path(user_id)

        if os.path.exists(old_notes_file) and not os.path.exists(new_notes_file):
            print(f"📄 迁移 notes 数据: {old_notes_file} -> {new_notes_file}")
            # 这里可以添加具体的文件复制逻辑

        return True

    except Exception as e:
        print(f"❌ 迁移用户 {user_id} 数据失败: {e}")
        return False