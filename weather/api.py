import time
import logging

import requests

logger = logging.getLogger(__name__)

_cache = {}
_CACHE_TTL = 3600

WMO_TO_WEATHER = {
    0: "clear",
    1: "clear",
    2: "normal",
    3: "normal",
    45: "normal",
    48: "normal",
    51: "rain",
    53: "rain",
    55: "rain",
    56: "rain",
    57: "rain",
    61: "rain",
    63: "rain",
    65: "rain",
    66: "rain",
    67: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    77: "snow",
    80: "rain",
    81: "rain",
    82: "rain",
    85: "snow",
    86: "snow",
    95: "rain",
    96: "rain",
    99: "rain",
}

DEFAULT_WEATHER = "normal"

_API_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather_for_city(city):
    key = city["key"]
    now = time.time()
    if key in _cache:
        cached_weather, cached_time = _cache[key]
        if now - cached_time < _CACHE_TTL:
            return cached_weather

    try:
        resp = requests.get(_API_URL, params={
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "current_weather": "true",
        }, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        wmo_code = data.get("current_weather", {}).get("weathercode", None)
        weather = WMO_TO_WEATHER.get(wmo_code, DEFAULT_WEATHER) if wmo_code is not None else DEFAULT_WEATHER
    except Exception:
        logger.warning("Weather API failed for %s, falling back to %s", key, DEFAULT_WEATHER)
        weather = DEFAULT_WEATHER

    _cache[key] = (weather, now)
    return weather