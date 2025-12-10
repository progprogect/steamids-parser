"""
Price History parser
"""
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class PriceParser:
    """Parser for Price History data"""
    
    def __init__(self):
        self.timeout = config.REQUEST_TIMEOUT * 1000  # milliseconds
        self.cloudflare_wait = config.CLOUDFLARE_WAIT_TIME
    
    async def parse_price_data(self, context, app_id: int) -> List[Dict]:
        """
        Parse Price History data for a single APP ID
        
        Returns:
            List of price data points with currency information
        """
        try:
            url = f"{config.STEAMDB_APP_URL}/{app_id}/"
            logger.debug(f"Fetching Price data for app_id {app_id}")
            
            page = await context.new_page()
            
            try:
                # Navigate to app page
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
                
                # Wait for Cloudflare challenge if present
                await asyncio.sleep(self.cloudflare_wait)
                
                # Extract currencies list
                currencies = await self._extract_currencies_list(page)
                
                if not currencies:
                    logger.warning(f"No currencies found for app_id {app_id}")
                    return []
                
                # Parse price history for each currency
                all_price_data = []
                for currency_info in currencies:
                    try:
                        price_data = await self._parse_currency_history(page, currency_info, app_id)
                        all_price_data.extend(price_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse price for currency {currency_info.get('symbol')} for app_id {app_id}: {e}")
                
                logger.debug(f"Parsed {len(all_price_data)} price records for app_id {app_id}")
                return all_price_data
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Error parsing Price data for app_id {app_id}: {e}")
            return []
    
    async def _extract_currencies_list(self, page) -> List[Dict]:
        """Extract list of currencies from Price History section"""
        try:
            # Look for Price History table
            currencies = await page.evaluate("""
                () => {
                    const currencies = [];
                    // Look for price history table
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
                        if (headers.includes('Currency') || headers.includes('Current Price')) {
                            const rows = table.querySelectorAll('tbody tr');
                            rows.forEach(row => {
                                const cells = row.querySelectorAll('td');
                                if (cells.length >= 3) {
                                    const currencyCell = cells[0];
                                    const symbol = currencyCell.textContent.trim();
                                    // Try to find currency name from button or link
                                    const button = currencyCell.querySelector('button');
                                    const name = button ? button.getAttribute('title') || button.textContent.trim() : symbol;
                                    currencies.push({symbol: symbol, name: name});
                                }
                            });
                        }
                    }
                    return currencies;
                }
            """)
            
            if currencies:
                return currencies
            
            # Fallback: look for currency buttons
            currency_buttons = await page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const currencies = [];
                    buttons.forEach(btn => {
                        const text = btn.textContent.trim();
                        const img = btn.querySelector('img');
                        if (img && img.alt) {
                            currencies.push({
                                symbol: img.alt,
                                name: text
                            });
                        }
                    });
                    return currencies;
                }
            """)
            
            return currency_buttons if currency_buttons else []
            
        except Exception as e:
            logger.warning(f"Failed to extract currencies list: {e}")
            return []
    
    async def _parse_currency_history(self, page, currency_info: Dict, app_id: int) -> List[Dict]:
        """Parse price history for a specific currency"""
        try:
            currency_symbol = currency_info.get('symbol', '')
            currency_name = currency_info.get('name', currency_symbol)
            
            # Try to click on currency button to expand history
            try:
                await page.click(f'button:has-text("{currency_symbol}")', timeout=5000)
                await asyncio.sleep(1)  # Wait for data to load
            except:
                pass  # Button might not exist or already clicked
            
            # Extract price history data
            # This is a simplified version - actual implementation may need to parse graph data
            # or extract from API responses
            
            # For now, return empty list - this needs to be implemented based on actual page structure
            # The actual implementation would need to:
            # 1. Find the price history graph/table for this currency
            # 2. Extract "Lowest Recorded Price" data points
            # 3. Parse dates and prices
            
            logger.debug(f"Price history parsing for {currency_symbol} needs implementation based on page structure")
            return []
            
        except Exception as e:
            logger.warning(f"Failed to parse currency history for {currency_symbol}: {e}")
            return []
    
    def _normalize_datetime(self, timestamp) -> str:
        """Normalize datetime to YYYY-MM-DD HH:MM:SS format"""
        try:
            if isinstance(timestamp, (int, float)):
                if timestamp > 1e10:
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            if isinstance(timestamp, str):
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        continue
            
            return str(timestamp)
            
        except Exception as e:
            logger.warning(f"Failed to normalize datetime {timestamp}: {e}")
            return str(timestamp)

