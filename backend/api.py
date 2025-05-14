import sqlite3
import json
import logging
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DB_PATH = "moodcast.db"

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

@app.route('/weather', methods=['GET'])
def get_weather():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({'error': 'Missing lat or lon'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score
            FROM sensor_data
            WHERE ABS(lat - ?) <= 0.01 AND ABS(lon - ?) <= 0.01
            AND source IN ('openweathermap', 'openmeteo')
            ORDER BY timestamp DESC, source = 'openweathermap' DESC LIMIT 1
        """, (lat, lon))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'No weather data found'}), 404

        cursor.execute("""
            SELECT completeness, freshness, missing_fields, error
            FROM quality_metrics
            WHERE city = ? ORDER BY timestamp DESC LIMIT 1
        """, (row[0],))
        quality_row = cursor.fetchone()

        cursor.execute("""
            SELECT pi_id, sensor_id
            FROM iot_nodes
            WHERE city = ?
        """, (row[0],))
        iot_row = cursor.fetchone()

        response = {
            'city': row[0],
            'lat': row[1],
            'lon': row[2],
            'weather': {
                'temp': row[3],
                'humidity': row[4],
                'pressure': row[5],
                'wind_speed': row[6],
                'clouds': row[7],
                'rain': row[8]
            },
            'timestamp': row[9],
            'source': row[10],
            'mood_score': row[11],
            'quality': {
                'completeness': quality_row[0] if quality_row else None,
                'freshness': quality_row[1] if quality_row else None,
                'missing_fields': quality_row[2].split(',') if quality_row and quality_row[2] else [],
                'error': quality_row[3] if quality_row else None
            },
            'iot_node': {
                'pi_id': iot_row[0] if iot_row else None,
                'sensor_id': iot_row[1] if iot_row else None
            }
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/forecast', methods=['GET'])
def get_forecast():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({'error': 'Missing lat or lon'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score
            FROM sensor_data
            WHERE ABS(lat - ?) <= 0.01 AND ABS(lon - ?) <= 0.01 AND source = 'openweathermap_forecast'
            ORDER BY timestamp ASC
        """, (lat, lon))
        api_rows = cursor.fetchall()

        cursor.execute("""
            SELECT city, lat, lon, temp, humidity, pressure, wind_speed, clouds, rain, timestamp, source, mood_score
            FROM sensor_data
            WHERE ABS(lat - ?) <= 0.01 AND ABS(lon - ?) <= 0.01 AND source = 'model_prediction'
            ORDER BY timestamp ASC
        """, (lat, lon))
        model_rows = cursor.fetchall()

        api_forecasts = [{
            'city': row[0],
            'lat': row[1],
            'lon': row[2],
            'weather': {
                'temp': row[3],
                'humidity': row[4],
                'pressure': row[5],
                'wind_speed': row[6],
                'clouds': row[7],
                'rain': row[8]
            },
            'timestamp': row[9],
            'source': row[10],
            'mood_score': row[11]
        } for row in api_rows]

        model_forecasts = [{
            'city': row[0],
            'lat': row[1],
            'lon': row[2],
            'weather': {
                'temp': row[3],
                'humidity': row[4],
                'pressure': row[5],
                'wind_speed': row[6],
                'clouds': row[7],
                'rain': row[8]
            },
            'timestamp': row[9],
            'source': row[10],
            'mood_score': row[11]
        } for row in model_rows]

        return jsonify({'api': api_forecasts, 'model': model_forecasts})
    except Exception as e:
        logger.error(f"Error fetching forecast: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/status', methods=['GET'])
def get_status():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'Missing city parameter'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pi_id, sensor_id, last_seen, lat, lon
            FROM iot_nodes
            WHERE city = ?
        """, (city,))
        node_row = cursor.fetchone()
        if not node_row:
            return jsonify({'error': 'No IoT node found for city'}), 404

        last_seen = None
        if node_row[2]:
            try:
                last_seen = datetime.strptime(node_row[2], '%Y-%m-%dT%H:%M:%S.%f%z')
            except ValueError as e:
                logger.error(f"Failed to parse last_seen timestamp '{node_row[2]}': {e}")
                return jsonify({'error': 'Invalid timestamp format'}), 500

        status = 'Online' if last_seen and (datetime.now(timezone.utc) - last_seen).total_seconds() < 300 else 'Offline'
        freshness = (datetime.now(timezone.utc) - last_seen).total_seconds() if last_seen else None

        response = {
            'city': city,
            'status': status,
            'freshness': round(freshness, 1) if freshness is not None else None,
            'pi_id': node_row[0],
            'sensor_id': node_row[1]
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/nodes', methods=['GET'])
def get_nodes():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT city, pi_id, sensor_id, last_seen, lat, lon
            FROM iot_nodes
        """)
        rows = cursor.fetchall()

        nodes = []
        for row in rows:
            last_seen = None
            if row[3]:
                try:
                    last_seen = datetime.strptime(row[3], '%Y-%m-%dT%H:%M:%S.%f%z')
                except ValueError as e:
                    logger.error(f"Failed to parse last_seen timestamp '{row[3]}': {e}")
                    continue
            status = 'Online' if last_seen and (datetime.now(timezone.utc) - last_seen).total_seconds() < 300 else 'Offline'
            freshness = (datetime.now(timezone.utc) - last_seen).total_seconds() if last_seen else None
            nodes.append({
                'city': row[0],
                'pi_id': row[1],
                'sensor_id': row[2],
                'status': status,
                'freshness': round(freshness, 1) if freshness is not None else None,
                'lat': row[4] if row[4] is not None else CITY_COORDS.get(row[0], (0, 0))[0],
                'lon': row[5] if row[5] is not None else CITY_COORDS.get(row[0], (0, 0))[1],
                'logs': []
            })
        return jsonify(nodes)
    except Exception as e:
        logger.error(f"Error fetching nodes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/alerts', methods=['GET'])
def get_alerts():
    city = request.args.get('city')
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor()
        if city:
            cursor.execute("""
                SELECT city, type, message, timestamp, severity
                FROM alerts
                WHERE city = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (city, (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()))
        else:
            cursor.execute("""
                SELECT city, type, message, timestamp, severity
                FROM alerts
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, ((datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),))
        
        rows = cursor.fetchall()
        alerts = [{
            'city': row[0],
            'type': row[1],
            'message': row[2],
            'timestamp': row[3],
            'severity': row[4]
        } for row in rows]
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)