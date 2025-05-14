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

def check_weather_alerts(cursor, city, current_data, source, timestamp):
    """Check for exceptional weather changes and generate alerts."""
    try:
        # Get the previous sensor data for the same city and source
        cursor.execute("""
            SELECT temp, pressure, wind_speed, clouds, rain, timestamp
            FROM sensor_data
            WHERE city = ? AND source = ?
            ORDER BY timestamp DESC LIMIT 1 OFFSET 1
        """, (city, source))
        prev_row = cursor.fetchone()

        if not prev_row:
            return

        prev_temp, prev_pressure, prev_wind, prev_clouds, prev_rain, prev_timestamp = prev_row
        prev_time = datetime.strptime(prev_timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
        current_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
        time_diff_hours = (current_time - prev_time).total_seconds() / 3600

        if time_diff_hours == 0:
            return

        alerts = []
        # Temperature change: ±5°C/hour
        temp_change = abs(current_data['temp'] - prev_temp)
        if temp_change / time_diff_hours >= 5:
            alerts.append({
                'type': 'temperature_change',
                'message': f"Rapid temperature {'drop' if current_data['temp'] < prev_temp else 'rise'}: {temp_change:.1f}°C in {time_diff_hours:.1f} hours",
                'severity': 'warning'
            })

        # Pressure drop: ≥4 hPa in 3 hours
        pressure_change = prev_pressure - current_data['pressure']
        if time_diff_hours <= 3 and pressure_change >= 4:
            alerts.append({
                'type': 'pressure_drop',
                'message': f"Rapid pressure drop: {pressure_change:.1f} hPa in {time_diff_hours:.1f} hours, possible storm",
                'severity': 'critical'
            })

        # Wind speed: ≥15 m/s
        if current_data['wind_speed'] >= 15:
            alerts.append({
                'type': 'high_wind',
                'message': f"High wind speed: {current_data['wind_speed']:.1f} m/s",
                'severity': 'warning'
            })

        # Rain: ≥5 mm/h
        if current_data['rain'] >= 5:
            alerts.append({
                'type': 'heavy_rain',
                'message': f"Heavy rain: {current_data['rain']:.1f} mm/h",
                'severity': 'warning'
            })

        # Clouds: Increase to ≥80% in 1 hour
        cloud_change = current_data['clouds'] - prev_clouds
        if time_diff_hours <= 1 and current_data['clouds'] >= 80 and cloud_change >= 50:
            alerts.append({
                'type': 'sudden_clouds',
                'message': f"Sudden cloud cover increase: {cloud_change:.1f}% to {current_data['clouds']}%",
                'severity': 'warning'
            })

        for alert in alerts:
            cursor.execute("""
                INSERT INTO alerts (city, type, message, timestamp, severity)
                VALUES (?, ?, ?, ?, ?)
            """, (city, alert['type'], alert['message'], timestamp, alert['severity']))

    except Exception as e:
        logger.error(f"Error checking alerts for {city}: {e}")

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
            source = payload.get('source', 'unknown')
            timestamp = payload.get('timestamp', datetime.now(timezone.utc).isoformat())
            mood_score = payload.get('mood_score', calculate_mood_score(weather['temp'], weather['clouds']))

            # Check for alerts
            if source == 'openweathermap':
                check_weather_alerts(cursor, city, weather, source, timestamp)

            cursor.execute("""
                INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                city, lat, lon,
                weather['temp'], weather['humidity'], weather['pressure'],
                weather['wind_speed'], weather['clouds'], weather['rain'],
                timestamp, source, mood_score
            ))

        elif topic.startswith("moodcast/source/"):
            city = topic.split('/')[-1]
            cursor.execute("""
                INSERT INTO quality_metrics (city, completeness, freshness, missing_fields, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                city,
                payload.get('completeness', 100),
                payload.get('freshness', 60),
                ','.join(payload.get('missing_fields', [])),
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
            source = payload.get('source', 'unknown')
            timestamp = payload.get('timestamp', datetime.now(timezone.utc).isoformat())
            mood_score = payload.get('mood_score', calculate_mood_score(weather.get('temp'), weather.get('clouds', 0)))

            # Check for forecast alerts (e.g., high wind in next 48 hours)
            if source == 'openweathermap_forecast':
                check_weather_alerts(cursor, city, weather, source, timestamp)

            cursor.execute("""
                INSERT INTO sensor_data (city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                city, lat, lon,
                weather.get('temp'), weather.get('humidity'), weather.get('pressure'),
                weather.get('wind_speed'), weather.get('clouds', 0), weather.get('rain', 0),
                timestamp, source, mood_score
            ))

        conn.commit()
        logger.debug(f"Stored data for {topic}")

        # Publish alerts to MQTT
        cursor.execute("SELECT city, type, message, timestamp, severity FROM alerts WHERE city = ? ORDER BY timestamp DESC LIMIT 5", (city,))
        for alert in cursor.fetchall():
            alert_topic = f"moodcast/alert/{city}"
            alert_payload = json.dumps({
                'city': alert[0],
                'type': alert[1],
                'message': alert[2],
                'timestamp': alert[3],
                'severity': alert[4]
            })
            client.publish(alert_topic, alert_payload, qos=1)
            logger.debug(f"Published alert to {alert_topic}")

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