import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime, timedelta
import sqlite3
from database import store_sensor_data, compute_mood_score, DB_PATH
from fetch_weather import CITIES as CITY_CONFIG  # Import CITIES from fetch_weather

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
# Use CITY_CONFIG keys (display names) for subscriptions
CITIES = list(CITY_CONFIG.keys())  # ["Auckland", "Tokyo", ...]
QUALITY_THRESHOLD_COMPLETENESS = 80.0
QUALITY_THRESHOLD_FRESHNESS = 300
MESSAGE_CACHE = set()

def preprocess_data(data):
    """Preprocess sensor data (filter outliers, handle missing fields)."""
    try:
        required = ["city", "lat", "lon", "temp", "timestamp", "source"]
        if not all(key in data for key in required):
            missing = [key for key in required if key not in data]
            logger.error(f"Missing required fields {missing} for {data.get('city', 'unknown')}")
            return None

        temp = data.get("temp")
        if temp is None or not (-50 <= temp <= 50):
            logger.warning(f"Invalid temperature {temp} for {data['city']}")
            return None

        optional_fields = ["humidity", "pressure", "wind_speed", "clouds", "rain"]
        for field in optional_fields:
            if field not in data or data[field] is None:
                logger.debug(f"Missing {field} for {data['city']}, setting to None")
                data[field] = None

        return data
    except Exception as e:
        logger.error(f"Error preprocessing data for {data.get('city', 'unknown')}: {e}")
        return None

def select_best_source(city):
    """Select best source based on recent quality metrics."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            cursor.execute("""
                SELECT source, AVG(completeness) as avg_completeness
                FROM quality_metrics
                WHERE city = ? AND timestamp >= ?
                GROUP BY source
            """, (city, cutoff))
            results = cursor.fetchall()
            if not results:
                return None
            best_source = max(results, key=lambda x: x[1])[0]
            logger.debug(f"Selected source for {city}: {best_source} (avg completeness {results[0][1]:.1f}%)")
            return best_source
    except sqlite3.Error as e:
        logger.error(f"Error selecting source for {city}: {e}")
        return None

def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback for MQTT connection."""
    if reason_code == 0:
        logger.debug(f"Connected to MQTT broker with code {reason_code}")
        for city in CITIES:
            topic = f"moodcast/sensor/{CITY_CONFIG[city]['topic']}"
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
            return

        if topic.startswith("moodcast/sensor/"):
            city = payload["city"]
            if city not in CITY_CONFIG:
                logger.error(f"Invalid city in payload: {city}")
                return
            message_key = f"{city}_{payload['source']}_{payload['timestamp']}"
            if message_key in MESSAGE_CACHE:
                logger.debug(f"Skipping duplicate message for {city}")
                return
            MESSAGE_CACHE.add(message_key)
            if len(MESSAGE_CACHE) > 1000:
                MESSAGE_CACHE.clear()

            logger.info(f"Processing sensor data for {city}")
            processed_data = preprocess_data(payload)
            if processed_data:
                mood_score = compute_mood_score(processed_data)
                processed_data["mood_score"] = mood_score
                store_sensor_data(processed_data)
                logger.info(f"Stored data for {city} with mood_score {mood_score}")

                # Publish quality metrics
                optional_fields = ["temp", "humidity", "pressure", "wind_speed", "clouds", "rain"]
                completeness = len([k for k in optional_fields if processed_data.get(k) is not None]) / len(optional_fields) * 100
                freshness = (datetime.utcnow() - datetime.fromisoformat(processed_data["timestamp"])).seconds
                quality = {
                    "city": city,
                    "completeness": completeness,
                    "freshness": freshness,
                    "missing_fields": [k for k in optional_fields if processed_data.get(k) is None]
                }
                if completeness < QUALITY_THRESHOLD_COMPLETENESS:
                    logger.warning(f"Low completeness for {city}: {completeness}%")
                if freshness > QUALITY_THRESHOLD_FRESHNESS:
                    logger.warning(f"Stale data for {city}: {freshness}s")
                topic_suffix = CITY_CONFIG[city]["topic"]
                client.publish(f"moodcast/quality/{topic_suffix}", json.dumps(quality), qos=1)
                logger.debug(f"Published quality metrics to moodcast/quality/{topic_suffix}")

                # Source selection
                best_source = select_best_source(city)
                if best_source:
                    source_payload = {"city": city, "source": best_source}
                    client.publish(f"moodcast/source/{topic_suffix}", json.dumps(source_payload), qos=1)
                    logger.debug(f"Published source selection to moodcast/source/{topic_suffix}: {best_source}")

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
    logger.info("Starting MQTT loop")
    client.loop_forever()

if __name__ == "__main__":
    logger.info("Starting main.py")
    main()