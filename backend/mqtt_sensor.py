import paho.mqtt.client as mqtt
import json
import time
import logging
from fetch_weather import fetch_all_weather, CITIES

# Try to import CallbackAPIVersion, fallback to version 1 API
try:
    from paho.mqtt import CallbackAPIVersion
    MQTT_VERSION = CallbackAPIVersion.VERSION2
except ImportError:
    MQTT_VERSION = None
    logging.warning("paho-mqtt <2.0.0 detected, using deprecated Callback API version 1")

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback for MQTT connection."""
    if reason_code == 0:
        logger.debug(f"Connected to MQTT broker with code {reason_code}")
    else:
        logger.error(f"Failed to connect to MQTT broker with code {reason_code}")

def on_publish(client, userdata, mid, reason_codes=None, properties=None):
    """Callback for successful publish."""
    logger.debug(f"Published message with mid {mid}")

def publish_sensor_data():
    """Simulate IoT clients publishing sensor data for each city."""
    logger.debug("Starting MQTT sensor simulation")
    clients = {}
    try:
        for city, info in CITIES.items():
            client_id = f"moodcast_sensor_{info['topic']}"
            logger.debug(f"Initializing MQTT client for {city}: {client_id}")
            client_args = {"client_id": client_id}
            if MQTT_VERSION:
                client_args["callback_api_version"] = MQTT_VERSION
            client = mqtt.Client(**client_args)
            client.on_connect = on_connect
            client.on_publish = on_publish
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            clients[city] = client
            client.loop_start()
            logger.debug(f"Started MQTT loop for {city}")

        while True:
            logger.debug("Fetching weather data for all cities")
            weather_data = fetch_all_weather()
            if not weather_data:
                logger.warning("No weather data fetched, skipping publish")
                time.sleep(60)  # Wait before retrying
                continue
            for data in weather_data:
                city = data["city"]
                topic = f"moodcast/sensor/{CITIES[city]['topic']}"
                payload = json.dumps(data)
                result = clients[city].publish(topic, payload, qos=1)
                logger.debug(f"Publishing to {topic}: {payload}")
                logger.debug(f"Publish result for {city}: {result.rc}")
            logger.debug("Sleeping for 5 minutes")
            time.sleep(300)  # Publish every 5 minutes
    except Exception as e:
        logger.error(f"Error in publish_sensor_data: {e}", exc_info=True)
    finally:
        logger.debug("Cleaning up MQTT clients")
        for client in clients.values():
            client.loop_stop()
            client.disconnect()

if __name__ == "__main__":
    logger.debug("Starting mqtt_sensor.py")
    publish_sensor_data()