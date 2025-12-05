"""
Isodistance Map - Streamlit App (Optimized Version)

Uses OpenRouteService API for fast isodistance calculations.
Results in 1-2 seconds even for distances up to 100km+.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Isodistance Map",
    page_icon="🗺️",
    layout="wide"
)

# Cache directory
CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRY_HOURS = 24

# OpenRouteService API configuration
ORS_BASE_URL = "https://api.openrouteservice.org/v2/isochrones"

# Profile mapping
PROFILE_MAP = {
    "Driving": "driving-car",
    "Walking": "foot-walking",
    "Cycling": "cycling-regular",
    "Cycling (Road)": "cycling-road",
    "Cycling (Mountain)": "cycling-mountain",
    "Hiking": "foot-hiking",
    "Wheelchair": "wheelchair"
}


def get_cache_key(lat: float, lon: float, distance_m: float, profile: str) -> str:
    """Generate a unique cache key for the request."""
    data = f"{lat:.6f},{lon:.6f},{distance_m},{profile}"
    return hashlib.md5(data.encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[dict]:
    """Retrieve cached result if it exists and is not expired."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            # Check expiry
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                return cached['data']
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def save_to_cache(cache_key: str, data: dict):
    """Save result to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    with open(cache_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'data': data
        }, f)


def calculate_isodistance(
    api_key: str,
    lat: float,
    lon: float,
    distances_m: list[float],
    profile: str = "driving-car"
) -> Optional[dict]:
    """
    Calculate isodistance using OpenRouteService API.

    Args:
        api_key: OpenRouteService API key
        lat, lon: Starting coordinates
        distances_m: List of distances in meters (for multiple rings)
        profile: Travel mode profile

    Returns:
        GeoJSON FeatureCollection with isodistance polygons
    """
    # Check cache first
    cache_key = get_cache_key(lat, lon, max(distances_m), profile)
    cached = get_cached_result(cache_key)
    if cached:
        return cached

    url = f"{ORS_BASE_URL}/{profile}"

    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    body = {
        'locations': [[lon, lat]],  # Note: ORS uses [lon, lat] order
        'range': distances_m,
        'range_type': 'distance',
        'units': 'm',
        'smoothing': 25,  # Smooth the polygon edges
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        # Cache the result
        save_to_cache(cache_key, result)

        return result
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            st.error("Invalid API key. Please check your OpenRouteService API key.")
        elif response.status_code == 403:
            st.error("API key doesn't have permission for this endpoint.")
        elif response.status_code == 429:
            st.error("Rate limit exceeded. Please wait a moment and try again.")
        else:
            st.error(f"API Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return None


def geocode_place(api_key: str, place_name: str) -> Optional[tuple[float, float]]:
    """Geocode a place name to coordinates using ORS."""
    url = "https://api.openrouteservice.org/geocode/search"

    headers = {'Authorization': api_key}
    params = {'text': place_name, 'size': 1}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('features'):
            coords = data['features'][0]['geometry']['coordinates']
            return coords[1], coords[0]  # Return as lat, lon
    except Exception:
        pass
    return None


def add_isodistance_to_map(m: folium.Map, geojson_data: dict, colors: list[str]):
    """Add isodistance polygons to the map."""
    if not geojson_data or 'features' not in geojson_data:
        return

    features = geojson_data['features']

    # Sort features by distance (largest first so smaller ones draw on top)
    features_sorted = sorted(
        features,
        key=lambda f: f.get('properties', {}).get('value', 0),
        reverse=True
    )

    for i, feature in enumerate(features_sorted):
        color = colors[i % len(colors)]
        distance_m = feature.get('properties', {}).get('value', 0)
        distance_km = distance_m / 1000

        folium.GeoJson(
            feature,
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': c,
                'weight': 2,
                'fillOpacity': 0.3,
            },
            tooltip=f"{distance_km:.1f} km"
        ).add_to(m)


def main():
    st.title("🗺️ Isodistance Map Calculator")
    st.markdown("""
    Calculate the actual area you can reach traveling a certain distance along roads.
    Powered by OpenRouteService - results in seconds, even for 100km+ distances.
    """)

    # Check for API key
    api_key = st.session_state.get('ors_api_key', '')

    # API Key setup section
    with st.sidebar:
        st.header("🔑 API Setup")

        with st.expander("API Key Configuration", expanded=not api_key):
            st.markdown("""
            This app uses [OpenRouteService](https://openrouteservice.org/) for fast calculations.

            **Get your free API key:**
            1. Go to [openrouteservice.org](https://openrouteservice.org/dev/#/signup)
            2. Create a free account
            3. Copy your API key

            *Free tier: 2,000 requests/day*
            """)

            new_api_key = st.text_input(
                "Enter API Key",
                value=api_key,
                type="password",
                help="Your OpenRouteService API key"
            )

            if new_api_key != api_key:
                st.session_state['ors_api_key'] = new_api_key
                api_key = new_api_key

        if api_key:
            st.success("✓ API key configured")
        else:
            st.warning("⚠ API key required")

        st.divider()

        st.header("⚙️ Settings")

        # Location input
        st.subheader("📍 Starting Location")

        location_method = st.radio(
            "Input method:",
            ["Search place", "Enter coordinates"],
            horizontal=True
        )

        if location_method == "Search place":
            place_name = st.text_input("Place name", "London, UK")

            if place_name and api_key:
                coords = geocode_place(api_key, place_name)
                if coords:
                    lat, lon = coords
                    st.caption(f"📍 {lat:.4f}, {lon:.4f}")
                else:
                    st.caption("Could not find location")
                    lat, lon = 51.5074, -0.1278
            else:
                lat, lon = 51.5074, -0.1278
        else:
            col1, col2 = st.columns(2)
            with col1:
                lat = st.number_input("Latitude", value=51.5074, format="%.6f")
            with col2:
                lon = st.number_input("Longitude", value=-0.1278, format="%.6f")

        st.divider()

        # Distance input
        st.subheader("📏 Distance")

        distance_unit = st.selectbox("Unit", ["Kilometers", "Miles"])

        if distance_unit == "Kilometers":
            max_dist = 150.0
            default_dist = 10.0
            distance_input = st.slider(
                "Distance (km)",
                min_value=1.0,
                max_value=max_dist,
                value=default_dist,
                step=1.0
            )
            distance_m = distance_input * 1000
        else:
            max_dist = 93.0  # ~150km
            default_dist = 6.0
            distance_input = st.slider(
                "Distance (miles)",
                min_value=1.0,
                max_value=max_dist,
                value=default_dist,
                step=1.0
            )
            distance_m = distance_input * 1609.34

        # Show distance rings
        show_rings = st.checkbox("Show distance rings", value=True)
        if show_rings:
            num_rings = st.slider("Number of rings", 1, 5, 3)
        else:
            num_rings = 1

        st.divider()

        # Travel mode
        st.subheader("🚗 Travel Mode")

        travel_mode = st.selectbox(
            "Mode",
            list(PROFILE_MAP.keys()),
            help="How you're traveling"
        )
        profile = PROFILE_MAP[travel_mode]

        st.divider()

        # Color scheme
        st.subheader("🎨 Appearance")

        color_schemes = {
            "Blue": ["#08519c", "#3182bd", "#6baed6", "#9ecae1", "#c6dbef"],
            "Green": ["#006d2c", "#31a354", "#74c476", "#a1d99b", "#c7e9c0"],
            "Red": ["#a50f15", "#de2d26", "#fb6a4a", "#fc9272", "#fcbba1"],
            "Purple": ["#54278f", "#756bb1", "#9e9ac8", "#bcbddc", "#dadaeb"],
            "Orange": ["#a63603", "#e6550d", "#fd8d3c", "#fdae6b", "#fdd0a2"],
        }

        color_choice = st.selectbox("Color scheme", list(color_schemes.keys()))
        colors = color_schemes[color_choice]

        st.divider()

        # Calculate button
        calculate_btn = st.button(
            "🚀 Calculate",
            type="primary",
            use_container_width=True,
            disabled=not api_key
        )

    # Main map area
    col_map, col_info = st.columns([3, 1])

    with col_map:
        # Create base map
        m = folium.Map(location=[lat, lon], zoom_start=11, tiles="cartodbpositron")

        # Add starting point marker
        folium.Marker(
            [lat, lon],
            popup=f"Start: {lat:.4f}, {lon:.4f}",
            tooltip="Starting Point",
            icon=folium.Icon(color='red', icon='play', prefix='fa')
        ).add_to(m)

        # Calculate and display isodistance
        if calculate_btn and api_key:
            # Generate distance rings
            if num_rings > 1:
                distances = [distance_m * (i + 1) / num_rings for i in range(num_rings)]
            else:
                distances = [distance_m]

            with st.spinner("Calculating reachable area..."):
                result = calculate_isodistance(api_key, lat, lon, distances, profile)

            if result:
                add_isodistance_to_map(m, result, colors)

                # Store results
                st.session_state['last_result'] = result
                st.session_state['last_params'] = {
                    'lat': lat,
                    'lon': lon,
                    'distance_m': distance_m,
                    'profile': profile,
                    'travel_mode': travel_mode
                }

                # Fit map to bounds
                if result.get('bbox'):
                    bbox = result['bbox']
                    m.fit_bounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]])

                st.success("✓ Calculation complete!")

        # Show previous result if exists
        elif 'last_result' in st.session_state:
            result = st.session_state['last_result']
            add_isodistance_to_map(m, result, colors)
            if result.get('bbox'):
                bbox = result['bbox']
                m.fit_bounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]])

        # Display map
        st_folium(m, width=None, height=600, key="main_map")

    with col_info:
        st.subheader("ℹ️ Info")

        st.markdown(f"""
        **Current Settings:**
        - 📍 Location: `{lat:.4f}, {lon:.4f}`
        - 📏 Distance: `{distance_input:.1f} {distance_unit.lower()}`
        - 🚗 Mode: `{travel_mode}`
        """)

        if 'last_params' in st.session_state:
            params = st.session_state['last_params']
            st.divider()
            st.markdown(f"""
            **Last Calculation:**
            - Distance: `{params['distance_m']/1000:.1f} km`
            - Mode: `{params['travel_mode']}`
            """)

        st.divider()

        st.markdown("""
        **How it works:**

        Uses [OpenRouteService](https://openrouteservice.org/) routing engine with:
        - Pre-computed road network graphs
        - Contraction hierarchies for speed
        - Real road data from OpenStreetMap

        **Performance:**
        - ~1-2 seconds for any distance
        - Up to 150km supported
        - Results are cached for 24h

        **Tips:**
        - Different travel modes give very different results
        - Urban areas have more roads = larger reachable area
        - Try "Walking" vs "Driving" to see the difference
        """)


if __name__ == "__main__":
    main()
