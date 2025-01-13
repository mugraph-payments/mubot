import json
import aiohttp
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

FUNCTION_SCHEMAS = [
    {
        "name": "get_temperature",
        "description": "Get the current temperature for a specified city",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name with country code (e.g., 'London,UK')"
                }
            },
            "required": ["location"]
        }
    }
]

LOCATION_PATTERNS = {
    "prefixes": [
        "in", "at", "for", "of", "around", "near",
        "what's the temperature in",
        "what is the temperature in",
        "how hot is it in",
        "how cold is it in",
        "what's it like in",
        "temperature of",
        "temperature at",
        "weather in",
        "what's the temp in",
        "what is the temp in",
        "current temperature in",
        "right now in"
    ],
    "suffixes": [
        "right now",
        "at the moment",
        "today",
        "currently",
        "now"
    ]
}

def extract_location(message: str) -> Optional[str]:
    """
    Extract a potential location from the message based on known prefixes/suffixes.
    Returns None if no location is found.
    """
    message_lower = message.lower()

    # Remove known suffixes
    for suffix in LOCATION_PATTERNS["suffixes"]:
        if suffix in message_lower:
            message_lower = message_lower.replace(suffix, "").strip()

    # Check prefixes from longest to shortest (to handle bigger phrases first)
    for prefix in sorted(LOCATION_PATTERNS["prefixes"], key=len, reverse=True):
        if prefix in message_lower:
            potential_location = message_lower.split(prefix, 1)[1].strip()
            potential_location = potential_location.strip('?!.,')
            if potential_location:
                return potential_location

    return None

def should_use_tools(message: str) -> bool:
    """
    Determine if we should call the weather API for this user message.
    Returns True if the message likely requests weather/temperature info.
    """
    message_lower = message.lower()

    # Greet/thanks handling
    if message_lower.startswith(("hi", "hello", "hey", "thanks", "thank")):
        return False

    # Exclude messages about other temperature contexts
    negative_patterns = [
        "temperature setting",
        "fever temperature",
        "body temperature",
        "water temperature",
        "room temperature",
        "cooking temperature"
    ]
    if any(pattern in message_lower for pattern in negative_patterns):
        return False

    # Look for temperature/weather indicators
    temperature_indicators = [
        "degree",
        "celsius",
        "fahrenheit",
        "°c",
        "°f",
        "temperature",
        "weather",
        "hot",
        "cold",
        "warm",
        "temp"
    ]
    has_temperature_indicator = any(indicator in message_lower for indicator in temperature_indicators)
    location = extract_location(message)

    return has_temperature_indicator and location is not None

async def get_temperature(location: str, api_key: str = OPENWEATHER_API_KEY) -> Optional[float]:
    """
    Get the current temperature (in Celsius) for a specific location using
    OpenWeather's 2.5 'weather' endpoint (suitable for the free tier).
    Returns None if no data is found or on error.
    """
    if not api_key:
        raise ValueError("OpenWeather API key is not set.")

    async with aiohttp.ClientSession() as session:
        # 1. Geocoding: Convert city name to lat/lon
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        params_geo = {
            "q": location,
            "limit": 1,
            "appid": api_key
        }
        try:
            async with session.get(geo_url, params=params_geo) as response:
                response.raise_for_status()
                location_data = await response.json()
        except aiohttp.ClientError as e:
            print(f"Failed to fetch geocoding data: {e}")
            return None

        if not location_data:
            # No valid location found
            return None

        lat = location_data[0]["lat"]
        lon = location_data[0]["lon"]

        # 2. Fetch weather data using the 2.5 endpoint
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        params_weather = {
            "lat": lat,
            "lon": lon,
            "units": "metric",  # °C
            "appid": api_key
        }
        try:
            async with session.get(weather_url, params=params_weather) as response:
                response.raise_for_status()
                weather_data = await response.json()
        except aiohttp.ClientError as e:
            print(f"Failed to fetch weather data: {e}")
            return None

        # Extract the current temperature
        try:
            current_temp = weather_data["main"]["temp"]
            return float(current_temp)
        except (KeyError, TypeError):
            return None

async def execute_function_call(function_call: Dict[str, Any]) -> str:
    """
    Execute the function call based on its 'name' and return a user-friendly message.
    """
    if function_call["name"] == "get_temperature":
        args = json.loads(function_call["arguments"])
        temperature = await get_temperature(args["location"])
        if temperature is not None:
            return f"The current temperature in {args['location']} is {temperature}°C."
        return f"Sorry, I couldn't get the temperature for {args['location']}."

    return "Unknown function call"
