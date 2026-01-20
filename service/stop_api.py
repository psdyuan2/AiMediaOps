#!/usr/bin/env python3
"""
停止后端API服务脚本

功能：
1. 查找并停止所有运行中的 uvicorn 进程
2. 查找并停止所有运行中的 start_api.py 进程
3. 释放端口 8000
4. 提供详细的停止日志
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

def find_processes_by_name(name_patterns):
    """
    根据进程名模式查找进程
    
    Args:
        name_patterns: 进程名模式列表，如 ['uvicorn', 'start_api']
    
    Returns:
        list: 进程ID列表
    """
    pids = []
    try:
        # 使用 ps 命令查找进程
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.split('\n'):
            for pattern in name_patterns:
                if pattern in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            if pid not in pids:
                                pids.append(pid)
                        except (ValueError, IndexError):
                            continue
    except Exception as e:
        print(f"⚠️  查找进程时出错: {e}")
    
    return pids

def find_processes_by_port(port):
    """
    根据端口查找进程
    
    Args:
        port: 端口号
    
    Returns:
        list: 进程ID列表
    """
    pids = []
    try:
        # 使用 lsof 命令查找占用端口的进程
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            for pid_str in result.stdout.strip().split('\n'):
                try:
                    pid = int(pid_str)
                    if pid not in pids:
                        pids.append(pid)
                except ValueError:
                    continue
    except Exception as e:
        print(f"⚠️  查找端口占用时出错: {e}")
    
    return pids

def stop_process(pid, force=False):
    """
    停止指定进程
    
    Args:
        pid: 进程ID
        force: 是否强制停止（使用 SIGKILL）
    
    Returns:
        bool: 是否成功停止
    """
    try:
        if force:
            os.kill(pid, signal.SIGKILL)
            print(f"  ✅ 强制停止进程 {pid}")
        else:
            os.kill(pid, signal.SIGTERM)
            print(f"  ✅ 发送停止信号到进程 {pid}")
        return True
    except ProcessLookupError:
        print(f"  ⚠️  进程 {pid} 不存在")
        return False
    except PermissionError:
        print(f"  ❌ 无权限停止进程 {pid}，尝试强制停止...")
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"  ✅ 强制停止进程 {pid}")
            return True
        except Exception as e:
            print(f"  ❌ 强制停止进程 {pid} 失败: {e}")
            return False
    except Exception as e:
        print(f"  ❌ 停止进程 {pid} 失败: {e}")
        return False

def stop_api_service():
    """
    停止后端API服务
    """
    print("=" * 70)
    print("🛑 停止后端API服务")
    print("=" * 70)
    
    # 1. 查找所有相关进程
    print("\n📋 查找运行中的服务进程...")
    
    # 查找进程名匹配的进程
    process_patterns = ['uvicorn', 'start_api', 'app.api.main']
    pids_by_name = find_processes_by_name(process_patterns)
    
    # 查找占用端口8000的进程
    pids_by_port = find_processes_by_port(8000)
    
    # 合并所有进程ID（去重）
    all_pids = list(set(pids_by_name + pids_by_port))
    
    if not all_pids:
        print("✅ 未找到运行中的后端服务进程")
        print("✅ 端口8000未被占用")
        return True
    
    print(f"📌 找到 {len(all_pids)} 个相关进程: {all_pids}")
    
    # 2. 先尝试优雅停止（SIGTERM）
    print("\n🔄 尝试优雅停止进程...")
    stopped_pids = []
    for pid in all_pids:
        if stop_process(pid, force=False):
            stopped_pids.append(pid)
    
    # 等待进程停止
    if stopped_pids:
        print(f"\n⏳ 等待进程停止（最多5秒）...")
        time.sleep(2)
        
        # 检查是否还有进程在运行
        remaining_pids = []
        for pid in stopped_pids:
            try:
                os.kill(pid, 0)  # 检查进程是否存在
                remaining_pids.append(pid)
            except ProcessLookupError:
                pass  # 进程已停止
        
        if remaining_pids:
            print(f"⚠️  以下进程仍在运行，将强制停止: {remaining_pids}")
            for pid in remaining_pids:
                stop_process(pid, force=True)
            time.sleep(1)
    
    # 3. 检查端口8000是否已释放
    print("\n🔍 检查端口8000状态...")
    remaining_port_pids = find_processes_by_port(8000)
    if remaining_port_pids:
        print(f"⚠️  端口8000仍被占用，进程ID: {remaining_port_pids}")
        print("🔄 强制停止占用端口的进程...")
        for pid in remaining_port_pids:
            stop_process(pid, force=True)
        time.sleep(1)
        
        # 再次检查
        final_port_pids = find_processes_by_port(8000)
        if final_port_pids:
            print(f"❌ 端口8000仍被占用，进程ID: {final_port_pids}")
            print("💡 提示：可能需要手动停止这些进程或使用 sudo 权限")
            return False
        else:
            print("✅ 端口8000已释放")
    else:
        print("✅ 端口8000已释放")
    
    # 4. 最终确认
    print("\n🔍 最终确认...")
    final_pids = find_processes_by_name(process_patterns)
    if final_pids:
        print(f"⚠️  仍有进程在运行: {final_pids}")
        return False
    else:
        print("✅ 所有后端服务进程已停止")
    
    print("\n" + "=" * 70)
    print("✅ 后端API服务已完全停止")
    print("=" * 70)
    return True

def main():
    """主函数"""
    try:
        success = stop_api_service()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 停止服务时发生错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
