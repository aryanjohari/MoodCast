import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# City coordinates (lat/long)
CITIES = {
    "Auckland": {"lat": -36.8485, "lon": 174.7633, "topic": "auckland"},
    "Tokyo": {"lat": 35.6895, "lon": 139.6917, "topic": "tokyo"},
    "London": {"lat": 51.5074, "lon": -0.1278, "topic": "london"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "topic": "new_york"},
    "Sydney": {"lat": -33.8688, "lon": 151.2093, "topic": "sydney"},
    "Paris": {"lat": 48.8566, "lon": 2.3522, "topic": "paris"},
    "Singapore": {"lat": 1.3521, "lon": 103.8198, "topic": "singapore"},
    "Dubai": {"lat": 25.2048, "lon": 55.2708, "topic": "dubai"},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "topic": "mumbai"},
    "Cape Town": {"lat": -33.9249, "lon": 18.4241, "topic": "cape_town"}
}

# Cache to reduce API calls
cache = {}

def fetch_current_weather(city, lat, lon):
    """Fetch current weather from OpenWeatherMap."""
    cache_key = f"current_{city}"
    if cache_key in cache and (datetime.now() - cache[cache_key]["timestamp"]).seconds < 300:
        logger.info(f"Using cached current weather for {city}")
        return cache[cache_key]["data"]

    try:
        url = f"{OPENWEATHERMAP_URL}/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        result = {
            "city": city,
            "lat": lat,
            "lon": lon,
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "clouds": data["clouds"]["all"],
            "rain": data.get("rain", {}).get("1h", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "openweathermap"
        }
        cache[cache_key] = {"data": result, "timestamp": datetime.now()}
        logger.info(f"Fetched current weather for {city}")
        return result
    except requests.RequestException as e:
        logger.error(f"Error fetching current weather for {city}: {e}")
        return None

def fetch_historical_weather(city, lat, lon):
    """Fetch 24-hour historical weather from Open-Meteo."""
    cache_key = f"historical_{city}"
    if cache_key in cache and (datetime.now() - cache[cache_key]["timestamp"]).seconds < 3600:
        logger.info(f"Using cached historical weather for {city}")
        return cache[cache_key]["data"]

    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        url = (f"{OPENMETEO_URL}?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,"
               f"pressure_msl,cloud_cover,precipitation&start_date={start_date.strftime('%Y-%m-%d')}"
               f"&end_date={end_date.strftime('%Y-%m-%d')}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Take the latest hourly data point
        latest = data["hourly"]
        result = {
            "city": city,
            "lat": lat,
            "lon": lon,
            "temp": latest["temperature_2m"][-1],
            "humidity": latest["relative_humidity_2m"][-1],
            "pressure": latest["pressure_msl"][-1],
            "clouds": latest["cloud_cover"][-1],
            "rain": latest["precipitation"][-1],
            "timestamp": latest["time"][-1],
            "source": "openmeteo"
        }
        cache[cache_key] = {"data": result, "timestamp": datetime.now()}
        logger.info(f"Fetched historical weather for {city}")
        return result
    except requests.RequestException as e:
        logger.error(f"Error fetching historical weather for {city}: {e}")
        return None

def fetch_all_weather():
    """Fetch current and historical weather for all cities."""
    results = []
    for city, info in CITIES.items():
        current = fetch_current_weather(city, info["lat"], info["lon"])
        historical = fetch_historical_weather(city, info["lat"], info["lon"])
        if current:
            results.append(current)
        if historical:
            results.append(historical)
    return results