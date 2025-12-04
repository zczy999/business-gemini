"""会话管理模块 - JWT、Session 创建和管理"""

import time
import uuid
import base64
import requests
from typing import Optional, Dict

from .config import CREATE_SESSION_URL, ADD_CONTEXT_FILE_URL
from .account_manager import account_manager
from .jwt_utils import get_jwt_for_account
from .exceptions import AccountRequestError, AccountError
from .utils import raise_for_account_response
from .media_handler import download_image_from_url


def get_headers(jwt: str) -> dict:
    """获取请求头"""
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "authorization": f"Bearer {jwt}",
        "content-type": "application/json",
        "origin": "https://business.gemini.google",
        "referer": "https://business.gemini.google/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "x-server-timeout": "1800",
    }


def ensure_jwt_for_account(account_idx: int, account: dict):
    """确保指定账号的JWT有效，必要时刷新"""
    # 调试日志已关闭
    # print(f"[DEBUG][ensure_jwt_for_account] 开始 - 账号索引: {account_idx}, CSESIDX: {account.get('csesidx')}")
    start_time = time.time()
    
    # 先检查是否需要刷新（快速检查，最小化锁持有时间）
    need_refresh = False
    jwt = None
    with account_manager.lock:
        state = account_manager.account_states[account_idx]
        jwt = state.get("jwt")
        jwt_age = time.time() - state["jwt_time"] if jwt else float('inf')
        # 调试日志已关闭
        # print(f"[DEBUG][ensure_jwt_for_account] JWT状态 - 存在: {jwt is not None}, 年龄: {jwt_age:.2f}秒")
        need_refresh = jwt is None or jwt_age > 240
    
    # 如果需要刷新，在锁外进行网络请求（避免长时间阻塞）
    if need_refresh:
        # 调试日志已关闭
        # print(f"[DEBUG][ensure_jwt_for_account] 需要刷新JWT...")
        from .utils import get_proxy
        proxy = get_proxy()
        try:
            refresh_start = time.time()
            new_jwt = get_jwt_for_account(account, proxy, account_idx)  # 网络请求在锁外进行
            # 调试日志已关闭
            # print(f"[DEBUG][ensure_jwt_for_account] JWT刷新成功 - 耗时: {time.time() - refresh_start:.2f}秒")
            
            # 更新状态（重新获取锁）
            with account_manager.lock:
                state = account_manager.account_states[account_idx]
                state["jwt"] = new_jwt
                state["jwt_time"] = time.time()
                # JWT 刷新不影响 session，session 由 Gemini 服务端维护
                # session 的过期由 ensure_session_for_account 中的 12小时/50次 规则控制
                jwt = new_jwt
        except Exception as e:
            # 调试日志已关闭
            # print(f"[DEBUG][ensure_jwt_for_account] JWT刷新失败: {e}")
            raise
    else:
        # 调试日志已关闭
        # print(f"[DEBUG][ensure_jwt_for_account] 使用缓存JWT")
        pass
    
    # 调试日志已关闭
    # print(f"[DEBUG][ensure_jwt_for_account] 完成 - 总耗时: {time.time() - start_time:.2f}秒")
    return jwt


def create_chat_session(jwt: str, team_id: str, proxy: str, account_idx: Optional[int] = None) -> str:
    """创建会话，返回session ID"""
    # 调试日志已关闭
    # print(f"[DEBUG][create_chat_session] 开始 - team_id: {team_id}")
    start_time = time.time()
    session_id = uuid.uuid4().hex[:12]
    # 调试日志已关闭
    # print(f"[DEBUG][create_chat_session] 生成session_id: {session_id}")
    body = {
        "configId": team_id,
        "additionalParams": {"token": "-"},
        "createSessionRequest": {
            "session": {"name": session_id, "displayName": session_id}
        }
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None
    # 调试日志已关闭
    # print(f"[DEBUG][create_chat_session] 发送请求到: {CREATE_SESSION_URL}")
    # print(f"[DEBUG][create_chat_session] 使用代理: {proxy}")
    
    request_start = time.time()
    try:
        resp = requests.post(
            CREATE_SESSION_URL,
            headers=get_headers(jwt),
            json=body,
            proxies=proxies,
            verify=False,
            timeout=30
        )
    except requests.RequestException as e:
        raise AccountRequestError(f"创建会话请求失败: {e}") from e
    # 调试日志已关闭
    # print(f"[DEBUG][create_chat_session] 请求完成 - 状态码: {resp.status_code}, 耗时: {time.time() - request_start:.2f}秒")

    if resp.status_code != 200:
        # 调试日志已关闭
        # print(f"[DEBUG][create_chat_session] 请求失败 - 响应: {resp.text[:500]}")
        if resp.status_code == 401:
            # 调试日志已关闭
            # print(f"[DEBUG][create_chat_session] 401错误 - 可能是team_id填错了")
            pass
        raise_for_account_response(resp, "创建会话", account_idx)

    data = resp.json()
    session_name = data.get("session", {}).get("name")
    # 调试日志已关闭
    # print(f"[DEBUG][create_chat_session] 完成 - session_name: {session_name}, 总耗时: {time.time() - start_time:.2f}秒")
    return session_name


def ensure_session_for_account(account_idx: int, account: dict):
    """确保指定账号的会话有效

    简化规则：
    - 每个账号只维护一个 session
    - 对话数超过 50 次 → 更新 session
    - 超过 12 小时 → 更新 session
    """
    SESSION_MAX_COUNT = 50  # 最大对话次数
    SESSION_MAX_AGE = 12 * 3600  # 12 小时（秒）

    start_time = time.time()

    jwt = ensure_jwt_for_account(account_idx, account)

    with account_manager.lock:
        state = account_manager.account_states[account_idx]
        current_session = state.get("session")
        session_count = state.get("session_count", 0)
        session_created_time = state.get("session_created_time", 0)

        now = time.time()
        session_age = now - session_created_time if session_created_time > 0 else float('inf')

        # 判断是否需要创建新 session
        need_new_session = (
            current_session is None or  # 没有 session
            session_count >= SESSION_MAX_COUNT or  # 超过 50 次
            session_age >= SESSION_MAX_AGE  # 超过 12 小时
        )

        if need_new_session:
            reason = "无 session" if current_session is None else (
                f"超过 {SESSION_MAX_COUNT} 次" if session_count >= SESSION_MAX_COUNT else
                f"超过 {SESSION_MAX_AGE // 3600} 小时"
            )

            from .utils import get_proxy
            proxy = get_proxy()
            team_id = account.get("team_id")
            new_session = create_chat_session(jwt, team_id, proxy, account_idx)

            # 更新状态
            state["session"] = new_session
            state["session_count"] = 1  # 重置计数
            state["session_created_time"] = now

            print(f"[Session] ✓ 账号 {account_idx} 创建新 session: {new_session}（原因: {reason}）")

            return new_session, jwt, team_id
        else:
            # 复用现有 session，计数 +1
            state["session_count"] = session_count + 1

            return current_session, jwt, account.get("team_id")


def upload_file_to_gemini(jwt: str, session_name: str, team_id: str, 
                          file_content: bytes, filename: str, mime_type: str,
                          proxy: str = None, account_idx: Optional[int] = None) -> str:
    """
    上传文件到 Gemini，返回 Gemini 的 fileId
    
    Args:
        jwt: JWT 认证令牌
        session_name: 会话名称
        team_id: 团队ID
        file_content: 文件内容（字节）
        filename: 文件名
        mime_type: MIME 类型
        proxy: 代理地址
    
    Returns:
        str: Gemini 返回的 fileId
    """
    import base64
    
    start_time = time.time()
    # 调试日志已关闭
    # print(f"[DEBUG][upload_file_to_gemini] 开始上传文件: {filename}, MIME类型: {mime_type}, 文件大小: {len(file_content)} bytes")
    
    encode_start = time.time()
    file_contents_b64 = base64.b64encode(file_content).decode('utf-8')
    # 调试日志已关闭
    # print(f"[DEBUG][upload_file_to_gemini] Base64编码完成 - 耗时: {time.time() - encode_start:.2f}秒, 编码后大小: {len(file_contents_b64)} chars")
    
    body = {
        "addContextFileRequest": {
            "fileContents": file_contents_b64,
            "fileName": filename,
            "mimeType": mime_type,
            "name": session_name
        },
        "additionalParams": {"token": "-"},
        "configId": team_id
    }
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    # 调试日志已关闭
    # print(f"[DEBUG][upload_file_to_gemini] 准备发送请求到: {ADD_CONTEXT_FILE_URL}")
    # print(f"[DEBUG][upload_file_to_gemini] 使用代理: {proxy if proxy else '无'}")
    
    request_start = time.time()
    try:
        resp = requests.post(
            ADD_CONTEXT_FILE_URL,
            headers=get_headers(jwt),
            json=body,
            proxies=proxies,
            verify=False,
            timeout=60
        )
    except requests.RequestException as e:
        raise AccountRequestError(f"文件上传请求失败: {e}") from e
    # 调试日志已关闭
    # print(f"[DEBUG][upload_file_to_gemini] 请求完成 - 耗时: {time.time() - request_start:.2f}秒, 状态码: {resp.status_code}")
    
    if resp.status_code != 200:
        # 调试日志已关闭
        # print(f"[DEBUG][upload_file_to_gemini] 上传失败 - 响应内容: {resp.text[:500]}")
        raise_for_account_response(resp, "文件上传", account_idx)
    
    parse_start = time.time()
    data = resp.json()
    file_id = data.get("addContextFileResponse", {}).get("fileId")
    # 调试日志已关闭
    # print(f"[DEBUG][upload_file_to_gemini] 解析响应完成 - 耗时: {time.time() - parse_start:.2f}秒")
    
    if not file_id:
        # 调试日志已关闭
        # print(f"[DEBUG][upload_file_to_gemini] 响应中未找到fileId - 响应数据: {data}")
        raise ValueError(f"响应中未找到 fileId: {data}")
    
    # 调试日志已关闭
    # print(f"[DEBUG][upload_file_to_gemini] 上传成功 - fileId: {file_id}, 总耗时: {time.time() - start_time:.2f}秒")
    return file_id


def build_download_url(session_name: str, file_id: str) -> str:
    """构造正确的下载URL"""
    return f"https://biz-discoveryengine.googleapis.com/v1alpha/{session_name}:downloadFile?fileId={file_id}&alt=media"


def upload_inline_image_to_gemini(jwt: str, session_name: str, team_id: str, 
                                   image_data: Dict, proxy: str = None, account_idx: Optional[int] = None) -> Optional[str]:
    """上传内联图片到 Gemini，返回 fileId"""
    try:
        ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
        
        if image_data.get("type") == "base64":
            mime_type = image_data.get("mime_type", "image/png")
            file_content = base64.b64decode(image_data.get("data", ""))
            ext = ext_map.get(mime_type, ".png")
            filename = f"inline_{uuid.uuid4().hex[:8]}{ext}"
        elif image_data.get("type") == "url":
            file_content, mime_type = download_image_from_url(image_data.get("url"), proxy)
            ext = ext_map.get(mime_type, ".png")
            filename = f"url_{uuid.uuid4().hex[:8]}{ext}"
        else:
            return None
        
        return upload_file_to_gemini(jwt, session_name, team_id, file_content, filename, mime_type, proxy, account_idx)
    except AccountError:
        # 让账号相关错误向上抛出，以便触发冷却
        raise
    except Exception:
        return None

