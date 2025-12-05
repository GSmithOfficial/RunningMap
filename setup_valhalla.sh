#!/bin/bash

# Valhalla Setup Script
# Downloads OSM data and starts the Valhalla routing engine

set -e

echo "=========================================="
echo "  Valhalla Isodistance Setup"
echo "=========================================="
echo ""

# Create data directory
mkdir -p valhalla_data

# Region selection
echo "Select a region to download:"
echo ""
echo "Small regions (fast setup, <1GB):"
echo "  1) Great Britain (~1.1GB, builds in ~10 min)"
echo "  2) Germany (~3.5GB, builds in ~30 min)"
echo "  3) France (~3.8GB, builds in ~30 min)"
echo "  4) Spain (~1.0GB, builds in ~10 min)"
echo "  5) Italy (~1.5GB, builds in ~15 min)"
echo "  6) Netherlands (~1.1GB, builds in ~10 min)"
echo ""
echo "Medium regions (1-5GB):"
echo "  10) Europe (~28GB, builds in ~3-4 hours)"
echo "  11) North America (~12GB, builds in ~2 hours)"
echo "  12) Australia & Oceania (~1GB, builds in ~10 min)"
echo ""
echo "US States:"
echo "  20) California (~1.0GB)"
echo "  21) New York (~400MB)"
echo "  22) Texas (~600MB)"
echo "  23) Florida (~400MB)"
echo ""
echo "Other:"
echo "  30) Custom URL (enter your own Geofabrik URL)"
echo "  31) Planet (entire world - 70GB+, needs 100GB+ RAM)"
echo ""

read -p "Enter selection [1]: " selection
selection=${selection:-1}

case $selection in
    1) TILE_URL="https://download.geofabrik.de/europe/great-britain-latest.osm.pbf" ;;
    2) TILE_URL="https://download.geofabrik.de/europe/germany-latest.osm.pbf" ;;
    3) TILE_URL="https://download.geofabrik.de/europe/france-latest.osm.pbf" ;;
    4) TILE_URL="https://download.geofabrik.de/europe/spain-latest.osm.pbf" ;;
    5) TILE_URL="https://download.geofabrik.de/europe/italy-latest.osm.pbf" ;;
    6) TILE_URL="https://download.geofabrik.de/europe/netherlands-latest.osm.pbf" ;;
    10) TILE_URL="https://download.geofabrik.de/europe-latest.osm.pbf" ;;
    11) TILE_URL="https://download.geofabrik.de/north-america-latest.osm.pbf" ;;
    12) TILE_URL="https://download.geofabrik.de/australia-oceania-latest.osm.pbf" ;;
    20) TILE_URL="https://download.geofabrik.de/north-america/us/california-latest.osm.pbf" ;;
    21) TILE_URL="https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf" ;;
    22) TILE_URL="https://download.geofabrik.de/north-america/us/texas-latest.osm.pbf" ;;
    23) TILE_URL="https://download.geofabrik.de/north-america/us/florida-latest.osm.pbf" ;;
    30)
        read -p "Enter Geofabrik URL: " TILE_URL
        ;;
    31) TILE_URL="https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf" ;;
    *)
        echo "Invalid selection, using Great Britain"
        TILE_URL="https://download.geofabrik.de/europe/great-britain-latest.osm.pbf"
        ;;
esac

echo ""
echo "Selected: $TILE_URL"
echo ""

# Export for docker-compose
export TILE_URL

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not installed."
    exit 1
fi

echo "Starting Valhalla..."
echo "This will:"
echo "  1. Download the OSM data (~may take a while)"
echo "  2. Build routing tiles (can take 10min - several hours)"
echo "  3. Start the routing server on port 8002"
echo ""
echo "First run will take time. Subsequent runs are instant."
echo ""

# Use docker compose (v2) or docker-compose (v1)
if docker compose version &> /dev/null; then
    TILE_URL=$TILE_URL docker compose up -d
else
    TILE_URL=$TILE_URL docker-compose up -d
fi

echo ""
echo "=========================================="
echo "  Valhalla is starting!"
echo "=========================================="
echo ""
echo "Monitor progress with:"
echo "  docker logs -f valhalla"
echo ""
echo "Once ready, the API will be at:"
echo "  http://localhost:8002"
echo ""
echo "Test with:"
echo "  curl 'http://localhost:8002/status'"
echo ""
echo "Then run the Streamlit app:"
echo "  streamlit run app.py"
echo ""
echo "And select 'Local (Valhalla)' as the backend!"
