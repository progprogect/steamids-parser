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

# Database configuration
# If DATABASE_URL or DATABASE_PUBLIC_URL is set (e.g., from Railway PostgreSQL), use PostgreSQL
# Otherwise, use SQLite
DATABASE_PUBLIC_URL_DEFAULT = "postgresql://postgres:uOPRuIMnrxqslboMcXBWmIpREfTwsQnh@switchyard.proxy.rlwy.net:58449/railway"
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL", DATABASE_PUBLIC_URL_DEFAULT)
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL") or DATABASE_PUBLIC_URL_DEFAULT  # PostgreSQL connection string from Railway
USE_POSTGRESQL = DATABASE_URL is not None

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

# SteamCharts API settings
STEAMCHARTS_API_URL = "https://steamcharts.com/app/{appid}/chart-data.json"
# Can be overridden via environment variables (useful for Railway)
STEAMCHARTS_REQUESTS_PER_SECOND = int(os.getenv("STEAMCHARTS_REQUESTS_PER_SECOND", "100"))
STEAMCHARTS_REQUEST_DELAY = 1.0 / STEAMCHARTS_REQUESTS_PER_SECOND
STEAMCHARTS_MAX_CONCURRENT = int(os.getenv("STEAMCHARTS_MAX_CONCURRENT", "80"))
STEAMCHARTS_RETRY_ATTEMPTS = 3
STEAMCHARTS_RETRY_DELAY = 2.0
STEAMCHARTS_TIMEOUT = 30

# ITAD API settings
ITAD_API_KEY = os.getenv("ITAD_API_KEY", "e717cf2ac561530d8f78cd541560feddbc523c27")  # Get from https://isthereanydeal.com/app/
ITAD_BATCH_SIZE = 200  # Number of app IDs per batch
ITAD_REQUEST_DELAY = 0.5  # Delay between requests (seconds)
ITAD_PARALLEL_THREADS = 3  # Number of parallel threads for history requests (reduced to avoid 429 errors)
ITAD_HISTORY_SINCE = "2012-01-01T00:00:00Z"  # Start date for price history
STEAM_SHOP_ID = 61  # Steam shop ID in ITAD

# Steam Store API settings
STEAM_PARSER_THREADS = 30  # Number of parallel threads for Steam API requests (~50 requests/sec)
STEAM_BATCH_SIZE = 200  # Number of app IDs per batch
STEAM_BATCH_DELAY = 0.1  # Delay between batches (seconds)

# Logging
LOG_FILE = LOGS_DIR / "parser.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

