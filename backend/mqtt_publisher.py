import paho.mqtt.client as mqtt
import json
from datetime import datetime

BROKER = "localhost"
PORT = 1883
TOPIC_WEATHER = "moodcast/weather"
TOPIC_FORECAST = "moodcast/forecast"
TOPIC_ALERTS = "moodcast/alerts"

def publish_weather(weather_data):
    """Publish current weather data to MQTT."""
    client = mqtt.Client()
    client.connect(BROKER, PORT)
    client.publish(TOPIC_WEATHER, json.dumps(weather_data))
    client.disconnect()

def publish_forecast(forecast_data):
    """Publish 48-hour forecast data to MQTT."""
    client = mqtt.Client()
    client.connect(BROKER, PORT)
    client.publish(TOPIC_FORECAST, json.dumps(forecast_data))
    client.disconnect()

def publish_alert(message):
    """Publish an alert (e.g., pressure drop) to MQTT."""
    client = mqtt.Client()
    client.connect(BROKER, PORT)
    client.publish(TOPIC_ALERTS, json.dumps({"message": message, "timestamp": datetime.utcnow().isoformat()}))
    client.disconnect()