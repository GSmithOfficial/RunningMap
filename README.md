# Isodistance Map Calculator

A Streamlit app that calculates how far you could travel along real road networks from a starting point and visualizes the reachable area on an interactive map.

Unlike a simple radius circle, this app uses actual road network data from OpenStreetMap to show you the true reachable area based on the roads, paths, and routes available.

## Features

- **Real Road Networks**: Uses OpenStreetMap data to calculate actual travel distances along roads
- **Multiple Travel Modes**: Support for driving, walking, cycling, or all road types
- **Interactive Map**: Click to set your starting point or search by place name
- **Customizable Display**: Choose colors, opacity, and polygon smoothing options
- **Distance Units**: Support for kilometers, miles, and meters

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd RunningMap
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to the URL shown (typically http://localhost:8501)

3. Configure your settings in the sidebar:
   - Set your starting location (coordinates, place search, or click on map)
   - Enter the distance you want to travel
   - Choose your travel mode (drive, walk, bike)
   - Customize display options

4. Click "Calculate Reachable Area" to see the results

## How It Works

1. **Network Download**: Downloads road network data from OpenStreetMap for the area around your starting point
2. **Graph Analysis**: Uses Dijkstra's algorithm to find all road intersections reachable within your specified distance
3. **Polygon Creation**: Creates a polygon encompassing all reachable points to visualize the area
4. **Map Display**: Shows the results on an interactive Folium map

## Limitations

- Maximum calculation radius is capped at 50km to prevent very long download times
- Larger distances and denser urban areas require more processing time
- Results depend on OpenStreetMap data quality for your area

## Dependencies

- `streamlit` - Web application framework
- `osmnx` - OpenStreetMap network analysis
- `networkx` - Graph algorithms
- `folium` / `streamlit-folium` - Interactive maps
- `shapely` / `geopandas` - Geometric operations
- `scipy` / `numpy` - Numerical computations

## License

MIT License
