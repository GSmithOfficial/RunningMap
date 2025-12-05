# Isodistance Map Calculator

A fast Streamlit app that calculates how far you could travel along real road networks from a starting point and visualizes the reachable area on an interactive map.

Unlike a simple radius circle, this app uses actual road network data to show you the true reachable area based on roads, paths, and routes available.

## Features

- **Lightning Fast**: Results in 1-2 seconds, even for 100km+ distances
- **Real Road Networks**: Uses OpenStreetMap data via OpenRouteService
- **Multiple Travel Modes**: Driving, walking, cycling (road/mountain), hiking, wheelchair
- **Distance Rings**: Visualize multiple distance ranges at once
- **Smart Caching**: Results cached for 24 hours to save API calls
- **Interactive Map**: Search by place name or enter coordinates
- **Customizable**: Multiple color schemes and display options

## Quick Start

### 1. Get a Free API Key

1. Go to [openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)
2. Create a free account
3. Copy your API key

*Free tier includes 2,000 requests/day - plenty for personal use!*

### 2. Install & Run

```bash
# Clone the repo
git clone <repository-url>
cd RunningMap

# Install dependencies (just 4 packages!)
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### 3. Use the App

1. Enter your API key in the sidebar
2. Search for a location or enter coordinates
3. Set your distance (up to 150km!)
4. Choose travel mode (driving, walking, cycling, etc.)
5. Click "Calculate" and see results in ~1-2 seconds

## How It Works

This app uses [OpenRouteService](https://openrouteservice.org/), a powerful routing engine that:

1. **Pre-computes road networks** from OpenStreetMap data
2. **Uses contraction hierarchies** for blazing fast graph traversal
3. **Returns isodistance polygons** directly via API

This is orders of magnitude faster than downloading and processing road networks locally.

## Performance Comparison

| Approach | 10km Query | 100km Query | Dependencies |
|----------|-----------|-------------|--------------|
| Local OSMnx | ~30-60 sec | Not feasible | 9 packages, 500MB+ |
| **OpenRouteService API** | **~1 sec** | **~2 sec** | **4 packages, ~50MB** |

## Dependencies

Just 4 lightweight packages:

- `streamlit` - Web UI framework
- `folium` - Interactive maps
- `streamlit-folium` - Streamlit + Folium integration
- `requests` - HTTP client for API calls

## API Limits

OpenRouteService free tier:
- 2,000 requests/day
- 40 requests/minute
- Up to 150km distance range

For higher limits, see [ORS pricing](https://openrouteservice.org/plans/).

## License

MIT License
