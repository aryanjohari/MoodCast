import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import paho.mqtt.client as mqtt
import json
import time
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "moodcast.db"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "moodcast/forecast"

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

def get_historical_data(city, lat, lon):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT timestamp, temp, humidity, clouds, rain
            FROM sensor_data
            WHERE city = ? AND ABS(lat - ?) <= 0.1 AND ABS(lon - ?) <= 0.1
            AND timestamp >= datetime('now', '-72 hours')
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn, params=(city, lat, lon))
        conn.close()
        return df
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        return pd.DataFrame()

def predict_weather(city, lat, lon):
    df = get_historical_data(city, lat, lon)
    if len(df) < 864:  # ~72 hours at 5-minute intervals
        logger.warning(f"Insufficient data for {city}: {len(df)} rows")
        return []
    
    # Prepare features: time since start, hour of day
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time_diff'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / 3600
    df['hour'] = df['timestamp'].dt.hour
    features = ['time_diff', 'hour']
    targets = ['temp', 'humidity', 'clouds', 'rain']
    
    predictions = []
    now = datetime.utcnow()
    
    for target in targets:
        X = df[features]
        y = df[target]
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict for next 72 hours (3-hour intervals)
        future_times = [now + timedelta(hours=i) for i in range(3, 73, 3)]
        future_features = pd.DataFrame({
            'time_diff': [(t - df['timestamp'].min()).total_seconds() / 3600 for t in future_times],
            'hour': [t.hour for t in future_times]
        })
        
        preds = model.predict(future_features)
        predictions.append(preds)
    
    # Combine predictions
    forecasts = []
    for i, t in enumerate(future_times):
        weather = {
            'temp': max(predictions[0][i], 0),
            'humidity': min(max(predictions[1][i], 0), 100),
            'clouds': min(max(predictions[2][i], 0), 100),
            'rain': max(predictions[3][i], 0),
            'timestamp': t.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'model_prediction'
        }
        mood_score = min(max((100 - weather['clouds']) * (weather['temp'] / 30), 0), 100)
        weather['mood_score'] = round(mood_score, 1)
        forecasts.append({
            'city': city,
            'lat': lat,
            'lon': lon,
            'weather': weather,
            'timestamp': weather['timestamp'],
            'source': weather['source'],
            'mood_score': weather['mood_score']
        })
    
    logger.debug(f"Generated {len(forecasts)} model predictions for {city}")
    return forecasts

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
            forecasts = predict_weather(city['name'], city['lat'], city['lon'])
            for forecast in forecasts:
                topic = f"{MQTT_TOPIC}/{city['name']}"
                try:
                    client.publish(topic, json.dumps(forecast), qos=1)
                    logger.debug(f"Published model prediction to {topic}")
                except Exception as e:
                    logger.error(f"Error publishing to {topic}: {e}")
        time.sleep(3600)  # Run every hour

if __name__ == "__main__":
    main()