"""
Currency to ITAD country/region mapping
Based on Steam supported currencies and ITAD API country codes
"""
from typing import Dict, List, Optional

# Mapping Steam currencies to ITAD country codes
# ITAD uses country codes, not currency codes directly
CURRENCY_TO_COUNTRY = {
    'USD': 'US',      # United States
    'EUR': 'DE',      # Germany (EU region - using DE as default)
    'GBP': 'GB',      # United Kingdom
    'RUB': 'RU',      # Russia
    'AUD': 'AU',      # Australia
    'CAD': 'CA',      # Canada
    'BRL': 'BR',      # Brazil
    'TRY': 'TR',      # Turkey
    'PLN': 'PL',      # Poland
    'UAH': 'UA',      # Ukraine
    'JPY': 'JP',      # Japan
    'CNY': 'CN',      # China
    'KRW': 'KR',      # South Korea
    'INR': 'IN',      # India
    'MXN': 'MX',      # Mexico
    'ARS': 'AR',      # Argentina
    'CLP': 'CL',      # Chile
    'COP': 'CO',      # Colombia
    'PEN': 'PE',      # Peru
    'ZAR': 'ZA',      # South Africa
    'SGD': 'SG',      # Singapore
    'HKD': 'HK',      # Hong Kong
    'TWD': 'TW',      # Taiwan
    'THB': 'TH',      # Thailand
    'IDR': 'ID',      # Indonesia
    'MYR': 'MY',      # Malaysia
    'PHP': 'PH',      # Philippines
    'VND': 'VN',      # Vietnam
    'ILS': 'IL',      # Israel
    'AED': 'AE',      # United Arab Emirates
    'SAR': 'SA',      # Saudi Arabia
    'KWD': 'KW',      # Kuwait
    'QAR': 'QA',      # Qatar
    'KZT': 'KZ',      # Kazakhstan
    'UYU': 'UY',      # Uruguay
    'CRC': 'CR',      # Costa Rica
    'NOK': 'NO',      # Norway
    'NZD': 'NZ',      # New Zealand
    'CHF': 'CH',      # Switzerland
    'SEK': 'SE',      # Sweden
    'DKK': 'DK',      # Denmark
    'CZK': 'CZ',      # Czech Republic
    'HUF': 'HU',      # Hungary
    'RON': 'RO',      # Romania
    'BGN': 'BG',      # Bulgaria
    'HRK': 'HR',      # Croatia
    'BYN': 'BY',      # Belarus
}

# Currency symbols mapping
CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'RUB': '₽',
    'AUD': 'A$',
    'CAD': 'C$',
    'BRL': 'R$',
    'TRY': '₺',
    'PLN': 'zł',
    'UAH': '₴',
    'JPY': '¥',
    'CNY': '¥',
    'KRW': '₩',
    'INR': '₹',
    'MXN': '$',
    'ARS': '$',
    'CLP': '$',
    'COP': '$',
    'PEN': 'S/',
    'ZAR': 'R',
    'SGD': 'S$',
    'HKD': 'HK$',
    'TWD': 'NT$',
    'THB': '฿',
    'IDR': 'Rp',
    'MYR': 'RM',
    'PHP': '₱',
    'VND': '₫',
    'ILS': '₪',
    'AED': 'د.إ',
    'SAR': '﷼',
    'KWD': 'د.ك',
    'QAR': '﷼',
    'KZT': '₸',
    'UYU': '$U',
    'CRC': '₡',
    'NOK': 'kr',
    'NZD': 'NZ$',
    'CHF': 'CHF',
    'SEK': 'kr',
    'DKK': 'kr',
    'CZK': 'Kč',
    'HUF': 'Ft',
    'RON': 'lei',
    'BGN': 'лв',
    'HRK': 'kn',
    'BYN': 'Br',
}

# Currency names mapping (from Steam documentation)
CURRENCY_NAMES = {
    'USD': 'U.S. Dollar',
    'EUR': 'Euro',
    'GBP': 'British Pound',
    'RUB': 'Russian Ruble',
    'AUD': 'Australian Dollar',
    'CAD': 'Canadian Dollar',
    'BRL': 'Brazilian Real',
    'TRY': 'Turkish Lira',
    'PLN': 'Polish Zloty',
    'UAH': 'Ukrainian Hryvnia',
    'JPY': 'Japanese Yen',
    'CNY': 'Chinese Yuan',
    'KRW': 'South Korean Won',
    'INR': 'Indian Rupee',
    'MXN': 'Mexican Peso',
    'ARS': 'Argentine Peso',
    'CLP': 'Chilean Peso',
    'COP': 'Colombian Peso',
    'PEN': 'Peruvian Sol',
    'ZAR': 'South African Rand',
    'SGD': 'Singapore Dollar',
    'HKD': 'Hong Kong Dollar',
    'TWD': 'New Taiwan Dollar',
    'THB': 'Thai Baht',
    'IDR': 'Indonesian Rupiah',
    'MYR': 'Malaysian Ringgit',
    'PHP': 'Philippine Peso',
    'VND': 'Vietnamese Dong',
    'ILS': 'New Israeli Shekel',
    'AED': 'UAE Dirham',
    'SAR': 'Saudi Riyal',
    'KWD': 'Kuwaiti Dinar',
    'QAR': 'Qatari Riyal',
    'KZT': 'Kazakhstani Tenge',
    'UYU': 'Uruguayan Peso',
    'CRC': 'Costa Rican Colon',
    'NOK': 'Norwegian Krone',
    'NZD': 'New Zealand Dollar',
    'CHF': 'Swiss Franc',
    'SEK': 'Swedish Krona',
    'DKK': 'Danish Krone',
    'CZK': 'Czech Koruna',
    'HUF': 'Hungarian Forint',
    'RON': 'Romanian Leu',
    'BGN': 'Bulgarian Lev',
    'HRK': 'Croatian Kuna',
    'BYN': 'Belarusian Ruble',
}

# List of all supported currencies (active currencies from Steam)
SUPPORTED_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'RUB', 'AUD', 'CAD', 'BRL', 'TRY', 'PLN', 'UAH',
    'JPY', 'CNY', 'KRW', 'INR', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'ZAR',
    'SGD', 'HKD', 'TWD', 'THB', 'IDR', 'MYR', 'PHP', 'VND', 'ILS', 'AED',
    'SAR', 'KWD', 'QAR', 'KZT', 'UYU', 'CRC', 'NOK', 'NZD', 'CHF', 'SEK',
    'DKK', 'CZK', 'HUF', 'RON', 'BGN', 'HRK', 'BYN'
]


def get_country_for_currency(currency: str) -> Optional[str]:
    """Get ITAD country code for Steam currency"""
    return CURRENCY_TO_COUNTRY.get(currency.upper())


def get_currency_symbol(currency: str) -> str:
    """Get currency symbol"""
    return CURRENCY_SYMBOLS.get(currency.upper(), currency.upper())


def get_currency_name(currency: str) -> str:
    """Get currency full name"""
    return CURRENCY_NAMES.get(currency.upper(), currency.upper())


def get_all_currencies() -> List[str]:
    """Get list of all supported currencies"""
    return SUPPORTED_CURRENCIES.copy()

