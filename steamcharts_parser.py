"""
SteamCharts API parser for CCU data collection
"""
import logging
import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import re
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
            Dictionary with 'avg' list of data points (only average values)
            Format: {'avg': [{'datetime': 'YYYY-MM-DD HH:MM:SS', 'players': int}, ...]}
            
        Note: 
        - Only average values are collected from chart-data.json API
        - Data is saved as-is without aggregation to preserve maximum detail
        - Granularity: hourly, daily, monthly - whatever API provides
        """
        async with self.semaphore:
            await self.rate_limiter.acquire()
            
            try:
                # Fetch average values from API
                raw_data = await self._fetch_api(app_id)
                if not raw_data:
                    logger.debug(f"No API data returned for app_id {app_id}")
                    return {'avg': []}
                
                # Process average data
                processed = self._process_raw_data(raw_data, value_type='avg')
                
                if not processed.get('avg'):
                    logger.debug(f"No processed data for app_id {app_id}")
                    return {'avg': []}
                
                return processed
                
            except Exception as e:
                logger.error(f"Error fetching CCU data for app_id {app_id}: {e}", exc_info=True)
                return {'avg': []}
    
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
    
    def _process_raw_data(self, data: List[List], value_type: str = 'avg') -> Dict[str, List[Dict]]:
        """
        Process raw data from API preserving maximum detail (no aggregation)
        
        Args:
            data: List of [timestamp_ms, players] pairs
            value_type: 'avg' or 'peak' (for logging purposes)
            
        Returns:
            Dictionary with 'avg' or 'peak' list containing all data points
            Each point is saved as-is with its original timestamp
        """
        if not data:
            return {value_type: []}
        
        processed_data = []
        
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
                
                processed_data.append({
                    'datetime': datetime_str,
                    'players': players_value
                })
                
            except Exception as e:
                logger.warning(f"Error processing timestamp {timestamp_ms}: {e}")
                continue
        
        logger.debug(f"Processed {len(data)} raw data points as {value_type}: {len(processed_data)} points")
        
        return {value_type: processed_data}
    
    async def _fetch_peak_from_html(self, app_id: int) -> List[Dict]:
        """
        Fetch peak players data from SteamCharts HTML page
        
        Returns:
            List of {'datetime': 'YYYY-MM-DD HH:MM:SS', 'players': int} dicts
        """
        html_url = f"https://steamcharts.com/app/{app_id}"
        
        try:
            session = await self._get_session()
            async with session.get(html_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch HTML for app_id {app_id}: HTTP {response.status}")
                    return []
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find the table with player statistics
                # Table structure: Month | Avg. Players | Gain | % Gain | Peak Players
                table = soup.find('table', class_='common-table')
                
                if not table:
                    # Try to find any table with "Peak Players" header
                    tables = soup.find_all('table')
                    for t in tables:
                        headers = t.find_all('th')
                        if any('peak' in h.get_text().lower() for h in headers):
                            table = t
                            break
                
                if not table:
                    logger.warning(f"Could not find statistics table for app_id {app_id}")
                    return []
                
                peak_data = []
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 5:  # Need at least 5 columns (Month, Avg, Gain, %Gain, Peak)
                        continue
                    
                    try:
                        # Parse month/date (first column, index 0)
                        month_str = cells[0].get_text().strip()
                        # Parse peak players (fifth column, index 4)
                        peak_str = cells[4].get_text().strip().replace(',', '')
                        
                        if not peak_str or not peak_str.isdigit():
                            continue
                        
                        peak_value = int(peak_str)
                        
                        # Convert month string to datetime
                        # Format can be "November 2025", "Last 30 Days", etc.
                        try:
                            # Skip "Last 30 Days" and similar rows
                            if 'last' in month_str.lower() or 'days' in month_str.lower():
                                continue
                            
                            # Format: "November 2025" or "Nov 2025"
                            month_str_clean = month_str.strip()
                            if len(month_str_clean.split()) == 2:
                                # Try full month name first: "November 2025"
                                try:
                                    dt = datetime.strptime(month_str_clean, '%B %Y')
                                except ValueError:
                                    # Try abbreviated: "Nov 2025"
                                    dt = datetime.strptime(month_str_clean, '%b %Y')
                            elif '-' in month_str_clean:
                                # Format: "2024-01"
                                dt = datetime.strptime(month_str_clean, '%Y-%m')
                            else:
                                # Try other formats
                                dt = datetime.strptime(month_str_clean, '%Y-%m-%d')
                            
                            # Use first day of month for monthly data
                            datetime_str = dt.strftime('%Y-%m-01 %H:%M:%S')
                            
                            peak_data.append({
                                'datetime': datetime_str,
                                'players': peak_value
                            })
                        except ValueError as e:
                            logger.debug(f"Could not parse date '{month_str}' for app_id {app_id}: {e}")
                            continue
                            
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing table row for app_id {app_id}: {e}")
                        continue
                
                logger.debug(f"Extracted {len(peak_data)} peak data points from HTML for app_id {app_id}")
                return peak_data
                
        except Exception as e:
            logger.warning(f"Error fetching peak data from HTML for app_id {app_id}: {e}")
            return []
    
    def _combine_avg_peak(self, avg_data: List[Dict], peak_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Combine avg and peak data, matching by datetime when possible
        
        Args:
            avg_data: List of avg data points
            peak_data: List of peak data points
            
        Returns:
            Dictionary with 'avg' and 'peak' lists
        """
        # Create datetime-indexed dictionaries for matching
        avg_dict = {item['datetime']: item['players'] for item in avg_data}
        peak_dict = {item['datetime']: item['players'] for item in peak_data}
        
        # Get all unique datetimes
        all_datetimes = set(avg_dict.keys()) | set(peak_dict.keys())
        
        combined_avg = []
        combined_peak = []
        
        for dt in sorted(all_datetimes):
            if dt in avg_dict:
                combined_avg.append({'datetime': dt, 'players': avg_dict[dt]})
            if dt in peak_dict:
                combined_peak.append({'datetime': dt, 'players': peak_dict[dt]})
        
        return {
            'avg': combined_avg,
            'peak': combined_peak
        }

