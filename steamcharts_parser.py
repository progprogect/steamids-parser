"""
SteamCharts API parser for CCU data collection
"""
import logging
import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp
import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests"""
    
    def __init__(self, rate: float):
        self.rate = rate  # requests per second
        self.tokens = rate
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        async with self._lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # If not enough tokens, wait
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


class SteamChartsParser:
    """Parser for SteamCharts CCU data via API"""
    
    def __init__(self):
        self.api_url_template = config.STEAMCHARTS_API_URL
        self.timeout = config.STEAMCHARTS_TIMEOUT
        self.retry_attempts = config.STEAMCHARTS_RETRY_ATTEMPTS
        self.retry_delay = config.STEAMCHARTS_RETRY_DELAY
        self.rate_limiter = RateLimiter(config.STEAMCHARTS_REQUESTS_PER_SECOND)
        self.semaphore = asyncio.Semaphore(config.STEAMCHARTS_MAX_CONCURRENT)
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_ccu_data(self, app_id: int) -> Dict[str, List[Dict]]:
        """
        Fetch CCU data for a single app_id from SteamCharts API
        
        Returns:
            Dictionary with 'avg' and 'peak' lists of data points
            Format: {'avg': [{'datetime': 'YYYY-MM-DD HH:MM:SS', 'players': int}, ...],
                     'peak': [{'datetime': 'YYYY-MM-DD HH:MM:SS', 'players': int}, ...]}
            
        Note: Data is saved as-is without aggregation to preserve maximum detail
        (hourly, daily, monthly - whatever granularity API provides)
        """
        async with self.semaphore:
            await self.rate_limiter.acquire()
            
            try:
                raw_data = await self._fetch_api(app_id)
                if not raw_data:
                    logger.debug(f"No data returned for app_id {app_id}")
                    return {'avg': [], 'peak': []}
                
                processed = self._process_raw_data(raw_data)
                if not processed or (not processed.get('avg') and not processed.get('peak')):
                    logger.debug(f"No processed data for app_id {app_id}")
                    return {'avg': [], 'peak': []}
                
                return processed
                
            except Exception as e:
                logger.error(f"Error fetching CCU data for app_id {app_id}: {e}", exc_info=True)
                return {'avg': [], 'peak': []}
    
    async def _fetch_api(self, app_id: int) -> List[List]:
        """
        Fetch raw data from SteamCharts API with retry logic
        
        Returns:
            List of [timestamp_ms, players] pairs
        """
        url = self.api_url_template.format(appid=app_id)
        
        for attempt in range(self.retry_attempts):
            try:
                session = await self._get_session()
                async with session.get(url) as response:
                    if response.status == 404:
                        logger.warning(f"App ID {app_id} not found (404)")
                        return []
                    
                    if response.status == 429:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limited (429) for app_id {app_id}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    if response.status != 200:
                        logger.warning(f"Unexpected status {response.status} for app_id {app_id}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        return []
                    
                    try:
                        data = await response.json()
                    except Exception as json_error:
                        logger.warning(f"Failed to parse JSON for app_id {app_id}: {json_error}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        return []
                    
                    if not isinstance(data, list):
                        logger.warning(f"Invalid data format for app_id {app_id}: expected list")
                        return []
                    
                    logger.debug(f"Fetched {len(data)} data points for app_id {app_id}")
                    return data
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching app_id {app_id} (attempt {attempt + 1}/{self.retry_attempts})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return []
                
            except aiohttp.ClientError as e:
                logger.warning(f"Client error fetching app_id {app_id}: {e} (attempt {attempt + 1}/{self.retry_attempts})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return []
                
            except Exception as e:
                logger.error(f"Unexpected error fetching app_id {app_id}: {e}", exc_info=True)
                return []
        
        return []
    
    def _process_raw_data(self, data: List[List]) -> Dict[str, List[Dict]]:
        """
        Process raw data from API preserving maximum detail (no aggregation)
        
        Args:
            data: List of [timestamp_ms, players] pairs
            
        Returns:
            Dictionary with 'avg' and 'peak' lists containing all data points
            Each point is saved as-is with its original timestamp
        """
        if not data:
            return {'avg': [], 'peak': []}
        
        avg_data = []
        peak_data = []
        
        for point in data:
            if len(point) < 2:
                continue
            
            timestamp_ms = point[0]
            players = point[1]
            
            # Convert timestamp to datetime string
            try:
                if timestamp_ms > 1e10:  # milliseconds
                    timestamp_sec = timestamp_ms / 1000
                else:
                    timestamp_sec = timestamp_ms
                
                dt = datetime.fromtimestamp(timestamp_sec)
                datetime_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                
                players_value = int(players)
                
                # Save each point as both avg and peak (since it's detailed data)
                # This preserves all available detail: hourly, daily, monthly - whatever API provides
                avg_data.append({
                    'datetime': datetime_str,
                    'players': players_value
                })
                
                peak_data.append({
                    'datetime': datetime_str,
                    'players': players_value
                })
                
            except Exception as e:
                logger.warning(f"Error processing timestamp {timestamp_ms}: {e}")
                continue
        
        logger.debug(f"Processed {len(data)} raw data points: {len(avg_data)} avg points, {len(peak_data)} peak points")
        
        return {
            'avg': avg_data,
            'peak': peak_data
        }

