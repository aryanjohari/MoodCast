import { useState, useEffect } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
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

// Component to recenter map
function MapRecenter({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// Weather animation component
function WeatherAnimation({ condition }) {
  const baseStyle = { marginRight: "8px", display: "inline-block" };
  if (condition === "sunny") {
    return (
      <motion.span
        style={{ ...baseStyle, fontSize: "24px" }}
        animate={{ rotate: [0, 360], scale: [1, 1.1, 1] }}
        transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
      >
        ☀️
      </motion.span>
    );
  } else if (condition === "cloudy") {
    return (
      <motion.span
        style={{ ...baseStyle, fontSize: "24px" }}
        animate={{ x: [-5, 5, -5], opacity: [0.8, 1, 0.8] }}
        transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
      >
        ☁️
      </motion.span>
    );
  } else if (condition === "rainy") {
    return (
      <motion.span
        style={{ ...baseStyle, fontSize: "24px" }}
        animate={{ y: [0, 5, 0], opacity: [1, 0.7, 1] }}
        transition={{ repeat: Infinity, duration: 1, ease: "easeInOut" }}
      >
        🌧️
      </motion.span>
    );
  }
  return null;
}

function App() {
  const [selectedCity, setSelectedCity] = useState(cities[0]);
  const [weatherData, setWeatherData] = useState(null);
  const [forecastData, setForecastData] = useState([]);
  const [statusData, setStatusData] = useState(null);
  const [networkData, setNetworkData] = useState([]);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("weather");

  useEffect(() => {
    async function fetchData() {
      setError(null);
      try {
        // Fetch current weather
        const weatherResponse = await axios.get(
          `http://localhost:5000/weather?lat=${selectedCity.lat}&lon=${selectedCity.lon}`
        );
        console.log("Weather API Response:", weatherResponse.data);
        if (weatherResponse.data && weatherResponse.data.city) {
          setWeatherData(weatherResponse.data);
        } else {
          setError("No valid weather data returned");
        }

        // Fetch 72-hour forecast
        const forecastResponse = await axios.get(
          `http://localhost:5000/forecast?lat=${selectedCity.lat}&lon=${selectedCity.lon}`
        );
        console.log("Forecast API Response:", forecastResponse.data);
        setForecastData(forecastResponse.data || []);

        // Fetch IoT status for selected city
        const statusResponse = await axios.get(
          `http://localhost:5000/status?city=${selectedCity.name}`
        );
        console.log("Status API Response:", statusResponse.data);
        setStatusData(statusResponse.data || null);

        // Fetch IoT network data for all cities
        const networkResponses = await Promise.all(
          cities.map((city) =>
            axios.get(`http://localhost:5000/status?city=${city.name}`)
          )
        );
        console.log(
          "Network API Responses:",
          networkResponses.map((res) => res.data)
        );
        setNetworkData(networkResponses.map((res) => res.data));
      } catch (error) {
        console.error("Error fetching data:", error);
        setError("Failed to fetch data");
      }
    }
    fetchData();
  }, [selectedCity]);

  // Determine weather condition
  const getWeatherCondition = (weather) => {
    if (!weather) return "unknown";
    if (weather.rain && weather.rain > 0) return "rainy";
    if (weather.clouds && weather.clouds > 50) return "cloudy";
    return "sunny";
  };

  // Safely format missing_fields
  const formatMissingFields = (missingFields) => {
    if (Array.isArray(missingFields) && missingFields.length > 0) {
      return missingFields.join(", ");
    }
    return "None";
  };

  return (
    <div className="min-h-screen text-gray-800 relative">
      {/* Map as background */}
      <div className="fixed inset-0 z-[-10]">
        <MapContainer
          center={[selectedCity.lat, selectedCity.lon]}
          zoom={4}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            url="https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png"
            attribution='© <a href="https://stadiamaps.com/">Stadia Maps</a>, © <a href="https://openmaptiles.org/">OpenMapTiles</a>'
          />
          <MapRecenter center={[selectedCity.lat, selectedCity.lon]} zoom={4} />
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

      {/* Main content */}
      <div className="relative z-10 container mx-auto p-6">
        <header className="mb-6 text-center">
          <h1 className="text-4xl font-bold font-montserrat">MoodCast</h1>
        </header>

        {/* Tabs */}
        <div className="mb-6 flex justify-center space-x-4">
          <button
            className={`px-4 py-2 rounded-lg font-montserrat ${
              activeTab === "weather"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-800"
            }`}
            onClick={() => setActiveTab("weather")}
          >
            Weather
          </button>
          <button
            className={`px-4 py-2 rounded-lg font-montserrat ${
              activeTab === "network"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-800"
            }`}
            onClick={() => setActiveTab("network")}
          >
            IoT Network
          </button>
        </div>

        {activeTab === "weather" && (
          <>
            <div className="mb-6">
              <h2 className="text-xl font-montserrat mb-2">Select City</h2>
              <select
                className="p-3 w-full bg-white rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            </div>

            {error && <p className="text-red-600 mb-4">{error}</p>}

            {weatherData && (
              <motion.div
                className="mb-6 p-6 bg-white rounded-xl shadow-lg"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              >
                <h3 className="text-2xl font-montserrat mb-2 flex items-center">
                  <WeatherAnimation
                    condition={getWeatherCondition(weatherData.weather)}
                  />
                  {weatherData.city}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <p>Temp: {weatherData.weather?.temp ?? "N/A"}°C</p>
                  <p>Humidity: {weatherData.weather?.humidity ?? "N/A"}%</p>
                  <p>Pressure: {weatherData.weather?.pressure ?? "N/A"}hPa</p>
                  <p>
                    Wind Speed: {weatherData.weather?.wind_speed ?? "N/A"}m/s
                  </p>
                  <p>Clouds: {weatherData.weather?.clouds ?? "N/A"}%</p>
                  <p>Rain: {weatherData.weather?.rain ?? "N/A"}mm</p>
                </div>
                <p className="text-lg mt-4">
                  Mood Score: {weatherData.mood_score ?? "N/A"}/100
                </p>
                <p>Source: {weatherData.source ?? "N/A"}</p>
                <p className="mt-2 font-semibold">Quality Metrics:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                </div>
                <p className="mt-2 font-semibold">IoT Node:</p>
                <p>Pi ID: {weatherData.iot_node?.pi_id ?? "N/A"}</p>
                <p>Sensor ID: {weatherData.iot_node?.sensor_id ?? "N/A"}</p>
              </motion.div>
            )}

            {statusData && (
              <motion.div
                className="mb-6 p-6 bg-white rounded-xl shadow-lg"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              >
                <h3 className="text-xl font-montserrat mb-2">
                  IoT Node Status
                </h3>
                <p>City: {statusData.city}</p>
                <p>
                  Status:{" "}
                  <span
                    className={
                      statusData.status === "Online"
                        ? "text-green-600"
                        : "text-red-600"
                    }
                  >
                    {statusData.status}
                  </span>
                </p>
                <p>Data Freshness: {statusData.freshness ?? "N/A"}s</p>
                <p>Pi ID: {statusData.pi_id ?? "N/A"}</p>
                <p>Sensor ID: {statusData.sensor_id ?? "N/A"}</p>
              </motion.div>
            )}

            {forecastData.length > 0 && (
              <motion.div
                className="p-6 bg-white rounded-xl shadow-lg"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              >
                <h3 className="text-xl font-montserrat mb-4">
                  72-Hour Forecast
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <AnimatePresence>
                    {forecastData.map((forecast, index) => (
                      <motion.div
                        key={index}
                        className="p-4 bg-gray-50 rounded-lg shadow-sm"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{
                          duration: 0.3,
                          ease: "easeOut",
                          delay: index * 0.1,
                        }}
                      >
                        <p className="font-semibold">
                          {new Date(forecast.timestamp).toLocaleString()}
                        </p>
                        <p>Temp: {forecast.weather.temp ?? "N/A"}°C</p>
                        <p>Rain: {forecast.weather.rain ?? "N/A"}mm</p>
                        <p>Clouds: {forecast.weather.clouds ?? "N/A"}%</p>
                        <WeatherAnimation
                          condition={getWeatherCondition(forecast.weather)}
                        />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </>
        )}

        {activeTab === "network" && (
          <motion.div
            className="p-6 bg-white rounded-xl shadow-lg"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            <h3 className="text-xl font-montserrat mb-4">
              IoT Network Architecture
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-3 font-montserrat">City</th>
                    <th className="p-3 font-montserrat">Pi ID</th>
                    <th className="p-3 font-montserrat">Sensor ID</th>
                    <th className="p-3 font-montserrat">Status</th>
                    <th className="p-3 font-montserrat">Freshness</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {networkData.map((node, index) => (
                      <motion.tr
                        key={node.city}
                        className="border-b"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                      >
                        <td className="p-3">{node.city}</td>
                        <td className="p-3">{node.pi_id ?? "N/A"}</td>
                        <td className="p-3">{node.sensor_id ?? "N/A"}</td>
                        <td className="p-3">
                          <span
                            className={
                              node.status === "Online"
                                ? "text-green-600"
                                : "text-red-600"
                            }
                          >
                            {node.status}
                          </span>
                        </td>
                        <td className="p-3">{node.freshness ?? "N/A"}s</td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default App;
