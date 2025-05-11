import paho.mqtt.client as mqtt
import json
import time
import logging
from fetch_weather import fetch_current_weather, fetch_historical_weather, CITIES

# Try to import CallbackAPIVersion, fallback to version 1 API
try:
    from paho.mqtt import CallbackAPIVersion
    MQTT_VERSION = CallbackAPIVersion.VERSION2
except ImportError:
    MQTT_VERSION = None
    logging.warning("paho-mqtt <2.0.0 detected, using deprecated Callback API version 1")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
PREFERRED_SOURCES = {city: None for city in CITIES}  # Track preferred source per city

def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback for MQTT connection."""
    if reason_code == 0:
        logger.debug(f"Connected to MQTT broker with code {reason_code}")
        for city, info in CITIES.items():
            source_topic = f"moodcast/source/{info['topic']}"
            client.subscribe(source_topic, qos=1)
            logger.debug(f"Subscribed to {source_topic}")
    else:
        logger.error(f"Failed to connect to MQTT broker with code {reason_code}")

def on_message(client, userdata, msg):
    """Handle incoming source selection messages."""
    try:
        if msg.topic.startswith("moodcast/source/"):
            payload = json.loads(msg.payload.decode())
            city = payload["city"]
            source = payload["source"]
            if source in ["openweathermap", "openmeteo"]:
                PREFERRED_SOURCES[city] = source
                logger.info(f"Updated preferred source for {city}: {source}")
            else:
                logger.warning(f"Invalid source for {city}: {source}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message on {msg.topic}: {e}")
    except Exception as e:
        logger.error(f"Error processing message on {msg.topic}: {e}")

def on_publish(client, userdata, mid, reason_codes=None, properties=None):
    """Callback for successful publish."""
    logger.debug(f"Published message with mid {mid}")

def publish_sensor_data():
    """Simulate IoT clients publishing sensor data for each city."""
    logger.info("Starting MQTT sensor simulation")
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
            client.on_message = on_message
            client.on_publish = on_publish
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            clients[city] = client
            client.loop_start()
            logger.debug(f"Started MQTT loop for {city}")

        while True:
            logger.debug("Fetching weather data for all cities")
            weather_data = []
            for city, info in CITIES.items():
                preferred_source = PREFERRED_SOURCES.get(city)
                if preferred_source == "openweathermap":
                    data = fetch_current_weather(city, info["lat"], info["lon"])
                    if data:
                        weather_data.append(data)
                    else:
                        logger.warning(f"Failed to fetch openweathermap for {city}, falling back")
                        data = fetch_historical_weather(city, info["lat"], info["lon"])
                        if data:
                            weather_data.append(data)
                elif preferred_source == "openmeteo":
                    data = fetch_historical_weather(city, info["lat"], info["lon"])
                    if data:
                        weather_data.append(data)
                    else:
                        logger.warning(f"Failed to fetch openmeteo for {city}, falling back")
                        data = fetch_current_weather(city, info["lat"], info["lon"])
                        if data:
                            weather_data.append(data)
                else:
                    # Fetch both initially
                    data_current = fetch_current_weather(city, info["lat"], info["lon"])
                    data_historical = fetch_historical_weather(city, info["lat"], info["lon"])
                    if data_current:
                        weather_data.append(data_current)
                    if data_historical:
                        weather_data.append(data_historical)

            if not weather_data:
                logger.warning("No weather data fetched, skipping publish")
                time.sleep(60)
                continue

            for data in weather_data:
                city = data["city"]
                topic = f"moodcast/sensor/{CITIES[city]['topic']}"
                payload = json.dumps(data)
                result = clients[city].publish(topic, payload, qos=1)
                logger.debug(f"Publishing to {topic}: {payload}")
                logger.debug(f"Publish result for {city}: {result.rc}")
            logger.info("Sleeping for 5 minutes")
            time.sleep(300)
    except Exception as e:
        logger.error(f"Error in publish_sensor_data: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up MQTT clients")
        for client in clients.values():
            client.loop_stop()
            client.disconnect()

if __name__ == "__main__":
    logger.info("Starting mqtt_sensor.py")
    publish_sensor_data()