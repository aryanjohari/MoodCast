import paho.mqtt.client as mqtt
import json
import logging
import time

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BROKER = "localhost"
PORT = 1883
CLIENT_ID = "moodcast_publisher"

def get_mqtt_client():
    client = mqtt.Client(client_id=CLIENT_ID)
    client.connect(BROKER, PORT, keepalive=60)
    return client

def publish_weather(city, weather_data):
    try:
        client = get_mqtt_client()
        topic = f"moodcast/sensor/{city}"
        payload = json.dumps(weather_data)
        result = client.publish(topic, payload, qos=1)
        client.disconnect()
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published weather to {topic}: {payload[:100]}...")
        else:
            logger.error(f"Failed to publish weather to {topic}, rc={result.rc}")
    except Exception as e:
        logger.error(f"Error publishing weather: {e}")

def publish_forecast(city, forecast_data):
    try:
        client = get_mqtt_client()
        topic = f"moodcast/forecast/{city}"
        payload = json.dumps(forecast_data)
        result = client.publish(topic, payload, qos=1)
        client.disconnect()
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published forecast to {topic}: {payload[:100]}...")
        else:
            logger.error(f"Failed to publish forecast to {topic}, rc={result.rc}")
    except Exception as e:
        logger.error(f"Error publishing forecast: {e}")

def publish_quality(city, quality_data):
    try:
        client = get_mqtt_client()
        topic = f"moodcast/quality/{city}"
        payload = json.dumps(quality_data)
        result = client.publish(topic, payload, qos=1)
        client.disconnect()
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published quality to {topic}: {payload}")
        else:
            logger.error(f"Failed to publish quality to {topic}, rc={result.rc}")
    except Exception as e:
        logger.error(f"Error publishing quality: {e}")