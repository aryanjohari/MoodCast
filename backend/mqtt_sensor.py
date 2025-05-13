import paho.mqtt.client as mqtt
import requests
import json
import time
import logging
import sys
from datetime import datetime
from fetch_weather import fetch_openweathermap, fetch_openmeteo

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT settings
BROKER = "localhost"
PORT = 1883
QOS = 1

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to MQTT broker for {userdata['city']}")
    else:
        logger.error(f"Failed to connect to MQTT broker for {userdata['city']}, code: {rc}")
        sys.exit(1)

def on_publish(client, userdata, mid):
    logger.debug(f"Successfully published message ID {mid} for {userdata['city']}")

def publish_weather(client, city, data, source):
    topic = f"moodcast/sensor/{city}"
    payload = json.dumps({
        "city": city,
        "lat": data["lat"],
        "lon": data["lon"],
        "temp": data.get("temp"),
        "humidity": data.get("humidity"),
        "pressure": data.get("pressure"),
        "wind_speed": data.get("wind_speed"),
        "clouds": data.get("clouds"),
        "rain": data.get("rain"),
        "timestamp": datetime.utcnow().isoformat(),
        "source": source
    })
    try:
        result = client.publish(topic, payload, qos=QOS)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(f"Failed to publish weather data for {city}, code: {result.rc}")
    except Exception as e:
        logger.error(f"Error publishing weather data for {city}: {e}")

def main():
    logger.debug("Starting mqtt_sensor.py")
    
    if len(sys.argv) != 2:
        logger.error("Usage: python mqtt_sensor.py <city>")
        sys.exit(1)
    
    city = sys.argv[1]
    logger.debug(f"Received city argument: {city}")
    
    pi_id = f"pi_{city.lower()}"
    sensor_id = f"sensor_{city.lower()}"
    
    # MQTT client setup
    try:
        client = mqtt.Client(client_id=sensor_id, userdata={"city": city}, protocol=mqtt.MQTTv5)
        client.on_connect = on_connect
        client.on_publish = on_publish
        logger.debug(f"Attempting to connect to MQTT broker at {BROKER}:{PORT}")
        client.connect(BROKER, PORT, keepalive=60)
    except Exception as e:
        logger.error(f"Failed to initialize or connect MQTT client: {e}")
        sys.exit(1)
    
    # City coordinates
    cities = {
        "Auckland": {"lat": -36.8485, "lon": 174.7633},
        "Tokyo": {"lat": 35.6762, "lon": 139.6503},
        "London": {"lat": 51.5074, "lon": -0.1278},
        "New York": {"lat": 40.7128, "lon": -74.0060},
        "Sydney": {"lat": -33.8688, "lon": 151.2093},
        "Paris": {"lat": 48.8566, "lon": 2.3522},
        "Singapore": {"lat": 1.3521, "lon": 103.8198},
        "Dubai": {"lat": 25.2048, "lon": 55.2708},
        "Mumbai": {"lat": 19.0760, "lon": 72.8777},
        "Cape Town": {"lat": -33.9249, "lon": 18.4241}
    }
    
    if city not in cities:
        logger.error(f"City {city} not supported. Supported cities: {list(cities.keys())}")
        sys.exit(1)
    
    lat, lon = cities[city]["lat"], cities[city]["lon"]
    logger.debug(f"Using coordinates for {city}: lat={lat}, lon={lon}")
    
    try:
        client.loop_start()
        logger.debug(f"Started MQTT loop for {city}")
    except Exception as e:
        logger.error(f"Failed to start MQTT loop: {e}")
        sys.exit(1)
    
    while True:
        try:
            logger.debug(f"Fetching weather data for {city}")
            # Try OpenWeatherMap
            data = fetch_openweathermap(lat, lon)
            source = "openweathermap"
            if data:
                publish_weather(client, city, data, source)
            else:
                # Fallback to Open-Meteo
                data = fetch_openmeteo(lat, lon)
                source = "openmeteo"
                if data:
                    publish_weather(client, city, data, source)
                else:
                    logger.warning(f"No data available for {city}")
            
            # Publish source selection as JSON
            source_payload = json.dumps({"source": source})
            try:
                client.publish(f"moodcast/source/{city}", source_payload, qos=QOS)
                logger.info(f"Published source {source} for {city} to moodcast/source/{city}")
            except Exception as e:
                logger.error(f"Error publishing source for {city}: {e}")
            
        except Exception as e:
            logger.error(f"Error fetching/publishing data for {city}: {e}")
        
        time.sleep(60)  # Fetch every 60 seconds

if __name__ == "__main__":
    main()