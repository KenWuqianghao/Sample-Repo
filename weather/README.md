# Weather

A tiny static weather web app powered by [Open-Meteo](https://open-meteo.com/) — no API key required.

## Features
- City search via Open-Meteo geocoding API
- "Use my location" button (browser geolocation)
- Current conditions: temperature, feels-like, humidity, wind, condition label
- 7-day forecast with daily highs/lows
- Pure HTML/CSS/JS — no build step

## Run
Just open `index.html` in a browser, or serve the folder:

```sh
python -m http.server -d weather 8000
# then visit http://localhost:8000
```

## Files
- `index.html` — markup
- `styles.css` — styles
- `app.js` — geocoding + forecast logic
- WMO weather codes mapped to human-readable labels in `app.js`

## Notes
- Units are metric (°C, km/h). Adjust the Open-Meteo query params in `app.js` to switch to imperial.
- Open-Meteo's free tier is generous and CORS-friendly, so this works as a fully static site.
