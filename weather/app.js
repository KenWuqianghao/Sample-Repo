// Minimal weather app using Open-Meteo (no API key required).
// Geocoding: https://open-meteo.com/en/docs/geocoding-api
// Forecast:  https://open-meteo.com/en/docs

const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const geoBtn = document.getElementById("geo-btn");
const statusEl = document.getElementById("status");
const currentEl = document.getElementById("current");
const forecastEl = document.getElementById("forecast");

const placeEl = document.getElementById("place");
const nowTimeEl = document.getElementById("now-time");
const tempEl = document.getElementById("temp");
const condEl = document.getElementById("condition");
const feelsEl = document.getElementById("feels");
const humidityEl = document.getElementById("humidity");
const windEl = document.getElementById("wind");
const forecastList = document.getElementById("forecast-list");

// WMO weather code -> human label
const WEATHER_CODES = {
  0: "Clear sky",
  1: "Mainly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Fog",
  48: "Depositing rime fog",
  51: "Light drizzle",
  53: "Moderate drizzle",
  55: "Dense drizzle",
  56: "Light freezing drizzle",
  57: "Dense freezing drizzle",
  61: "Slight rain",
  63: "Moderate rain",
  65: "Heavy rain",
  66: "Light freezing rain",
  67: "Heavy freezing rain",
  71: "Slight snow",
  73: "Moderate snow",
  75: "Heavy snow",
  77: "Snow grains",
  80: "Rain showers",
  81: "Heavy rain showers",
  82: "Violent rain showers",
  85: "Snow showers",
  86: "Heavy snow showers",
  95: "Thunderstorm",
  96: "Thunderstorm w/ hail",
  99: "Severe thunderstorm w/ hail",
};

function describe(code) {
  return WEATHER_CODES[code] || "Unknown";
}

function setStatus(msg) {
  statusEl.textContent = msg || "";
}

async function geocode(query) {
  const url = new URL("https://geocoding-api.open-meteo.com/v1/search");
  url.searchParams.set("name", query);
  url.searchParams.set("count", "1");
  url.searchParams.set("language", "en");
  url.searchParams.set("format", "json");
  const res = await fetch(url);
  if (!res.ok) throw new Error("Geocoding failed");
  const data = await res.json();
  if (!data.results || data.results.length === 0) {
    throw new Error(`No location found for "${query}"`);
  }
  const r = data.results[0];
  return {
    latitude: r.latitude,
    longitude: r.longitude,
    name: [r.name, r.admin1, r.country].filter(Boolean).join(", "),
    timezone: r.timezone,
  };
}

async function reverseLabel(lat, lon) {
  // Open-Meteo doesn't have reverse geocoding, so just show coords.
  return `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`;
}

async function fetchWeather(lat, lon, timezone = "auto") {
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", lat);
  url.searchParams.set("longitude", lon);
  url.searchParams.set(
    "current",
    "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m"
  );
  url.searchParams.set(
    "daily",
    "weather_code,temperature_2m_max,temperature_2m_min"
  );
  url.searchParams.set("timezone", timezone);
  const res = await fetch(url);
  if (!res.ok) throw new Error("Weather lookup failed");
  return res.json();
}

function render(place, data) {
  const c = data.current;
  placeEl.textContent = place;
  nowTimeEl.textContent = new Date(c.time).toLocaleString();
  tempEl.textContent = Math.round(c.temperature_2m);
  condEl.textContent = describe(c.weather_code);
  feelsEl.textContent = Math.round(c.apparent_temperature);
  humidityEl.textContent = c.relative_humidity_2m;
  windEl.textContent = Math.round(c.wind_speed_10m);

  forecastList.innerHTML = "";
  const days = data.daily.time;
  for (let i = 0; i < days.length; i++) {
    const d = new Date(days[i] + "T00:00:00");
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="day">${d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</span>
      <span class="cond">${describe(data.daily.weather_code[i])}</span>
      <span class="range">
        <strong>${Math.round(data.daily.temperature_2m_max[i])}°</strong>
        <span class="lo">${Math.round(data.daily.temperature_2m_min[i])}°</span>
      </span>
    `;
    forecastList.appendChild(li);
  }

  currentEl.classList.remove("hidden");
  forecastEl.classList.remove("hidden");
}

async function showForQuery(query) {
  try {
    setStatus("Searching…");
    const loc = await geocode(query);
    setStatus("Loading weather…");
    const data = await fetchWeather(loc.latitude, loc.longitude, loc.timezone);
    render(loc.name, data);
    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus(err.message || "Something went wrong.");
  }
}

async function showForCoords(lat, lon) {
  try {
    setStatus("Loading weather…");
    const data = await fetchWeather(lat, lon);
    const label = await reverseLabel(lat, lon);
    render(label, data);
    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus(err.message || "Something went wrong.");
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (q) showForQuery(q);
});

geoBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setStatus("Geolocation not supported by this browser.");
    return;
  }
  setStatus("Getting your location…");
  navigator.geolocation.getCurrentPosition(
    (pos) => showForCoords(pos.coords.latitude, pos.coords.longitude),
    (err) => setStatus(`Location error: ${err.message}`),
    { enableHighAccuracy: false, timeout: 10000 }
  );
});

// Default city on load
showForQuery("San Francisco");
