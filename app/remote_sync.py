"""远程同步模块 - 将 Cookie 更新推送到远程服务器"""

import requests
from typing import Optional, Dict, Any
from .account_manager import account_manager


def get_remote_sync_config() -> Dict[str, Optional[str]]:
    """获取远程同步配置"""
    config = account_manager.config or {}
    return {
        "url": config.get("remote_sync_url", "").strip(),
        "api_key": config.get("remote_sync_api_key", "").strip()
    }


def sync_cookie_to_remote(account_idx: int, cookie_data: Dict[str, Any]) -> bool:
    """
    将 Cookie 同步到远程服务器

    Args:
        account_idx: 账号索引
        cookie_data: Cookie 数据，包含 secure_c_ses, host_c_oses, csesidx 等

    Returns:
        bool: 同步是否成功
    """
    sync_config = get_remote_sync_config()
    remote_url = sync_config["url"]
    api_key = sync_config["api_key"]

    if not remote_url:
        # 未配置远程同步，跳过
        return True

    if not api_key:
        print("[远程同步] 未配置 API Key，跳过同步")
        return False

    # 构建请求
    url = f"{remote_url.rstrip('/')}/api/accounts/{account_idx}"
    headers = {
        "Content-Type": "application/json",
        "X-Admin-Token": api_key
    }

    # 准备同步数据
    sync_data = {
        "secure_c_ses": cookie_data.get("secure_c_ses", ""),
        "host_c_oses": cookie_data.get("host_c_oses", ""),
        "csesidx": cookie_data.get("csesidx", ""),
    }

    try:
        print(f"[远程同步] 正在同步账号 {account_idx} 到 {remote_url}...")
        response = requests.put(url, json=sync_data, headers=headers, timeout=30)

        if response.status_code == 200:
            print(f"[远程同步] ✓ 账号 {account_idx} 同步成功")
            return True
        else:
            print(f"[远程同步] ✗ 账号 {account_idx} 同步失败: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"[远程同步] 错误信息: {error_data}")
            except Exception:
                print(f"[远程同步] 响应内容: {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        print(f"[远程同步] ✗ 账号 {account_idx} 同步超时")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"[远程同步] ✗ 账号 {account_idx} 连接失败: {e}")
        return False
    except Exception as e:
        print(f"[远程同步] ✗ 账号 {account_idx} 同步异常: {e}")
        return False


def test_remote_connection() -> Dict[str, Any]:
    """
    测试远程服务器连接

    Returns:
        dict: {"success": bool, "message": str}
    """
    sync_config = get_remote_sync_config()
    remote_url = sync_config["url"]
    api_key = sync_config["api_key"]

    if not remote_url:
        return {"success": False, "message": "未配置远程服务器地址"}

    if not api_key:
        return {"success": False, "message": "未配置 API Key"}

    # 尝试访问账号列表 API 测试连接
    url = f"{remote_url.rstrip('/')}/api/accounts"
    headers = {"X-Admin-Token": api_key}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"success": True, "message": "连接成功"}
        elif response.status_code == 401 or response.status_code == 403:
            return {"success": False, "message": "API Key 无效"}
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "连接超时"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "无法连接到服务器"}
    except Exception as e:
        return {"success": False, "message": str(e)}
