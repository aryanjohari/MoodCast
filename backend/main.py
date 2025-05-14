import paho.mqtt.client as mqtt
import sqlite3
import json
import logging
from datetime import datetime, timedelta, timezone
import database

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "moodcast.db"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPICS = ["moodcast/sensor/#", "moodcast/source/#", "moodcast/quality/#", "moodcast/forecast/#"]

# City coordinates
CITY_COORDS = {
    'Auckland': (-36.8485, 174.7633),
    'Tokyo': (35.6762, 139.6503),
    'London': (51.5074, -0.1278),
    'New York': (40.7128, -74.006),
    'Sydney': (-33.8688, 151.2093),
    'Paris': (48.8566, 2.3522),
    'Singapore': (1.3521, 103.8198),
    'Dubai': (25.2048, 55.2708),
    'Mumbai': (19.076, 72.8777),
    'Cape Town': (-33.9249, 18.4241)
}

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def calculate_mood_score(temp, clouds):
    """Compute mood_score: (100 - clouds) * (temp / 30), clamped 0-100."""
    try:
        score = (100 - clouds) * (temp / 30)
        return min(max(round(score, 1), 0), 100)
    except (TypeError, ZeroDivisionError):
        return 50.0

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code.is_failure:
        logger.error(f"Failed to connect to MQTT broker with code {reason_code}")
    else:
        logger.info("Connected to MQTT broker")
        for topic in MQTT_TOPICS:
            client.subscribe(topic, qos=1)
            logger.info(f"Subscribed to {topic}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        logger.debug(f"Received message on {topic}: {payload}")

        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return
        
        cursor = conn.cursor()

        if topic.startswith("moodcast/sensor/"):
            city = topic.split('/')[-1]
            weather = {
                'temp': payload.get('temp'),
                'humidity': payload.get('humidity'),
                'pressure': payload.get('pressure'),
                'wind_speed': payload.get('wind_speed'),
                'clouds': payload.get('clouds', 0),
                'rain': payload.get('rain', 0)
            }
            lat = payload.get('lat', CITY_COORDS.get(city, (0, 0))[0])
            lon = payload.get('lon', CITY_COORDS.get(city, (0, 0))[1])
            mood_score = payload.get('mood_score', calculate_mood_score(weather['temp'], weather['clouds']))
            cursor.execute("""
                INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                city, lat, lon,
                weather['temp'], weather['humidity'], weather['pressure'],
                weather['wind_speed'], weather['clouds'], weather['rain'],
                payload.get('timestamp', datetime.now(timezone.utc).isoformat()),
                payload.get('source', 'unknown'), mood_score
            ))

        elif topic.startswith("moodcast/source/"):
            city = topic.split('/')[-1]
            cursor.execute("""
                INSERT INTO quality_metrics (city, completeness, freshness, missing_fields, error, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                city,
                payload.get('completeness', 100),
                payload.get('freshness', 60),
                ','.join(payload.get('missing_fields', [])),
                payload.get('error'),
                payload.get('timestamp', datetime.now(timezone.utc).isoformat())
            ))

        elif topic.startswith("moodcast/quality/"):
            city = topic.split('/')[-1]
            lat, lon = CITY_COORDS.get(city, (0, 0))
            cursor.execute("""
                INSERT OR REPLACE INTO iot_nodes (city, pi_id, sensor_id, last_seen, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                city, payload.get('pi_id'), payload.get('sensor_id'),
                payload.get('last_seen', datetime.now(timezone.utc).isoformat()),
                lat, lon
            ))

        elif topic.startswith("moodcast/forecast/"):
            city = topic.split('/')[-1]
            weather = payload.get('weather', {})
            lat = payload.get('lat', CITY_COORDS.get(city, (0, 0))[0])
            lon = payload.get('lon', CITY_COORDS.get(city, (0, 0))[1])
            mood_score = payload.get('mood_score', calculate_mood_score(weather.get('temp'), weather.get('clouds', 0)))
            cursor.execute("""
                INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                city, lat, lon,
                weather.get('temp'), weather.get('humidity'), weather.get('pressure'),
                weather.get('wind_speed'), weather.get('clouds', 0), weather.get('rain', 0),
                payload.get('timestamp', datetime.now(timezone.utc).isoformat()),
                payload.get('source', 'unknown'), mood_score
            ))

        conn.commit()
        logger.debug(f"Stored data for {topic}")
    except Exception as e:
        logger.error(f"Error processing message on {topic}: {e}")
    finally:
        if conn:
            conn.close()

def main():
    database.init_db()  # Ensure database schema
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_forever()
    except Exception as e:
        logger.error(f"Error in MQTT client: {e}")

if __name__ == "__main__":
    main()