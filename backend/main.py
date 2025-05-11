import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
from database import store_sensor_data, compute_mood_score

# Try to import CallbackAPIVersion, fallback to version 1 API
try:
    from paho.mqtt import CallbackAPIVersion
    MQTT_VERSION = CallbackAPIVersion.VERSION2
except ImportError:
    MQTT_VERSION = None
    logging.warning("paho-mqtt <2.0.0 detected, using deprecated Callback API version 1")

# Setup logging (switch to INFO after debugging)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
CITIES = ["auckland", "tokyo", "london", "new_york", "sydney", "paris", "singapore", "dubai", "mumbai", "cape_town"]

def preprocess_data(data):
    """Preprocess sensor data (filter outliers, handle missing fields)."""
    try:
        # Required fields
        if not all(key in data for key in ["city", "lat", "lon", "temp", "timestamp", "source"]):
            missing = [key for key in ["city", "lat", "lon", "temp", "timestamp", "source"] if key not in data]
            logger.error(f"Missing required fields {missing} for {data.get('city', 'unknown')}")
            return None

        # Validate temperature
        temp = data.get("temp")
        if temp is None or not (-50 <= temp <= 50):
            logger.warning(f"Invalid temperature {temp} for {data['city']}")
            return None

        # Handle optional fields
        optional_fields = ["humidity", "pressure", "wind_speed", "clouds", "rain"]
        for field in optional_fields:
            if field not in data or data[field] is None:
                logger.debug(f"Missing {field} for {data['city']}, setting to None")
                data[field] = None

        return data
    except Exception as e:
        logger.error(f"Error preprocessing data for {data.get('city', 'unknown')}: {e}")
        return None

def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback for MQTT connection."""
    if reason_code == 0:
        logger.debug(f"Connected to MQTT broker with code {reason_code}")
        for city in CITIES:
            topic = f"moodcast/sensor/{city}"
            client.subscribe(topic, qos=1)
            logger.debug(f"Subscribed to {topic}")
        client.subscribe("moodcast/city", qos=1)
        logger.debug("Subscribed to moodcast/city")
    else:
        logger.error(f"Failed to connect to MQTT broker with code {reason_code}")

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages."""
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        logger.debug(f"Received message on {topic}: {payload}")

        if topic == "moodcast/city":
            logger.info(f"Received new city: {payload.get('city')}")
            # Handle city changes (to be expanded in Phase 2)
        elif topic.startswith("moodcast/sensor/"):
            city = payload["city"]
            logger.info(f"Processing sensor data for {city}")
            processed_data = preprocess_data(payload)
            if processed_data:
                mood_score = compute_mood_score(processed_data)
                processed_data["mood_score"] = mood_score
                store_sensor_data(processed_data)
                logger.info(f"Stored data for {city} with mood_score {mood_score}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message on {topic}: {e}")
    except Exception as e:
        logger.error(f"Error processing message on {topic}: {e}", exc_info=True)

def main():
    """Main backend loop."""
    client_args = {"client_id": "moodcast_backend"}
    if MQTT_VERSION:
        client_args["callback_api_version"] = MQTT_VERSION
    client = mqtt.Client(**client_args)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
    logger.debug("Starting MQTT loop")
    client.loop_forever()

if __name__ == "__main__":
    logger.debug("Starting main.py")
    main()