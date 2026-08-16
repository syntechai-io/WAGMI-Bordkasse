import logging
import requests
import defusedxml.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Optional
from models import Currency

logger = logging.getLogger(__name__)

# Last-resort static rates, only used if the ECB is unreachable and no
# successful ECB fetch exists in this process.
_STATIC_FALLBACK = {"EUR": 1.0, "DKK": 7.46, "SEK": 11.50, "GBP": 0.86}


class CurrencyService:
    ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

    _cache: Dict[str, float] = {}
    _cache_timestamp: Optional[datetime] = None
    _cache_duration = timedelta(hours=24)
    _last_good: Dict[str, float] = {}
    # True when the currently served rates are not fresh ECB data.
    using_fallback: bool = False

    @classmethod
    def _fetch_ecb_rates(cls) -> Optional[Dict[str, float]]:
        """Fetch latest exchange rates from ECB. Returns None on failure."""
        try:
            response = requests.get(cls.ECB_URL, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {
                "gesmes": "http://www.gesmes.org/2002-08-01",
                "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
            }
            rates = {"EUR": 1.0}

            for cube in root.findall(".//eurofxref:Cube[@currency]", ns):
                currency = cube.get("currency")
                rate_str = cube.get("rate")
                if currency and rate_str and currency in ("DKK", "SEK", "GBP"):
                    rates[currency] = float(rate_str)

            if len(rates) < 2:
                logger.warning("ECB response parsed but contained no tracked rates")
                return None
            return rates
        except Exception:
            logger.exception("Failed to fetch ECB exchange rates")
            return None

    @classmethod
    def get_rates(cls) -> Dict[str, float]:
        """Get exchange rates with caching and graceful degradation."""
        now = datetime.now()
        cache_valid = (
            bool(cls._cache)
            and cls._cache_timestamp is not None
            and (now - cls._cache_timestamp) <= cls._cache_duration
        )
        if cache_valid:
            return cls._cache

        fresh = cls._fetch_ecb_rates()
        if fresh is not None:
            cls._cache = fresh
            cls._last_good = dict(fresh)
            cls._cache_timestamp = now
            cls.using_fallback = False
            return cls._cache

        if cls._last_good:
            logger.warning("Using last successful ECB rates (ECB currently unreachable)")
            cls._cache = dict(cls._last_good)
        else:
            logger.warning("Using static fallback rates (ECB never reached this process)")
            cls._cache = dict(_STATIC_FALLBACK)
        cls._cache_timestamp = now
        cls.using_fallback = True
        return cls._cache

    @classmethod
    def convert_to_eur(cls, amount: float, currency: Currency) -> float:
        """Convert amount from given currency to EUR."""
        if currency == Currency.EUR:
            return amount

        rates = cls.get_rates()
        rate = rates.get(currency.value)
        if not rate:
            logger.error(
                "No exchange rate for %s; treating as 1:1 with EUR",
                currency.value,
            )
            rate = 1.0
        return amount / rate

    @classmethod
    def convert_from_eur(cls, amount_eur: float, currency: Currency) -> float:
        """Convert amount from EUR to given currency."""
        if currency == Currency.EUR:
            return amount_eur

        rates = cls.get_rates()
        rate = rates.get(currency.value)
        if not rate:
            logger.error(
                "No exchange rate for %s; treating as 1:1 with EUR",
                currency.value,
            )
            rate = 1.0
        return amount_eur * rate

    @classmethod
    def format_amount(cls, amount: float, currency: Currency, amount_eur: float) -> str:
        """Format amount showing original currency and EUR conversion."""
        if currency == Currency.EUR:
            return f"{amount:.2f} €"
        return f"{amount:.2f} {currency.value} ({amount_eur:.2f} €)"