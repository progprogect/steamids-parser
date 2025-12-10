"""
Browser manager with context pool for parallel processing
"""
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
from threading import Lock
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import config

logger = logging.getLogger(__name__)


class BrowserManager:
    """Browser manager with context pool for parallel processing"""
    
    def __init__(self, num_contexts: int = None):
        self.num_contexts = num_contexts or config.PARALLEL_THREADS
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: List[BrowserContext] = []
        self.available_contexts: List[BrowserContext] = []
        self.context_lock = Lock()
        self.cookies_file = config.COOKIES_FILE
        
    async def initialize(self):
        """Initialize browser and create context pool"""
        self.playwright = await async_playwright().start()
        
        # Launch browser with optimizations
        launch_args = [
            '--disable-dev-shm-usage',
            '--no-sandbox'
        ]
        
        # Select browser type based on config
        browser_type_name = config.BROWSER_TYPE.lower()
        
        if browser_type_name == "firefox":
            browser_type = self.playwright.firefox
            launch_options = {
                'headless': config.HEADLESS
            }
            logger.info("Using Firefox browser")
        elif browser_type_name == "webkit":
            browser_type = self.playwright.webkit
            launch_options = {
                'headless': config.HEADLESS
            }
            logger.info("Using WebKit (Safari) browser")
        else:  # chromium (default)
            browser_type = self.playwright.chromium
            # Only disable images if headless (in headless mode images don't matter)
            if config.HEADLESS and config.DISABLE_IMAGES:
                launch_args.append('--disable-images')
            
            launch_options = {
                'headless': config.HEADLESS,
                'args': launch_args
            }
            
            # Try to use system Chrome/Edge for better Cloudflare bypass
            if config.USE_SYSTEM_CHROME:
                try:
                    # Try to use installed Chrome
                    if config.CHROME_CHANNEL == "chrome":
                        # Try Chrome first
                        try:
                            self.browser = await browser_type.launch(**launch_options, channel="chrome")
                            logger.info("Using system Chrome browser")
                        except Exception:
                            # Fallback to Chromium
                            self.browser = await browser_type.launch(**launch_options)
                            logger.info("Using Chromium browser (Chrome not found)")
                    elif config.CHROME_CHANNEL == "msedge":
                        # Try Edge
                        try:
                            self.browser = await browser_type.launch(**launch_options, channel="msedge")
                            logger.info("Using system Edge browser")
                        except Exception:
                            self.browser = await browser_type.launch(**launch_options)
                            logger.info("Using Chromium browser (Edge not found)")
                    else:
                        self.browser = await browser_type.launch(**launch_options)
                        logger.info("Using Chromium browser")
                except Exception as e:
                    logger.warning(f"Failed to launch system browser: {e}, using Chromium")
                    self.browser = await browser_type.launch(**launch_options)
            else:
                self.browser = await browser_type.launch(**launch_options)
                logger.info("Using Chromium browser")
        
        # Launch browser if not already launched (for Firefox/WebKit)
        if not hasattr(self, 'browser') or self.browser is None:
            try:
                self.browser = await browser_type.launch(**launch_options)
            except Exception as e:
                logger.error(f"Failed to launch {browser_type_name} browser: {e}")
                logger.info("Falling back to Chromium...")
                browser_type = self.playwright.chromium
                self.browser = await browser_type.launch(headless=config.HEADLESS, args=launch_args)
                logger.info("Using Chromium browser as fallback")
        
        # Load cookies if they exist
        cookies = self._load_cookies()
        
        # Create context pool
        await self.create_context_pool(self.num_contexts, cookies)
        
        logger.info(f"Browser initialized with {len(self.contexts)} contexts")
    
    def _load_cookies(self) -> List[Dict]:
        """Load cookies from file"""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    logger.info(f"Loaded {len(cookies)} cookies from file")
                    return cookies
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        return []
    
    def _save_cookies(self, cookies: List[Dict]):
        """Save cookies to file"""
        try:
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.debug(f"Saved {len(cookies)} cookies to file")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")
    
    async def create_context_pool(self, size: int, cookies: List[Dict] = None):
        """Create pool of browser contexts"""
        # For Cloudflare bypass, we'll use fewer contexts but reuse them
        # This maintains session continuity
        actual_size = min(size, 3) if not config.HEADLESS else size  # Use fewer contexts in non-headless mode
        
        for i in range(actual_size):
            # Create context with realistic browser fingerprint
            context = await self.browser.new_context(
                viewport={'width': config.VIEWPORT_WIDTH, 'height': config.VIEWPORT_HEIGHT},
                user_agent=config.USER_AGENT,
                locale='en-US',
                timezone_id='America/New_York',
                # Add extra headers to look more like real browser
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                },
                # Set permissions to look like real user
                permissions=['geolocation'],
                # Set geolocation to look realistic
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York
                # Set color scheme
                color_scheme='light'
            )
            
            # Set up resource blocking
            await self._setup_resource_blocking(context)
            
            # Load cookies if available
            if cookies:
                await context.add_cookies(cookies)
            
            # Inject JavaScript to make browser look more realistic
            await context.add_init_script("""
                // Override navigator properties to look more realistic
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Add Chrome runtime
                window.chrome = {
                    runtime: {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            self.contexts.append(context)
            self.available_contexts.append(context)
        
        logger.info(f"Created context pool with {actual_size} contexts")
    
    async def _setup_resource_blocking(self, context: BrowserContext):
        """Set up resource blocking for optimization"""
        async def route_handler(route):
            resource_type = route.request.resource_type
            url = route.request.url
            
            # Block images
            if config.DISABLE_IMAGES and resource_type == "image":
                await route.abort()
                return
            
            # Block CSS
            if config.DISABLE_CSS and (resource_type == "stylesheet" or url.endswith('.css')):
                await route.abort()
                return
            
            # Block fonts
            if config.DISABLE_FONTS and (resource_type == "font" or 
                                         any(url.endswith(ext) for ext in ['.woff', '.woff2', '.ttf', '.otf'])):
                await route.abort()
                return
            
            await route.continue_()
        
        await context.route("**/*", route_handler)
    
    async def get_context(self) -> BrowserContext:
        """Get available context from pool (blocking)"""
        while True:
            with self.context_lock:
                if self.available_contexts:
                    context = self.available_contexts.pop()
                    # Reload cookies before returning context to ensure session continuity
                    cookies = self._load_cookies()
                    if cookies:
                        try:
                            await context.clear_cookies()
                            await context.add_cookies(cookies)
                        except Exception as e:
                            logger.debug(f"Failed to reload cookies: {e}")
                    return context
            
            # Wait a bit if no context available
            await asyncio.sleep(0.1)
    
    def get_context_sync(self) -> BrowserContext:
        """Get available context from pool (synchronous, for testing)"""
        while True:
            with self.context_lock:
                if self.available_contexts:
                    context = self.available_contexts.pop()
                    return context
            
            # Wait a bit if no context available
            import time
            time.sleep(0.1)
    
    async def return_context(self, context: BrowserContext):
        """Return context to pool and save cookies"""
        # Save cookies before returning context to maintain session
        try:
            cookies = await context.cookies()
            if cookies:
                self._save_cookies(cookies)
                logger.debug(f"Saved {len(cookies)} cookies from context")
        except Exception as e:
            logger.debug(f"Failed to save cookies: {e}")
        
        with self.context_lock:
            if context in self.contexts and context not in self.available_contexts:
                self.available_contexts.append(context)
    
    async def save_cookies_from_context(self, context: BrowserContext):
        """Save cookies from a context"""
        cookies = await context.cookies()
        if cookies:
            self._save_cookies(cookies)
    
    async def close(self):
        """Close all contexts and browser"""
        # Save cookies from first context before closing (if still open)
        if self.contexts:
            try:
                await self.save_cookies_from_context(self.contexts[0])
            except Exception as e:
                logger.debug(f"Could not save cookies during close: {e}")
        
        for context in self.contexts:
            try:
                await context.close()
            except Exception as e:
                logger.debug(f"Error closing context: {e}")
        
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}")
        
        logger.info("Browser closed")


# Synchronous wrapper for easier use
class BrowserManagerSync:
    """Synchronous wrapper for BrowserManager"""
    
    def __init__(self, num_contexts: int = None):
        self.manager = BrowserManager(num_contexts)
        self._loop = None
        self._initialized = False
    
    def _get_loop(self):
        """Get or create event loop"""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def initialize(self):
        """Initialize browser (sync)"""
        loop = self._get_loop()
        loop.run_until_complete(self.manager.initialize())
        self._initialized = True
    
    def get_context(self):
        """Get context (sync)"""
        if not self._initialized:
            self.initialize()
        loop = self._get_loop()
        return loop.run_until_complete(self.manager.get_context())
    
    def return_context(self, context):
        """Return context (sync)"""
        self.manager.return_context(context)
    
    def close(self):
        """Close browser (sync)"""
        if self._initialized:
            loop = self._get_loop()
            loop.run_until_complete(self.manager.close())

