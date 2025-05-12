from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
DB_PATH = "moodcast.db"

def get_db_connection():
    """Connect to SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

@app.route('/weather', methods=['GET'])
def get_weather():
    """Query weather and mood data by lat/long."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({"error": "Missing lat or lon parameters"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Find nearest data within 0.1 degrees
        cursor = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        cursor.execute("""
            SELECT city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain,
                   timestamp, source, mood_score
            FROM sensor_data
            WHERE ABS(lat - ?) <= 0.1 AND ABS(lon - ?) <= 0.1
            AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (lat, lon, cutoff))
        sensor_data = cursor.fetchone()

        if not sensor_data:
            conn.close()
            return jsonify({"error": "No recent data found for given lat/lon"}), 404

        # Get quality metrics
        cursor.execute("""
            SELECT completeness, freshness, missing_fields, error
            FROM quality_metrics
            WHERE city = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (sensor_data['city'], cutoff))
        quality_data = cursor.fetchone()

        # Parse missing_fields from string to list
        missing_fields = []
        if quality_data and quality_data['missing_fields']:
            missing_fields = quality_data['missing_fields'].split(',') if ',' in quality_data['missing_fields'] else [quality_data['missing_fields']]

        response = {
            "city": sensor_data['city'],
            "lat": sensor_data['lat'],
            "lon": sensor_data['lon'],
            "weather": {
                "temp": sensor_data['temp'],
                "humidity": sensor_data['humidity'],
                "pressure": sensor_data['pressure'],
                "wind_speed": sensor_data['wind_speed'],
                "clouds": sensor_data['clouds'],
                "rain": sensor_data['rain']
            },
            "mood_score": sensor_data['mood_score'],
            "source": sensor_data['source'],
            "timestamp": sensor_data['timestamp'],
            "quality": {
                "completeness": quality_data['completeness'] if quality_data else None,
                "freshness": quality_data['freshness'] if quality_data else None,
                "missing_fields": missing_fields,
                "error": quality_data['error'] if quality_data else None
            }
        }
        conn.close()
        return jsonify(response), 200
    except sqlite3.Error as e:
        conn.close()
        logger.error(f"Database query error: {e}")
        return jsonify({"error": "Database query failed"}), 500

if __name__ == "__main__":
    logger.info("Starting Flask API")
    app.run(host="0.0.0.0", port=5000, debug=True)