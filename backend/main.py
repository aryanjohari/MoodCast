import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
from database import insert_sensor_data, insert_quality_metrics, compute_mood_score, update_iot_node

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT settings
BROKER = "localhost"
PORT = 1883
QOS = 1
TOPICS = [("moodcast/sensor/#", QOS), ("moodcast/source/#", QOS)]

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        for topic, qos in TOPICS:
            client.subscribe(topic, qos=qos)
            logger.info(f"Subscribed to {topic}")
    else:
        logger.error(f"Failed to connect to MQTT broker, code: {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        logger.info(f"Received message on {topic}: {payload}")

        if topic.startswith("moodcast/sensor/"):
            city = topic.split("/")[-1]
            data = json.loads(payload)
            
            # Compute mood score
            mood_score = compute_mood_score(data)
            data["mood_score"] = mood_score
            
            # Insert sensor data
            insert_sensor_data(data)
            
            # Compute quality metrics
            required_fields = ["temp", "humidity", "pressure", "wind_speed", "clouds", "rain"]
            missing_fields = [field for field in required_fields if data.get(field) is None]
            completeness = (1 - len(missing_fields) / len(required_fields)) * 100
            freshness = int((datetime.utcnow() - datetime.fromisoformat(data["timestamp"])).total_seconds())
            error = None if not missing_fields else "Missing fields"
            
            # Insert quality metrics
            insert_quality_metrics(city, completeness, freshness, ",".join(missing_fields), error)
            
            # Update IoT node metadata
            pi_id = f"pi_{city.lower()}"
            sensor_id = f"sensor_{city.lower()}"
            update_iot_node(city, pi_id, sensor_id)
            
            # Publish quality metrics
            quality_topic = f"moodcast/quality/{city}"
            quality_payload = json.dumps({
                "city": city,
                "completeness": completeness,
                "freshness": freshness,
                "missing_fields": missing_fields,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
            client.publish(quality_topic, quality_payload, qos=QOS)
            logger.info(f"Published quality metrics for {city} to {quality_topic}")

        elif topic.startswith("moodcast/source/"):
            city = topic.split("/")[-1]
            try:
                # Try parsing as JSON
                source_data = json.loads(payload)
                source = source_data.get("source", payload)
            except json.JSONDecodeError:
                # Fallback to string payload
                source = payload
            logger.info(f"Received source for {city}: {source}")

    except Exception as e:
        logger.error(f"Error processing message on {topic}: {e}")

def main():
    client = mqtt.Client(protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    main()