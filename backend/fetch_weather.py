import requests
import logging
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API keys and endpoints
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "684d135ca91c19fce9c0e052e3d55ddc")
OPENWEATHERMAP_URL = "http://api.openweathermap.org/data/2.5/weather"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_openweathermap(lat, lon):
    """Fetch weather data from OpenWeatherMap."""
    logger.debug(f"Fetching OpenWeatherMap data for lat={lat}, lon={lon}")
    if not OPENWEATHERMAP_API_KEY or OPENWEATHERMAP_API_KEY == "":
        logger.error("OpenWeatherMap API key is missing or invalid")
        return None
    
    try:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHERMAP_API_KEY,
            "units": "metric"
        }
        response = requests.get(OPENWEATHERMAP_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"OpenWeatherMap response: {data}")
        return {
            "lat": data["coord"]["lat"],
            "lon": data["coord"]["lon"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "clouds": data["clouds"]["all"],
            "rain": data.get("rain", {}).get("1h", 0),
            "source": "openweathermap"
        }
    except requests.RequestException as e:
        logger.error(f"Error fetching OpenWeatherMap data: {e}")
        return None

def fetch_openmeteo(lat, lon):
    """Fetch weather data from Open-Meteo."""
    logger.debug(f"Fetching Open-Meteo data for lat={lat}, lon={lon}")
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "temperature_2m,relativehumidity_2m,pressure_msl,windspeed_10m,cloudcover,precipitation"
        }
        response = requests.get(OPENMETEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"Open-Meteo response: {data}")
        return {
            "lat": lat,
            "lon": lon,
            "temp": data["current_weather"]["temperature"],
            "humidity": data["hourly"]["relativehumidity_2m"][0],
            "pressure": data["hourly"]["pressure_msl"][0],
            "wind_speed": data["current_weather"]["windspeed"],
            "clouds": data["hourly"]["cloudcover"][0],
            "rain": data["hourly"]["precipitation"][0],
            "source": "openmeteo"
        }
    except requests.RequestException as e:
        logger.error(f"Error fetching Open-Meteo data: {e}")
        return None