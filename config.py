"""
Configuration module for SteamDB parser
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Paths
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
APP_IDS_FILE = BASE_DIR / "app_ids.txt"
DATABASE_PATH = DATA_DIR / "steam_data.db"
COOKIES_FILE = DATA_DIR / "cookies.json"
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Parsing parameters
DELAY_BETWEEN_REQUESTS = 1.0  # seconds between requests
REQUEST_TIMEOUT = 90  # seconds (increased for Cloudflare challenge)
MAX_RETRIES = 3
STATS_UPDATE_INTERVAL = 100  # update stats every N processed items
CLOUDFLARE_WAIT_TIME = 15  # seconds to wait for Cloudflare challenge to complete

# Parallelism parameters
PARALLEL_THREADS = 10  # number of parallel browser contexts
COMPARE_BATCH_SIZE = 10  # number of APP IDs in one Compare request (10-20 recommended)

# Browser settings
HEADLESS = False  # Set to False to pass Cloudflare challenge manually on first run
USE_SYSTEM_CHROME = True  # Use installed Chrome instead of Chromium for better Cloudflare bypass
BROWSER_TYPE = "chromium"  # Options: "chromium", "firefox", "webkit" (Safari)
CHROME_CHANNEL = "chrome"  # Options: "chrome", "chrome-beta", "msedge", "chromium" (only for chromium)
DISABLE_IMAGES = True
DISABLE_CSS = True
DISABLE_FONTS = True
DISABLE_SCRIPTS = False  # needed for API to work

# Browser viewport
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# User agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# SteamDB URLs
STEAMDB_BASE_URL = "https://steamdb.info"
STEAMDB_CHARTS_URL = f"{STEAMDB_BASE_URL}/charts"
STEAMDB_COMPARE_URL = f"{STEAMDB_CHARTS_URL}/?compare="
STEAMDB_APP_URL = f"{STEAMDB_BASE_URL}/app"
STEAMDB_API_GRAPH_MAX = f"{STEAMDB_BASE_URL}/api/GetGraphMax"

# Database batch insert size
DB_BATCH_SIZE = 1000  # insert records in batches

# Logging
LOG_FILE = LOGS_DIR / "parser.log"
LOG_LEVEL = "INFO"

