import { useState, useEffect } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "./App.css";

// Fix Leaflet marker icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const cities = [
  { name: "Auckland", lat: -36.8485, lon: 174.7633 },
  { name: "Tokyo", lat: 35.6762, lon: 139.6503 },
  { name: "London", lat: 51.5074, lon: -0.1278 },
  { name: "New York", lat: 40.7128, lon: -74.006 },
  { name: "Sydney", lat: -33.8688, lon: 151.2093 },
  { name: "Paris", lat: 48.8566, lon: 2.3522 },
  { name: "Singapore", lat: 1.3521, lon: 103.8198 },
  { name: "Dubai", lat: 25.2048, lon: 55.2708 },
  { name: "Mumbai", lat: 19.076, lon: 72.8777 },
  { name: "Cape Town", lat: -33.9249, lon: 18.4241 },
];

function App() {
  const [selectedCity, setSelectedCity] = useState(cities[0]);
  const [weatherData, setWeatherData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchWeather() {
      setError(null);
      try {
        const response = await axios.get(
          `http://localhost:5000/weather?lat=${selectedCity.lat}&lon=${selectedCity.lon}`
        );
        console.log("API Response:", response.data); // Debug log
        if (response.data && response.data.city) {
          setWeatherData(response.data);
        } else {
          setError("No valid data returned from API");
        }
      } catch (error) {
        console.error("Error fetching weather:", error);
        setError("Failed to fetch weather data");
      }
    }
    fetchWeather();
  }, [selectedCity]);

  // Safely format missing_fields
  const formatMissingFields = (missingFields) => {
    if (Array.isArray(missingFields) && missingFields.length > 0) {
      return missingFields.join(", ");
    }
    return "None";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 to-blue-900 text-white">
      <header className="p-4 text-center">
        <h1
          className="text-4xl font-bold"
          style={{ fontFamily: "Impact, sans-serif" }}
        >
          MoodCast: 9Horsemen Edition
        </h1>
      </header>
      <main className="p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="md:w-1/3">
            <h2 className="text-2xl mb-2">Select City</h2>
            <select
              className="p-2 w-full bg-gray-800 rounded"
              onChange={(e) => {
                const city = cities.find((c) => c.name === e.target.value);
                if (city) setSelectedCity(city);
              }}
              value={selectedCity.name}
            >
              {cities.map((city) => (
                <option key={city.name} value={city.name}>
                  {city.name}
                </option>
              ))}
            </select>
            {error && <p className="mt-4 text-red-500">{error}</p>}
            {weatherData ? (
              <motion.div
                className="mt-4 p-4 bg-gray-800 rounded-lg"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <h3 className="text-xl">
                  {weatherData.city || "Unknown City"}
                </h3>
                <p>Temp: {weatherData.weather?.temp ?? "N/A"}°C</p>
                <p>Humidity: {weatherData.weather?.humidity ?? "N/A"}%</p>
                <p>Pressure: {weatherData.weather?.pressure ?? "N/A"}hPa</p>
                <p>Wind Speed: {weatherData.weather?.wind_speed ?? "N/A"}m/s</p>
                <p>Clouds: {weatherData.weather?.clouds ?? "N/A"}%</p>
                <p>Rain: {weatherData.weather?.rain ?? "N/A"}mm</p>
                <p className="text-lg mt-2">
                  Mood Score: {weatherData.mood_score ?? "N/A"}/100
                </p>
                <p>Source: {weatherData.source ?? "N/A"}</p>
                <p className="mt-2">Quality Metrics:</p>
                <p>
                  Completeness: {weatherData.quality?.completeness ?? "N/A"}%
                </p>
                <p>Freshness: {weatherData.quality?.freshness ?? "N/A"}s</p>
                <p>
                  Missing Fields:{" "}
                  {formatMissingFields(weatherData.quality?.missing_fields)}
                </p>
                {weatherData.quality?.error && (
                  <p>Error: {weatherData.quality.error}</p>
                )}
              </motion.div>
            ) : (
              <p className="mt-4">Loading data...</p>
            )}
          </div>
          <div className="md:w-2/3 h-96">
            <MapContainer
              center={[selectedCity.lat, selectedCity.lon]}
              zoom={10}
              style={{ height: "100%" }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              {cities.map((city) => (
                <Marker
                  key={city.name}
                  position={[city.lat, city.lon]}
                  eventHandlers={{
                    click: () => setSelectedCity(city),
                  }}
                >
                  <Popup>{city.name}</Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
