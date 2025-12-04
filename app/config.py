"""配置和常量定义"""

import os
from pathlib import Path

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "business_gemini_session.json"

# 图片缓存配置
IMAGE_CACHE_DIR = Path(__file__).parent.parent / "image"
IMAGE_CACHE_HOURS = 1  # 图片缓存时间（小时）
IMAGE_CACHE_DIR.mkdir(exist_ok=True)

VIDEO_CACHE_DIR = Path(__file__).parent.parent / "video"
VIDEO_CACHE_HOURS = 6  # 视频缓存时间（小时）
VIDEO_CACHE_DIR.mkdir(exist_ok=True)

MEDIA_STREAM_CHUNK_SIZE = 65536  # 64KB

# API endpoints
BASE_URL = "https://biz-discoveryengine.googleapis.com/v1alpha/locations/global"
CREATE_SESSION_URL = f"{BASE_URL}/widgetCreateSession"
STREAM_ASSIST_URL = f"{BASE_URL}/widgetStreamAssist"
LIST_FILE_METADATA_URL = f"{BASE_URL}/widgetListSessionFileMetadata"
ADD_CONTEXT_FILE_URL = f"{BASE_URL}/widgetAddContextFile"
GETOXSRF_URL = "https://business.gemini.google/auth/getoxsrf"

# 账号错误冷却时间（秒）
AUTH_ERROR_COOLDOWN_SECONDS = 900      # 凭证错误，15分钟
RATE_LIMIT_COOLDOWN_SECONDS = 300      # 触发限额，5分钟
GENERIC_ERROR_COOLDOWN_SECONDS = 120   # 其他错误的短暂冷却

# 日志级别
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "ERROR": 40}
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
CURRENT_LOG_LEVEL_NAME = DEFAULT_LOG_LEVEL if DEFAULT_LOG_LEVEL in LOG_LEVELS else "INFO"
CURRENT_LOG_LEVEL = LOG_LEVELS[CURRENT_LOG_LEVEL_NAME]

# 时区支持
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# Playwright 支持（用于自动刷新 Cookie）
PLAYWRIGHT_AVAILABLE = False
PLAYWRIGHT_BROWSER_INSTALLED = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
    # 检查浏览器是否已安装
    try:
        with sync_playwright() as p:
            # 尝试获取 chromium，如果未安装会抛出异常
            try:
                p.chromium.executable_path
                PLAYWRIGHT_BROWSER_INSTALLED = True
            except Exception:
                PLAYWRIGHT_BROWSER_INSTALLED = False
    except Exception:
        PLAYWRIGHT_BROWSER_INSTALLED = False
except ImportError:
    # Playwright 未安装，使用默认值 False
    pass

