# app/services/weather.py — Open-Meteo forecast fetcher with cache (Section 4.3.3)
import time
from datetime import datetime, timezone

import httpx

from app.core.errors import ApiError

_cache: dict[str, tuple[float, dict]] = {}  # key -> (expiry_time, data)
_CACHE_TTL = 30 * 60  # 30 minutes
_TIMEOUT = 5.0


def _cache_key(lat: float, lng: float, hour: int) -> str:
    return f"{round(lat, 2)},{round(lng, 2)},{hour}"


async def fetch_forecast(lat: float, lng: float, simulate_rain_in_hours: int | None) -> dict:
    """Fetch 48 hourly rows from Open-Meteo. Returns weather summary dict.

    If simulateRainInHours is set and Open-Meteo fails, use a neutral baseline.
    If simulateRainInHours is None and Open-Meteo fails, raise WEATHER_UNAVAILABLE.
    """
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    key = _cache_key(lat, lng, current_hour)

    cached = _cache.get(key)
    raw_data = None
    if cached and cached[0] > time.time():
        raw_data = cached[1]

    if raw_data is None:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lng}"
            f"&hourly=precipitation_probability,temperature_2m,relative_humidity_2m,vapour_pressure_deficit"
            f"&forecast_days=3&timezone=UTC"
        )
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                raw_data = resp.json()
                _cache[key] = (time.time() + _CACHE_TTL, raw_data)
        except Exception:
            if simulate_rain_in_hours is not None:
                raw_data = None  # will use neutral baseline
            else:
                raise ApiError(502, "WEATHER_UNAVAILABLE",
                               "Weather forecast service unavailable",
                               {"provider": "OPEN_METEO"})

    # Extract 48 hourly rows starting at the current UTC hour
    if raw_data is not None:
        hourly = raw_data.get("hourly", {})
        precip = hourly.get("precipitation_probability", [])
        temp = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        vpd = hourly.get("vapour_pressure_deficit", [])

        # Find the index corresponding to the current hour
        times = hourly.get("time", [])
        now_str = now.strftime("%Y-%m-%dT%H:00")
        try:
            start_idx = next(i for i, t in enumerate(times) if t >= now_str)
        except StopIteration:
            start_idx = 0

        precip_48 = precip[start_idx:start_idx + 48]
        temp_48 = temp[start_idx:start_idx + 48]
        humidity_48 = humidity[start_idx:start_idx + 48]
        vpd_48 = vpd[start_idx:start_idx + 48]

        # Pad if fewer than 48 rows
        while len(precip_48) < 48:
            precip_48.append(0)
        while len(temp_48) < 48:
            temp_48.append(25.0)
        while len(humidity_48) < 48:
            humidity_48.append(60)
        while len(vpd_48) < 48:
            vpd_48.append(1.0)
    else:
        # Neutral baseline (Open-Meteo failed, simulateRainInHours is set)
        precip_48 = [0.0] * 48
        temp_48 = [25.0] * 48  # will be replaced with crop referenceTempC by caller
        humidity_48 = [60.0] * 48
        vpd_48 = [1.0] * 48

    return {
        "precipitation_probability": precip_48,
        "temperature": temp_48,
        "humidity": humidity_48,
        "vpd": vpd_48,
        "from_baseline": raw_data is None,
    }


def apply_rain_simulation(weather: dict, h: int) -> dict:
    """Apply rain simulation: set precip probability to max(value, 90) for hours h to h+3."""
    precip = list(weather["precipitation_probability"])
    end = min(h + 4, 48)
    for i in range(h, end):
        precip[i] = max(precip[i], 90)
    weather["precipitation_probability"] = precip
    return weather


def summarize_weather(weather: dict) -> dict:
    """Compute weather summary fields from 48-row arrays."""
    precip = weather["precipitation_probability"]
    temp = weather["temperature"]
    humidity = weather["humidity"]
    vpd = weather["vpd"]

    rain_prob_max_pct = max(precip) if precip else 0.0
    rain_expected_in_hours = None
    for i, p in enumerate(precip):
        if p >= 60:
            rain_expected_in_hours = float(i)
            break
    temp_max_c = max(temp) if temp else 0.0
    humidity_mean_pct = sum(humidity) / len(humidity) if humidity else 0.0
    vpd_max_kpa = max(vpd) if vpd else 0.0

    return {
        "rain_prob_max_pct": rain_prob_max_pct,
        "rain_expected_in_hours": rain_expected_in_hours,
        "temp_max_c": temp_max_c,
        "humidity_mean_pct": humidity_mean_pct,
        "vpd_max_kpa": vpd_max_kpa,
    }
