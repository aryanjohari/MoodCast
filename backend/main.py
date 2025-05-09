from fetch_weather import fetch_weather, fetch_forecast
from database import store_weather_data, store_forecast_data

CITY = "London"  # Change to your preferred city

def main():
    # Fetch and store current weather
    weather_data = fetch_weather(CITY)
    if weather_data:
        store_weather_data(
            weather_data,
            location=weather_data["city"],
            device_label="MoodCast"
        )
        print("Current weather stored.")
    else:
        print("Failed to store current weather.")

    # Fetch and store 48-hour forecast
    forecast_data = fetch_forecast(CITY)
    if forecast_data:
        store_forecast_data(
            forecast_data,
            location=weather_data["city"] if weather_data else CITY,
            device_label="MoodCast"
        )
        print("48-hour forecast stored.")
    else:
        print("Failed to store forecast.")

if __name__ == "__main__":
    main()