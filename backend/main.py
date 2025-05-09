import paho.mqtt.client as mqtt
from fetch_weather import fetch_weather, fetch_forecast
from database import store_weather_data, store_forecast_data
from mqtt_publisher import publish_weather, publish_forecast, publish_alert
import time
import logging
import json
import threading

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BROKER = "localhost"
PORT = 1883
CITY_TOPIC = "moodcast/city"
DEFAULT_CITY = "Auckland"
current_city = DEFAULT_CITY
current_coords = None
last_fetch = 0
FETCH_INTERVAL = 300  # 5 minutes

def fetch_and_publish(city, coords):
    global last_fetch
    try:
        logger.debug(f"Fetching weather for {city}, coords: {coords}")
        weather_data = fetch_weather(
            city=city if not coords else None,
            lat=coords['lat'] if coords else None,
            lon=coords['lon'] if coords else None
        )
        if weather_data:
            store_weather_data(weather_data, location=weather_data["city"], device_label="MoodCast")
            logger.debug(f"Attempting to publish weather for {weather_data['city']}")
            publish_weather(weather_data)
            logger.info(f"Current weather for {weather_data['city']} stored and published.")
            if weather_data["pressure"] < 1000:
                logger.debug("Low pressure detected, publishing alert")
                publish_alert("Low pressure detected—possible fatigue. Try a calming activity!")
        else:
            logger.error(f"Failed to fetch current weather for {city}.")

        forecast_data = fetch_forecast(
            city=city if not coords else None,
            lat=coords['lat'] if coords else None,
            lon=coords['lon'] if coords else None
        )
        if forecast_data:
            store_forecast_data(forecast_data, location=weather_data["city"] if weather_data else city, device_label="MoodCast")
            logger.debug(f"Attempting to publish forecast for {weather_data['city'] if weather_data else city}")
            publish_forecast(forecast_data)
            logger.info(f"72-hour forecast for {weather_data['city'] if weather_data else city} stored and published.")
        else:
            logger.error(f"Failed to fetch forecast for {city}.")
        last_fetch = time.time()
    except Exception as e:
        logger.error(f"Error in fetch_and_publish: {e}")

def on_connect(client, userdata, flags, rc):
    logger.debug(f"Connected to MQTT broker with code {rc}")
    client.subscribe(CITY_TOPIC)
    # Initial fetch on connect
    fetch_and_publish(current_city, current_coords)

def on_message(client, userdata, msg):
    global current_city, current_coords
    try:
        payload = json.loads(msg.payload.decode())
        if 'city' in payload:
            current_city = payload['city']
            current_coords = None
            logger.debug(f"Received new city: {current_city}")
            fetch_and_publish(current_city, current_coords)
        elif 'lat' in payload and 'lon' in payload:
            current_city = payload.get('city', current_city)
            current_coords = {'lat': payload['lat'], 'lon': payload['lon']}
            logger.debug(f"Received coordinates: {current_coords}")
            fetch_and_publish(current_city, current_coords)
    except Exception as e:
        logger.error(f"Error processing city message: {e}")

def periodic_fetch():
    while True:
        if time.time() - last_fetch >= FETCH_INTERVAL:
            fetch_and_publish(current_city, current_coords)
        time.sleep(60)  # Check every minute to avoid tight loop

def main():
    client = mqtt.Client(client_id="moodcast_backend")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_start()

    # Start periodic fetch in a separate thread
    threading.Thread(target=periodic_fetch, daemon=True).start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()