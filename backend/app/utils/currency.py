import time

import httpx


async def get_usd_ars_blue_rate() -> float | None:
    """Fetch the current USD/ARS blue rate from Bluelytics."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.bluelytics.com.ar/v2/latest", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data["blue"]["value_sell"]
    except Exception:
        return None


# In-memory cache for sync version
_rate_cache: dict[str, tuple[float, float]] = {}  # key -> (rate, timestamp)
_CACHE_TTL = 3600  # 1 hour


def get_usd_ars_blue_rate_sync(fallback: float | None = None) -> float | None:
    """Sync version with in-memory cache (TTL 1h). For use in Scrapy pipeline."""
    cache_key = "usd_ars_blue"
    now = time.time()

    cached = _rate_cache.get(cache_key)
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    try:
        resp = httpx.get("https://api.bluelytics.com.ar/v2/latest", timeout=10)
        resp.raise_for_status()
        rate = resp.json()["blue"]["value_sell"]
        _rate_cache[cache_key] = (rate, now)
        return rate
    except Exception:
        if cached:
            return cached[0]
        if fallback is not None:
            return fallback
        # Try env var as last resort
        import os
        env_rate = os.environ.get("USD_ARS_RATE_FALLBACK")
        return float(env_rate) if env_rate else None


def convert_to_usd(price: float, currency: str, usd_ars_rate: float | None) -> float | None:
    if currency == "USD":
        return price
    if currency == "ARS" and usd_ars_rate and usd_ars_rate > 0:
        return round(price / usd_ars_rate, 2)
    return None
