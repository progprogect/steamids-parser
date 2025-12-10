"""
CCU parser using Compare tool for batch processing
"""
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class CCUParser:
    """Parser for CCU data using Compare tool"""
    
    def __init__(self):
        self.timeout = config.REQUEST_TIMEOUT * 1000  # milliseconds
    
    async def parse_ccu_batch(self, context, app_ids: List[int]) -> Dict[int, List[Dict]]:
        """
        Parse CCU data for a batch of APP IDs using Compare tool
        
        Returns:
            Dictionary mapping app_id to list of data points
        """
        if not app_ids:
            return {}
        
        try:
            # Create Compare URL
            compare_ids = ','.join(map(str, app_ids))
            url = f"{config.STEAMDB_COMPARE_URL}{compare_ids}"
            
            logger.debug(f"Fetching CCU data for {len(app_ids)} APP IDs via Compare")
            
            # Create page
            page = await context.new_page()
            
            # Set up response interceptor BEFORE navigation
            api_responses = {}
            
            async def handle_response(response):
                url_str = response.url
                if "GetGraphMax" in url_str and "appid=" in url_str:
                    try:
                        app_id_match = url_str.split("appid=")[-1].split("&")[0].split("/")[0]
                        if app_id_match.isdigit():
                            app_id = int(app_id_match)
                            if response.status == 200:
                                try:
                                    data = await response.json()
                                    api_responses[app_id] = data
                                    logger.info(f"✅ Intercepted API response for app_id {app_id}: {len(data) if isinstance(data, list) else 'not a list'} items")
                                except Exception as e:
                                    logger.debug(f"Failed to parse JSON for app_id {app_id}: {e}")
                    except Exception as e:
                        logger.debug(f"Error handling response {url_str}: {e}")
            
            page.on("response", handle_response)
            
            try:
                # Navigate to Compare page and wait for it to fully load
                logger.debug(f"Navigating to {url}")
                # Use domcontentloaded first, then wait for networkidle
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                
                # Wait for Cloudflare challenge to complete (if present)
                logger.debug("Waiting for Cloudflare challenge to complete...")
                await asyncio.sleep(config.CLOUDFLARE_WAIT_TIME)
                
                # Now wait for network to be idle (all API calls completed)
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception as e:
                    logger.debug(f"Networkidle timeout, continuing anyway: {e}")
                
                # Extract data from intercepted responses
                results = {}
                for app_id in app_ids:
                    if app_id in api_responses:
                        data = self._parse_api_response(api_responses[app_id], app_id)
                        if data:
                            results[app_id] = data
                            logger.info(f"✅ Successfully parsed {len(data)} data points for app_id {app_id}")
                        else:
                            logger.warning(f"Failed to parse data for app_id {app_id}")
                            results[app_id] = []
                    else:
                        logger.warning(f"No intercepted response for app_id {app_id}, trying fallback methods")
                        # Fallback: try to fetch via API
                        data = await self._fetch_api_data(page, app_id)
                        if data:
                            results[app_id] = data
                            logger.info(f"✅ Successfully fetched {len(data)} data points for app_id {app_id} via fallback")
                        else:
                            logger.warning(f"No data returned for app_id {app_id}")
                            results[app_id] = []
                
                return results
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Error parsing CCU batch: {e}")
            # Return empty results for all APP IDs
            return {app_id: [] for app_id in app_ids}
    
    async def _fetch_api_data(self, page, app_id: int) -> List[Dict]:
        """Fetch CCU data from API response"""
        try:
            api_url = f"{config.STEAMDB_API_GRAPH_MAX}/?appid={app_id}"
            logger.debug(f"Fetching API data for app_id {app_id} from {api_url}")
            
            # Method 1: Wait for API response that was already triggered by page load
            # Increased timeout for Cloudflare challenge
            try:
                response = await page.wait_for_response(
                    lambda r: "GetGraphMax" in r.url and str(app_id) in r.url and r.status == 200,
                    timeout=30000  # 30 seconds instead of 10
                )
                if response:
                    data = await response.json()
                    logger.debug(f"Got API response via wait_for_response for app_id {app_id}: {len(data) if isinstance(data, list) else 'not a list'} items")
                    return self._parse_api_response(data, app_id)
            except asyncio.TimeoutError:
                logger.debug(f"Timeout waiting for API response for app_id {app_id}")
            except Exception as e:
                logger.debug(f"Error in wait_for_response for app_id {app_id}: {e}")
            
            # Method 2: Make API request through page context (with cookies)
            # This should work because we're in the same browser context
            try:
                # Use page context to make request (includes cookies)
                response = await page.request.get(api_url)
                logger.debug(f"Direct API request status for app_id {app_id}: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Got API response via direct request for app_id {app_id}: {len(data) if isinstance(data, list) else 'not a list'} items")
                    return self._parse_api_response(data, app_id)
                elif response.status == 403:
                    logger.warning(f"API request blocked (403) for app_id {app_id} - Cloudflare protection")
                else:
                    logger.warning(f"API request failed with status {response.status} for app_id {app_id}")
            except Exception as e:
                logger.debug(f"Direct API request failed for app_id {app_id}: {e}")
            
            # Method 3: Try via JavaScript fetch
            try:
                response_data = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const response = await fetch('{api_url}');
                            if (response.ok) {{
                                return await response.json();
                            }} else {{
                                console.log('Fetch failed with status:', response.status);
                                return null;
                            }}
                        }} catch (e) {{
                            console.log('Fetch error:', e);
                            return null;
                        }}
                    }}
                """)
                
                if response_data:
                    logger.debug(f"Got API response via JavaScript fetch for app_id {app_id}: {len(response_data) if isinstance(response_data, list) else 'not a list'} items")
                    return self._parse_api_response(response_data, app_id)
                else:
                    logger.debug(f"JavaScript fetch returned null for app_id {app_id}")
            except Exception as e:
                logger.debug(f"JavaScript fetch failed for app_id {app_id}: {e}")
            
            logger.warning(f"All methods failed to fetch data for app_id {app_id}")
            return []
            
        except Exception as e:
            logger.error(f"API fetch failed for app_id {app_id}: {e}", exc_info=True)
            return []
    
    def _parse_api_response(self, data: List, app_id: int) -> List[Dict]:
        """Parse API response data"""
        if not isinstance(data, list):
            return []
        
        result = []
        for item in data:
            if isinstance(item, dict):
                timestamp = item.get('time', item.get('timestamp', item.get('x')))
                players = item.get('players', item.get('y', item.get('value')))
                
                if timestamp and players is not None:
                    datetime_str = self._normalize_datetime(timestamp)
                    result.append({
                        'datetime': datetime_str,
                        'players': int(players)
                    })
            elif isinstance(item, list) and len(item) >= 2:
                # Format: [timestamp, players]
                timestamp = item[0]
                players = item[1]
                datetime_str = self._normalize_datetime(timestamp)
                result.append({
                    'datetime': datetime_str,
                    'players': int(players)
                })
        
        logger.debug(f"Parsed {len(result)} data points for app_id {app_id}")
        return result
    
    def _normalize_datetime(self, timestamp) -> str:
        """Normalize datetime to YYYY-MM-DD HH:MM:SS format"""
        try:
            # Handle Unix timestamp (seconds)
            if isinstance(timestamp, (int, float)):
                if timestamp > 1e10:  # milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle string timestamps
            if isinstance(timestamp, str):
                # Try various formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d %H:%M:%S.%f'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        continue
            
            # Fallback
            return str(timestamp)
            
        except Exception as e:
            logger.warning(f"Failed to normalize datetime {timestamp}: {e}")
            return str(timestamp)

