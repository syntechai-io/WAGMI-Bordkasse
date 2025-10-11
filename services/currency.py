import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Optional
from models import Currency

class CurrencyService:
    ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    
    _cache: Dict[str, float] = {}
    _cache_timestamp: Optional[datetime] = None
    _cache_duration = timedelta(hours=24)
    
    @classmethod
    def _fetch_ecb_rates(cls) -> Dict[str, float]:
        """Fetch latest exchange rates from ECB"""
        try:
            response = requests.get(cls.ECB_URL, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            ns = {
                'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                'eurofxref': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
            }
            
            rates = {'EUR': 1.0}
            
            for cube in root.findall('.//eurofxref:Cube[@currency]', ns):
                currency = cube.get('currency')
                rate = float(cube.get('rate'))
                if currency in ['DKK', 'SEK', 'GBP']:
                    rates[currency] = rate
            
            return rates
            
        except Exception as e:
            print(f"Error fetching ECB rates: {e}")
            return {
                'EUR': 1.0,
                'DKK': 7.46,
                'SEK': 11.50,
                'GBP': 0.86
            }
    
    @classmethod
    def get_rates(cls) -> Dict[str, float]:
        """Get exchange rates with caching"""
        now = datetime.now()
        
        if not cls._cache or not cls._cache_timestamp or (now - cls._cache_timestamp) > cls._cache_duration:
            cls._cache = cls._fetch_ecb_rates()
            cls._cache_timestamp = now
        
        return cls._cache
    
    @classmethod
    def convert_to_eur(cls, amount: float, currency: Currency) -> float:
        """Convert amount from given currency to EUR"""
        if currency == Currency.EUR:
            return amount
        
        rates = cls.get_rates()
        rate = rates.get(currency.value, 1.0)
        
        return amount / rate
    
    @classmethod
    def convert_from_eur(cls, amount_eur: float, currency: Currency) -> float:
        """Convert amount from EUR to given currency"""
        if currency == Currency.EUR:
            return amount_eur
        
        rates = cls.get_rates()
        rate = rates.get(currency.value, 1.0)
        
        return amount_eur * rate
    
    @classmethod
    def format_amount(cls, amount: float, currency: Currency, amount_eur: float) -> str:
        """Format amount showing original currency and EUR conversion"""
        if currency == Currency.EUR:
            return f"{amount:.2f} €"
        else:
            return f"{amount:.2f} {currency.value} ({amount_eur:.2f} €)"
