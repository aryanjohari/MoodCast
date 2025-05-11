import requests
import logging
from datetime import datetime, timedelta
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CITIES = {
    "Auckland": {"lat": -36.8485, "lon": 174.7633, "topic": "auckland"},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503, "topic": "tokyo"},
    "London": {"lat": 51.5074, "lon": -0.1278, "topic": "london"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "topic": "new_york"},
    "Sydney": {"lat": -33.8688, "lon": 151.2093, "topic": "sydney"},
    "Paris": {"lat": 48.8566, "lon": 2.3522, "topic": "paris"},
    "Singapore": {"lat": 1.3521, "lon": 103.8198, "topic": "singapore"},
    "Dubai": {"lat": 25.2048, "lon": 55.2708, "topic": "dubai"},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "topic": "mumbai"},
    "Cape Town": {"lat": -33.9249, "lon": 18.4241, "topic": "cape_town"}
}

def fetch_current_weather(city, lat, lon):
    """Fetch current weather from OpenWeatherMap."""
    api_key = "your_openweathermap_api_key"  # Replace with your key
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return {
                "city": city,
                "lat": lat,
                "lon": lon,
                "temp": data["main"]["temp"],
                "humidity": data["main"].get("humidity"),
                "pressure": data["main"].get("pressure"),
                "wind_speed": data["wind"].get("speed"),
                "clouds": data["clouds"].get("all"),
                "rain": data.get("rain", {}).get("1h", 0),
                "timestamp": datetime.utcnow().isoformat(),  # Use current UTC time
                "source": "openweathermap"
            }
        except requests.RequestException as e:
            logger.error(f"Error fetching current weather for {city}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
            else:
                return None
    return None

def fetch_historical_weather(city, lat, lon):
    """Fetch historical weather from Open-Meteo."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&hourly=temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,cloud_cover,precipitation"
           f"&start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}")
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            latest = data["hourly"]
            index = -1  # Latest available hour
            return {
                "city": city,
                "lat": lat,
                "lon": lon,
                "temp": latest["temperature_2m"][index],
                "humidity": latest["relative_humidity_2m"][index],
                "pressure": latest["pressure_msl"][index],
                "wind_speed": latest["wind_speed_10m"][index],
                "clouds": latest["cloud_cover"][index],
                "rain": latest["precipitation"][index],
                "timestamp": datetime.utcnow().isoformat(),  # Use current UTC time
                "source": "openmeteo"
            }
        except requests.RequestException as e:
            logger.error(f"Error fetching historical weather for {city}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return None
    return None

def fetch_all_weather():
    """Fetch weather data for all cities from both sources."""
    weather_data = []
    for city, info in CITIES.items():
        current = fetch_current_weather(city, info["lat"], info["lon"])
        historical = fetch_historical_weather(city, info["lat"], info["lon"])
        if current:
            weather_data.append(current)
        if historical:
            weather_data.append(historical)
    return weather_data