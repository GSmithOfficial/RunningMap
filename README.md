# Isodistance Map Calculator

Calculate how far you can actually travel along road networks - no distance limits!

Shows the real area you can reach, not just a radius circle. Uses actual road data from OpenStreetMap.

## Features

- **Unlimited Distance**: Calculate 10km, 100km, or 1000km+ with local Valhalla
- **Two Backends**: Local Valhalla (unlimited) or OpenRouteService API (easy setup)
- **Multiple Travel Modes**: Driving, walking, cycling, bus, truck, motorcycle
- **Distance Rings**: Visualize multiple distance ranges at once
- **Smart Caching**: Results cached for 24 hours
- **Offline Capable**: Works without internet once Valhalla is set up

## Quick Start

### Option 1: OpenRouteService API (Easiest)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Get a free API key from [openrouteservice.org](https://openrouteservice.org/dev/#/signup) (2,000 requests/day).

**Limits**: 150km max distance, requires internet.

### Option 2: Local Valhalla (Unlimited - Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up Valhalla (requires Docker)
./setup_valhalla.sh

# Wait for tiles to build (10min - few hours depending on region)
docker logs -f valhalla

# Run the app
streamlit run app.py
```

**No limits**: Any distance, unlimited queries, works offline.

## Valhalla Setup Details

The setup script lets you choose from pre-configured regions:

| Region | Download Size | Build Time | Coverage |
|--------|--------------|------------|----------|
| Great Britain | ~1.1 GB | ~10 min | UK |
| Germany | ~3.5 GB | ~30 min | Germany |
| California | ~1.0 GB | ~15 min | CA, USA |
| Europe | ~28 GB | ~3-4 hours | All of Europe |
| North America | ~12 GB | ~2 hours | USA, Canada, Mexico |
| Planet | ~70 GB | ~12+ hours | Entire world |

### System Requirements for Valhalla

| Region Size | RAM | Disk Space |
|-------------|-----|------------|
| Single country | 4 GB | 10 GB |
| Continent | 16 GB | 50 GB |
| Planet | 64+ GB | 200+ GB |

### Manual Valhalla Setup

If you prefer manual control:

```bash
# Create data directory
mkdir -p valhalla_data

# Download OSM data (example: Great Britain)
wget -P valhalla_data https://download.geofabrik.de/europe/great-britain-latest.osm.pbf

# Start Valhalla with Docker
docker run -d --name valhalla \
  -p 8002:8002 \
  -v $(pwd)/valhalla_data:/custom_files \
  -e tile_urls=https://download.geofabrik.de/europe/great-britain-latest.osm.pbf \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest

# Monitor build progress
docker logs -f valhalla
```

Find more OSM extracts at [download.geofabrik.de](https://download.geofabrik.de/).

## How It Works

### With Valhalla (Local)

1. Downloads OpenStreetMap road data for your region
2. Builds a routing graph with contraction hierarchies
3. Calculates isodistance polygons using the `/isochrone` endpoint
4. All processing happens locally - no external API calls

### With OpenRouteService (API)

1. Sends request to ORS cloud servers
2. ORS uses pre-built global routing data
3. Returns isodistance polygons
4. Limited by API quotas (2,000/day free)

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────┐
│   Streamlit UI  │────▶│         Backend Choice           │
└─────────────────┘     └──────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          ┌─────────────────┐               ┌─────────────────┐
          │ Local Valhalla  │               │  ORS API        │
          │ (Docker)        │               │  (Cloud)        │
          │                 │               │                 │
          │ • Unlimited     │               │ • 150km max     │
          │ • No API key    │               │ • 2000 req/day  │
          │ • Works offline │               │ • Easy setup    │
          └─────────────────┘               └─────────────────┘
```

## Dependencies

Just 4 packages:

```
streamlit
folium
streamlit-folium
requests
```

Plus Docker for local Valhalla (optional).

## Files

```
├── app.py               # Main Streamlit application
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Valhalla Docker configuration
├── setup_valhalla.sh    # Interactive setup script
└── README.md            # This file
```

## Troubleshooting

### Valhalla won't start
```bash
# Check logs
docker logs valhalla

# Restart
docker restart valhalla

# Full reset
docker rm -f valhalla
rm -rf valhalla_data
./setup_valhalla.sh
```

### "Location not covered" error
Your starting point is outside your OSM data extract. Either:
- Download a larger region
- Choose a location within your current region

### Slow calculations
For very large distances (500km+), calculations may take 10-30 seconds. Results are cached, so subsequent queries are instant.

## License

MIT License
