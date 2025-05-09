import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API configuration
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL_WEATHER = "https://api.openweathermap.org/data/2.5/weather"
BASE_URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"

def fetch_weather(city):
    """Fetch current weather data for a given city."""
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    try:
        response = requests.get(BASE_URL_WEATHER, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "pressure": data["main"]["pressure"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "wind_speed": data["wind"]["speed"],
            "rain_1h": data.get("rain", {}).get("1h", 0),
            "clouds": data["clouds"]["all"],
            "sunrise": data["sys"]["sunrise"],
            "sunset": data["sys"]["sunset"],
            "timestamp": data["dt"]
        }
    except requests.RequestException as e:
        print(f"Error fetching weather: {e}")
        return None

def fetch_forecast(city, hours=48):
    """Fetch 48-hour weather forecast for a given city."""
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    try:
        response = requests.get(BASE_URL_FORECAST, params=params)
        response.raise_for_status()
        data = response.json()
        # Filter for 48 hours (16 intervals of 3 hours)
        forecast_list = data["list"][:16]
        forecasts = []
        for item in forecast_list:
            forecasts.append({
                "timestamp": item["dt"],
                "temperature": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "pressure": item["main"]["pressure"],
                "humidity": item["main"]["humidity"],
                "description": item["weather"][0]["description"],
                "icon": item["weather"][0]["icon"],
                "wind_speed": item["wind"]["speed"],
                "rain_3h": item.get("rain", {}).get("3h", 0),
                "clouds": item["clouds"]["all"]
            })
        return forecasts
    except requests.RequestException as e:
        print(f"Error fetching forecast: {e}")
        return None

if __name__ == "__main__":
    CITY = "London"  # Change to your preferred city
    # Test current weather
    weather_data = fetch_weather(CITY)
    if weather_data:
        print("Current Weather:", weather_data)
    # Test forecast
    forecast_data = fetch_forecast(CITY)
    if forecast_data:
        print("48-Hour Forecast:")
        for forecast in forecast_data:
            print(forecast)