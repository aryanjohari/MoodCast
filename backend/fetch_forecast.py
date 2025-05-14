import requests
import json
import paho.mqtt.client as mqtt
import time
from datetime import datetime, timedelta
import logging
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenWeatherMap API key
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "d82ef6867adb72ca0227e9d0d3e9fd7e")

# MQTT settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "moodcast/forecast"

# Cities
cities = [
    {"name": "Auckland", "lat": -36.8485, "lon": 174.7633},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
    {"name": "New York", "lat": 40.7128, "lon": -74.006},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name": "Singapore", "lat": 1.3521, "lon": 103.8198},
    {"name": "Dubai", "lat": 25.2048, "lon": 55.2708},
    {"name": "Mumbai", "lat": 19.076, "lon": 72.8777},
    {"name": "Cape Town", "lat": -33.9249, "lon": 18.4241},
]

def fetch_openweathermap_forecast(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        forecasts = []
        for item in data['list'][:16]:  # 48 hours (3-hour intervals)
            timestamp = datetime.utcfromtimestamp(item['dt']).strftime('%Y-%m-%d %H:%M:%S')
            weather = {
                'temp': item['main']['temp'],
                'humidity': item['main']['humidity'],
                'pressure': item['main']['pressure'],
                'wind_speed': item['wind']['speed'],
                'clouds': item['clouds']['all'],
                'rain': item.get('rain', {}).get('3h', 0),
                'timestamp': timestamp,
                'source': 'openweathermap_forecast'
            }
            mood_score = min(max((100 - weather['clouds']) * (weather['temp'] / 30), 0), 100)
            weather['mood_score'] = round(mood_score, 1)
            forecasts.append(weather)
        logger.debug(f"Fetched {len(forecasts)} forecast entries for lat={lat}, lon={lon}")
        return forecasts
    except requests.RequestException as e:
        logger.error(f"Error fetching OpenWeatherMap forecast: {e}")
        return []

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected to MQTT broker")
    else:
        logger.error(f"Failed to connect to MQTT broker with code {rc}")

def main():
    client = mqtt.Client(protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_start()
    except Exception as e:
        logger.error(f"Error connecting to MQTT broker: {e}")
        return

    while True:
        for city in cities:
            forecasts = fetch_openweathermap_forecast(city['lat'], city['lon'])
            for forecast in forecasts:
                payload = {
                    'city': city['name'],
                    'lat': city['lat'],
                    'lon': city['lon'],
                    'weather': {
                        'temp': forecast['temp'],
                        'humidity': forecast['humidity'],
                        'pressure': forecast['pressure'],
                        'wind_speed': forecast['wind_speed'],
                        'clouds': forecast['clouds'],
                        'rain': forecast['rain']
                    },
                    'timestamp': forecast['timestamp'],
                    'source': forecast['source'],
                    'mood_score': forecast['mood_score']
                }
                topic = f"{MQTT_TOPIC}/{city['name']}"
                try:
                    client.publish(topic, json.dumps(payload), qos=1)
                    logger.debug(f"Published forecast to {topic}")
                except Exception as e:
                    logger.error(f"Error publishing to {topic}: {e}")
        time.sleep(3600)  # Run every hour

if __name__ == "__main__":
    main()