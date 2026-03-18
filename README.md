# Dijkstra Router — Thesis Project

A web-based routing application developed as a thesis project on the implementation and analysis of Dijkstra's algorithm for optimal route finding. The application extends beyond the core algorithm to include A\*, bidirectional search, live traffic integration, and a Google Maps-style interface.

## Features

**Routing algorithms**
- Dijkstra — classic implementation, baseline for comparison
- A\* — with Manhattan, Euclidean, and adaptive heuristics
- Bidirectional Dijkstra — roughly 2× faster on long routes
- Automatic algorithm selection based on route characteristics

**Traffic**
- Live traffic data from TomTom, HERE, MapBox, and Google Maps APIs
- Traffic-colored route segments (free flow → heavy congestion)
- Rush hour multipliers and traffic light estimation for urban areas
- Real-time ETA updates via WebSocket

**Interface**
- Leaflet.js map with CARTO tile layers (light and dark)
- Sidebar with autocomplete location search (Nominatim/OSM)
- Turn-by-turn directions with distance and duration per step
- Dark mode, responsive layout, mobile bottom-sheet

## Tech Stack

**Backend:** Python 3, Flask, Flask-SocketIO
**Frontend:** HTML/CSS/JavaScript, Leaflet.js
**Data:** OpenStreetMap (Overpass API), OSM road network cached as pickled graphs
**Traffic APIs:** TomTom, HERE, MapBox, Google Maps (optional)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys. Only `TOMTOM_API_KEY` is required for live traffic. The app works without any traffic keys but will fall back to simulated traffic data.

### 3. Run

```bash
python app.py
```

Open `http://localhost:5000`.

## API Keys

| Key | Provider | Required |
|-----|----------|----------|
| `TOMTOM_API_KEY` | [developer.tomtom.com](https://developer.tomtom.com/) | For live traffic |
| `HERE_API_KEY` | [developer.here.com](https://developer.here.com/) | Optional |
| `MAPBOX_ACCESS_TOKEN` | [mapbox.com](https://www.mapbox.com/) | Optional |
| `GOOGLE_MAPS_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com/) | Optional |

## Project Structure

```
app.py                          # Flask server, route endpoints, SocketIO
routing/
    dijkstra.py                 # Dijkstra + bidirectional implementation
    astar_dijkstra.py           # A* with multiple heuristics
    osm_handler.py              # OSM graph loading and caching
    route_manager.py            # Algorithm selection and coordination
    live_traffic_manager.py     # Multi-source traffic data integration
    traffic_manager.py          # Traffic state and caching
    realtime_manager.py         # WebSocket real-time updates
    osrm_helper.py              # OSRM fallback helper
static/
    script.js                   # Map, autocomplete, route rendering
    style.css                   # Responsive UI, dark mode
templates/
    index.html                  # Main interface
    realtime_demo.html          # WebSocket demo page
```

## Notes

- OSM graph data is cached under `_osm_cache/` (excluded from version control). The first request for a new area downloads and caches the road network automatically.
- The app works without any API keys — traffic visualization will use simulated data.
- `SECRET_KEY` in `.env` should be changed to a random string for any non-local deployment.

## Author

**Name:** Marios Nikolaos Stefanidis
**Degree:** BSc Computer Science (First Class Honours)
**University:** University of East London

## License

MIT
