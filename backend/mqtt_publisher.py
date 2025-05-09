import paho.mqtt.client as mqtt
import json
import logging
import time

logger = logging.getLogger(__name__)

BROKER = "localhost"
PORT = 1883  # Adjust to 8083 if Mosquitto uses WSS exclusively
CLIENT_ID = "moodcast_publisher"

def get_mqtt_client():
    client = mqtt.Client(client_id=CLIENT_ID)
    client.connect(BROKER, PORT, keepalive=60)
    return client

def publish_weather(weather_data):
    try:
        client = get_mqtt_client()
        topic = "moodcast/weather"
        payload = json.dumps(weather_data)
        result = client.publish(topic, payload, qos=1)
        client.disconnect()
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published weather to {topic}: {payload[:100]}...")
        else:
            logger.error(f"Failed to publish weather to {topic}, rc={result.rc}")
    except Exception as e:
        logger.error(f"Error publishing weather: {e}")

def publish_forecast(forecast_data):
    try:
        client = get_mqtt_client()
        topic = "moodcast/forecast"
        payload = json.dumps(forecast_data)
        result = client.publish(topic, payload, qos=1)
        client.disconnect()
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published forecast to {topic}: {payload[:100]}...")
        else:
            logger.error(f"Failed to publish forecast to {topic}, rc={result.rc}")
    except Exception as e:
        logger.error(f"Error publishing forecast: {e}")

def publish_alert(message):
    try:
        client = get_mqtt_client()
        topic = "moodcast/alerts"
        payload = json.dumps({"message": message})
        result = client.publish(topic, payload, qos=1)
        client.disconnect()
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published alert to {topic}: {payload}")
        else:
            logger.error(f"Failed to publish alert to {topic}, rc={result.rc}")
    except Exception as e:
        logger.error(f"Error publishing alert: {e}")