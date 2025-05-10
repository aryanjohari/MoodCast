import { useState, useEffect, useRef } from "react";
import mqtt from "mqtt";
import axios from "axios";
import { WiDaySunny, WiCloudy, WiRain, WiThunderstorm } from "react-icons/wi";
import Chart from "chart.js/auto";
import "./App.css";

function App() {
  const [weather, setWeather] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [moodSuggestion, setMoodSuggestion] = useState(null);
  const [selectedCity, setSelectedCity] = useState({ name: "Auckland" });
  const [coordinates, setCoordinates] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const mqttClient = useRef(null);
  const publishTimeout = useRef(null);
  const lastPublished = useRef(null);
  const isMqttInitialized = useRef(false); // Track MQTT init

  // Curated list of cities
  const cities = [
    { name: "Auckland" },
    { name: "London" },
    { name: "New York" },
    { name: "Tokyo" },
    { name: "Sydney" },
    { name: "Paris" },
    { name: "Berlin" },
    { name: "Singapore" },
    { name: "Toronto" },
    { name: "Dubai" },
  ];

  // MQTT Setup
  useEffect(() => {
    if (isMqttInitialized.current) {
      console.log("MQTT: Already initialized, skipping");
      return;
    }

    mqttClient.current = mqtt.connect("ws://localhost:8083", {
      clientId: "moodcast_frontend_" + Math.random().toString(16).slice(3),
      protocolVersion: 4,
    });

    mqttClient.current.on("connect", () => {
      console.log("MQTT: Connected to broker");
      mqttClient.current.subscribe("moodcast/weather", (err) => {
        if (err) console.error("MQTT: Subscribe error (weather)", err);
        else console.log("MQTT: Subscribed to moodcast/weather");
      });
      mqttClient.current.subscribe("moodcast/forecast", (err) => {
        if (err) console.error("MQTT: Subscribe error (forecast)", err);
        else console.log("MQTT: Subscribed to moodcast/forecast");
      });
      mqttClient.current.subscribe("moodcast/alerts", (err) => {
        if (err) console.error("MQTT: Subscribe error (alerts)", err);
        else console.log("MQTT: Subscribed to moodcast/alerts");
      });
      // Publish default city on connect
      const payload = { city: selectedCity.name };
      console.log("MQTT: Publishing initial city:", payload);
      mqttClient.current.publish("moodcast/city", JSON.stringify(payload));
      lastPublished.current = JSON.stringify(payload);
    });

    mqttClient.current.on("message", (topic, message) => {
      console.log(`MQTT: Received message on ${topic}`);
      try {
        const data = JSON.parse(message.toString());
        console.log(`MQTT: Parsed data:`, data);
        if (topic === "moodcast/weather") {
          setWeather(data);
          updateMoodSuggestion(data);
          setError(null);
        } else if (topic === "moodcast/forecast") {
          setForecast(data);
          updateChart(data);
          setError(null);
        } else if (topic === "moodcast/alerts") {
          setAlerts((prev) => [...prev, data.message].slice(-3));
          setError(null);
        }
      } catch (error) {
        console.error(`MQTT: Error parsing message on ${topic}:`, error);
        setError("Failed to process weather data. Please try again.");
      }
    });

    mqttClient.current.on("error", (err) => {
      console.error("MQTT: Connection error:", err);
      setError(
        "Failed to connect to weather service. Please check your connection."
      );
    });

    mqttClient.current.on("close", () => {
      console.log("MQTT: Connection closed");
    });

    isMqttInitialized.current = true;

    // Timeout for loading error
    const timeout = setTimeout(() => {
      if (!weather) {
        setError(
          "Unable to load weather data. Please select a city or try again."
        );
      }
    }, 10000);

    return () => {
      clearTimeout(timeout);
      if (publishTimeout.current) clearTimeout(publishTimeout.current);
      if (mqttClient.current) {
        mqttClient.current.end(true, () => {
          console.log("MQTT: Client disconnected");
        });
      }
      if (chartInstance.current) chartInstance.current.destroy();
      isMqttInitialized.current = false; // Reset for remount
    };
  }, []); // Empty dependency array

  // Initial geolocation
  useEffect(() => {
    getCurrentLocation();
  }, []);

  // Publish city changes with debounce
  useEffect(() => {
    if (mqttClient.current && selectedCity.name) {
      console.log("useEffect: selectedCity.name:", selectedCity.name);
      if (publishTimeout.current) clearTimeout(publishTimeout.current);
      publishTimeout.current = setTimeout(() => {
        const payload = coordinates
          ? {
              city: selectedCity.name,
              lat: coordinates.lat,
              lon: coordinates.lon,
            }
          : { city: selectedCity.name };
        const payloadStr = JSON.stringify(payload);
        if (payloadStr !== lastPublished.current) {
          console.log("MQTT: Publishing to moodcast/city:", payload);
          mqttClient.current.publish("moodcast/city", payloadStr);
          lastPublished.current = payloadStr;
        } else {
          console.log("MQTT: Skipping publish, payload unchanged:", payload);
        }
      }, 500); // Debounce by 500ms
    }
  }, [selectedCity.name]); // Depend only on selectedCity.name

  // Geolocation
  const getCurrentLocation = async () => {
    setError(null);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          const newCoords = { lat: latitude, lon: longitude };
          console.log("Geolocation: New coordinates:", newCoords);
          setCoordinates(newCoords);
          try {
            const response = await axios.get(
              `https://api.openweathermap.org/geo/1.0/reverse?lat=${latitude}&lon=${longitude}&limit=1&appid=${
                import.meta.env.VITE_OPENWEATHERMAP_API_KEY
              }`
            );
            const city = response.data[0]?.name || "Auckland";
            console.log(`Geolocation: Resolved city: ${city}`);
            if (city !== selectedCity.name) {
              setSelectedCity({ name: city }); // Only update if different
            }
          } catch (error) {
            console.error("Geolocation: API error:", error);
            if (selectedCity.name !== "Auckland") {
              setSelectedCity({ name: "Auckland" });
            }
            setCoordinates(null);
            setError("Failed to resolve location. Using default city.");
          }
        },
        (error) => {
          console.error("Geolocation: Denied:", error);
          if (selectedCity.name !== "Auckland") {
            setSelectedCity({ name: "Auckland" });
          }
          setCoordinates(null);
          setError("Geolocation denied. Using default city.");
        }
      );
    } else {
      console.warn("Geolocation: Not supported");
      if (selectedCity.name !== "Auckland") {
        setSelectedCity({ name: "Auckland" });
      }
      setCoordinates(null);
      setError("Geolocation not supported. Using default city.");
    }
  };

  // MoodSync Scoring
  const updateMoodSuggestion = (data) => {
    if (!data) return;
    let score = 0;
    let badge = "";
    let message = "";

    if (data.pressure < 1000) score -= 20;
    else if (data.pressure > 1020) score += 10;
    if (data.clouds > 70) score -= 10;
    else if (data.clouds < 30) score += 10;
    if (data.rain_1h > 0) score -= 15;
    if (data.wind_speed > 10) score -= 10;
    const currentHour = new Date().getHours();
    const sunsetHour = new Date(data.sunset * 1000).getHours();
    if (currentHour >= sunsetHour) score -= 5;

    if (score < -20) {
      message = "Feeling low? Try a calming tea or meditation to recharge!";
      badge = "Zen Master";
    } else if (score < 0) {
      message = "Cloudy or rainy? Stay cozy with a book or movie!";
      badge = "Cozy Reader";
    } else if (score < 20) {
      message =
        "Nice weather! Take a walk or try a fun playlist to boost your mood!";
      badge = "Sunshine Explorer";
    } else {
      message = "Perfect day! Go for a run or outdoor adventure!";
      badge = "Energy Star";
    }

    setMoodSuggestion({ message, badge });
  };

  // Chart for Temperature Trend
  const updateChart = (forecastData) => {
    if (!chartRef.current || !forecastData.length) return;
    if (chartInstance.current) chartInstance.current.destroy();
    const ctx = chartRef.current.getContext("2d");
    chartInstance.current = new Chart(ctx, {
      type: "line",
      data: {
        labels: forecastData.map((item) =>
          new Date(item.timestamp * 1000).toLocaleTimeString()
        ),
        datasets: [
          {
            label: "Temperature (°C)",
            data: forecastData.map((item) => item.temperature),
            borderColor: "#007bff",
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          x: { display: true },
          y: {
            display: true,
            title: { display: true, text: "Temperature (°C)" },
          },
        },
      },
    });
  };

  const getWeatherIcon = (icon) => {
    switch (icon) {
      case "01d":
      case "01n":
        return WiDaySunny;
      case "02d":
      case "02n":
      case "03d":
      case "03n":
      case "04d":
      case "04n":
        return WiCloudy;
      case "09d":
      case "09n":
      case "10d":
      case "10n":
        return WiRain;
      case "11d":
      case "11n":
        return WiThunderstorm;
      default:
        return WiDaySunny;
    }
  };

  const getWeatherAnimationClass = (icon) => {
    switch (icon) {
      case "01d":
      case "01n":
        return "sunny-animation";
      case "02d":
      case "02n":
      case "03d":
      case "03n":
      case "04d":
      case "04n":
        return "cloudy-animation";
      case "09d":
      case "09n":
      case "10d":
      case "10n":
        return "rain-animation";
      case "11d":
      case "11n":
        return "thunderstorm-animation";
      default:
        return "";
    }
  };

  return (
    <div className="app">
      <h1>MoodCast</h1>
      <button className="change-city-btn" onClick={() => setShowModal(true)}>
        Change City
      </button>
      {showModal && (
        <div className="modal">
          <div className="modal-content">
            <h2>Select City</h2>
            <select
              value={selectedCity.name}
              onChange={(e) => {
                console.log("City select: Changed to:", e.target.value);
                setSelectedCity({ name: e.target.value });
                setCoordinates(null);
                setShowModal(false);
                setError(null);
              }}
            >
              {cities.map((city) => (
                <option key={city.name} value={city.name}>
                  {city.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => {
                getCurrentLocation();
                setShowModal(false);
              }}
            >
              Use Current Location
            </button>
            <button onClick={() => setShowModal(false)}>Close</button>
          </div>
        </div>
      )}
      {error && (
        <div className="error">
          <p>{error}</p>
        </div>
      )}
      {!weather && !error && (
        <div className="loading">
          <p>Loading weather data for {selectedCity.name}...</p>
        </div>
      )}
      {weather && (
        <div className={`weather ${getWeatherAnimationClass(weather.icon)}`}>
          <h2>Current Weather in {weather.city}</h2>
          <div className="weather-icon animated">
            {weather.icon &&
              (() => {
                const Icon = getWeatherIcon(weather.icon);
                return <Icon size={50} />;
              })()}
          </div>
          <p>
            Temperature: {weather.temperature}°C (Feels Like:{" "}
            {weather.feels_like}°C)
          </p>
          <p>Pressure: {weather.pressure} hPa</p>
          <p>Humidity: {weather.humidity}%</p>
          <p>Clouds: {weather.clouds}%</p>
          <p>Rain (1h): {weather.rain_1h} mm</p>
          <p>Description: {weather.description}</p>
          <p>
            Sunrise: {new Date(weather.sunrise * 1000).toLocaleTimeString()}
          </p>
          <p>Sunset: {new Date(weather.sunset * 1000).toLocaleTimeString()}</p>
        </div>
      )}
      {moodSuggestion && (
        <div className="mood-suggestion">
          <h3>MoodSync Suggestion</h3>
          <p>{moodSuggestion.message}</p>
          {moodSuggestion.badge && (
            <span className="badge">{moodSuggestion.badge}</span>
          )}
        </div>
      )}
      {alerts.length > 0 && (
        <div className="alerts">
          <h3>Alerts</h3>
          <ul>
            {alerts.map((alert, index) => (
              <li key={index}>{alert}</li>
            ))}
          </ul>
        </div>
      )}
      {forecast.length > 0 && (
        <div className="forecast">
          <h2>72-Hour Forecast</h2>
          <div className="forecast-list">
            {forecast.map((item, index) => (
              <div
                key={index}
                className={`forecast-item ${getWeatherAnimationClass(
                  item.icon
                )}`}
              >
                <p>{new Date(item.timestamp * 1000).toLocaleString()}</p>
                <div className="weather-icon animated">
                  {item.icon &&
                    (() => {
                      const Icon = getWeatherIcon(item.icon);
                      return <Icon size={50} />;
                    })()}
                </div>
                <p>Temp: {item.temperature}°C</p>
                <p>Pressure: {item.pressure} hPa</p>
                <p>Clouds: {item.clouds}%</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {forecast.length > 0 && (
        <div className="chart">
          <h3>Temperature Trend</h3>
          <canvas ref={chartRef}></canvas>
        </div>
      )}
    </div>
  );
}

export default App;
