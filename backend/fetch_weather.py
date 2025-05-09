import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5"

def fetch_weather(city=None, lat=None, lon=None):
    try:
        if city:
            url = f"{BASE_URL}/weather?q={city}&appid={API_KEY}&units=metric"
        else:
            url = f"{BASE_URL}/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        weather_data = {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "pressure": data["main"]["pressure"],
            "humidity": data["main"]["humidity"],
            "clouds": data["clouds"]["all"],
            "rain_1h": data.get("rain", {}).get("1h", 0),
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "sunrise": data["sys"]["sunrise"],
            "sunset": data["sys"]["sunset"],
            "timestamp": data["dt"]
        }
        logger.debug(f"Fetched current weather: {weather_data}")
        return weather_data
    except Exception as e:
        logger.error(f"Error fetching current weather: {e}")
        return None

def fetch_forecast(city=None, lat=None, lon=None):
    try:
        if city:
            url = f"{BASE_URL}/forecast?q={city}&appid={API_KEY}&units=metric"
        else:
            url = f"{BASE_URL}/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        forecast_data = []
        for item in data["list"][:24]:  # 24 steps = 72 hours (3-hour intervals)
            forecast_data.append({
                "timestamp": item["dt"],
                "temperature": item["main"]["temp"],
                "pressure": item["main"]["pressure"],
                "clouds": item["clouds"]["all"],
                "icon": item["weather"][0]["icon"]
            })
        logger.debug(f"Fetched 72-hour forecast with {len(forecast_data)} entries")
        return forecast_data
    except Exception as e:
        logger.error(f"Error fetching forecast: {e}")
        return None