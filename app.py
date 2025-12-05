"""
Isodistance Map - Streamlit App

Calculates how far you can travel along road networks and visualizes the reachable area.
Supports both local Valhalla (unlimited) and OpenRouteService API backends.
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
import urllib.parse

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

# API configurations
VALHALLA_URL = "http://localhost:8002"
ORS_BASE_URL = "https://api.openrouteservice.org/v2/isochrones"

# Profile mappings
VALHALLA_PROFILES = {
    "Driving": "auto",
    "Walking": "pedestrian",
    "Cycling": "bicycle",
    "Bus": "bus",
    "Truck": "truck",
    "Motorcycle": "motorcycle",
}

ORS_PROFILES = {
    "Driving": "driving-car",
    "Walking": "foot-walking",
    "Cycling": "cycling-regular",
    "Cycling (Road)": "cycling-road",
    "Hiking": "foot-hiking",
}


def get_cache_key(lat: float, lon: float, distance_m: float, profile: str, backend: str) -> str:
    """Generate a unique cache key for the request."""
    data = f"{backend}:{lat:.6f},{lon:.6f},{distance_m},{profile}"
    return hashlib.md5(data.encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[dict]:
    """Retrieve cached result if it exists and is not expired."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
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


def check_valhalla_status() -> bool:
    """Check if local Valhalla server is running."""
    try:
        response = requests.get(f"{VALHALLA_URL}/status", timeout=2)
        return response.status_code == 200
    except:
        return False


def calculate_isodistance_valhalla(
    lat: float,
    lon: float,
    distances_km: list[float],
    profile: str = "auto"
) -> Optional[dict]:
    """
    Calculate isodistance using local Valhalla server.
    NO LIMITS on distance!
    """
    cache_key = get_cache_key(lat, lon, max(distances_km) * 1000, profile, "valhalla")
    cached = get_cached_result(cache_key)
    if cached:
        return cached

    # Build contours for each distance
    contours = [{"distance": d} for d in distances_km]

    request_body = {
        "locations": [{"lat": lat, "lon": lon}],
        "costing": profile,
        "contours": contours,
        "polygons": True,
        "denoise": 0.5,
        "generalize": 50,  # Simplification tolerance in meters
    }

    url = f"{VALHALLA_URL}/isochrone?json={urllib.parse.quote(json.dumps(request_body))}"

    try:
        response = requests.get(url, timeout=120)  # Longer timeout for big distances
        response.raise_for_status()
        result = response.json()

        # Convert Valhalla response to GeoJSON FeatureCollection format
        geojson = convert_valhalla_to_geojson(result, distances_km)

        save_to_cache(cache_key, geojson)
        return geojson

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to Valhalla. Is it running? Start with: ./setup_valhalla.sh")
        return None
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = response.json().get('error', '')
        except:
            pass
        st.error(f"Valhalla error: {e} {error_detail}")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def convert_valhalla_to_geojson(valhalla_response: dict, distances_km: list[float]) -> dict:
    """Convert Valhalla isochrone response to standard GeoJSON FeatureCollection."""
    features = []

    if 'features' in valhalla_response:
        # Valhalla returns GeoJSON directly
        for i, feature in enumerate(valhalla_response['features']):
            # Add distance value to properties
            distance_km = distances_km[i] if i < len(distances_km) else 0
            feature['properties']['value'] = distance_km * 1000  # Convert to meters for consistency
            features.append(feature)

    # Calculate bounding box
    bbox = None
    for feature in features:
        if feature['geometry']['type'] == 'Polygon':
            coords = feature['geometry']['coordinates'][0]
            for lon, lat in coords:
                if bbox is None:
                    bbox = [lon, lat, lon, lat]
                else:
                    bbox[0] = min(bbox[0], lon)
                    bbox[1] = min(bbox[1], lat)
                    bbox[2] = max(bbox[2], lon)
                    bbox[3] = max(bbox[3], lat)

    return {
        'type': 'FeatureCollection',
        'features': features,
        'bbox': bbox
    }


def calculate_isodistance_ors(
    api_key: str,
    lat: float,
    lon: float,
    distances_m: list[float],
    profile: str = "driving-car"
) -> Optional[dict]:
    """Calculate isodistance using OpenRouteService API."""
    cache_key = get_cache_key(lat, lon, max(distances_m), profile, "ors")
    cached = get_cached_result(cache_key)
    if cached:
        return cached

    url = f"{ORS_BASE_URL}/{profile}"
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    body = {
        'locations': [[lon, lat]],
        'range': distances_m,
        'range_type': 'distance',
        'units': 'm',
        'smoothing': 25,
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        save_to_cache(cache_key, result)
        return result
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            st.error("Invalid API key.")
        elif response.status_code == 429:
            st.error("Rate limit exceeded. Try local Valhalla for unlimited queries!")
        else:
            st.error(f"API Error: {e}")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def geocode_nominatim(place_name: str) -> Optional[tuple[float, float]]:
    """Geocode using free Nominatim service."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': place_name,
        'format': 'json',
        'limit': 1
    }
    headers = {'User-Agent': 'IsodistanceMap/1.0'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return None


def add_isodistance_to_map(m: folium.Map, geojson_data: dict, colors: list[str]):
    """Add isodistance polygons to the map."""
    if not geojson_data or 'features' not in geojson_data:
        return

    features = geojson_data['features']

    # Sort by distance (largest first so smaller ones draw on top)
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

    # Check Valhalla status
    valhalla_available = check_valhalla_status()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Backend selection
        st.subheader("🖥️ Backend")

        if valhalla_available:
            st.success("✓ Local Valhalla detected!")
            backend_options = ["Local (Valhalla) - Unlimited!", "OpenRouteService API"]
            default_backend = 0
        else:
            st.info("💡 Run `./setup_valhalla.sh` for unlimited distances")
            backend_options = ["OpenRouteService API", "Local (Valhalla)"]
            default_backend = 0

        backend = st.selectbox("Select backend:", backend_options, index=default_backend)
        use_valhalla = "Valhalla" in backend

        # API key for ORS
        api_key = ""
        if not use_valhalla:
            with st.expander("API Key", expanded=True):
                st.markdown("Get free key: [openrouteservice.org](https://openrouteservice.org/dev/#/signup)")
                api_key = st.text_input("API Key", type="password", key="ors_key")
                if api_key:
                    st.success("✓ Key entered")

        st.divider()

        # Location
        st.subheader("📍 Location")

        location_method = st.radio("Input:", ["Search place", "Coordinates"], horizontal=True)

        if location_method == "Search place":
            place_name = st.text_input("Place name", "London, UK")
            if place_name:
                coords = geocode_nominatim(place_name)
                if coords:
                    lat, lon = coords
                    st.caption(f"📍 {lat:.4f}, {lon:.4f}")
                else:
                    st.caption("Location not found")
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

        # Distance
        st.subheader("📏 Distance")

        distance_unit = st.selectbox("Unit", ["Kilometers", "Miles"])

        if use_valhalla:
            # UNLIMITED distance for Valhalla!
            max_dist = 1000.0 if distance_unit == "Kilometers" else 620.0
            default_dist = 50.0 if distance_unit == "Kilometers" else 30.0
            st.caption("🚀 No distance limit with local Valhalla!")
        else:
            # Limited for ORS
            max_dist = 150.0 if distance_unit == "Kilometers" else 93.0
            default_dist = 10.0 if distance_unit == "Kilometers" else 6.0

        if distance_unit == "Kilometers":
            distance_input = st.slider(
                "Distance (km)",
                min_value=1.0,
                max_value=max_dist,
                value=default_dist,
                step=1.0 if max_dist <= 200 else 5.0
            )
            distance_km = distance_input
            distance_m = distance_input * 1000
        else:
            distance_input = st.slider(
                "Distance (miles)",
                min_value=1.0,
                max_value=max_dist,
                value=default_dist,
                step=1.0 if max_dist <= 100 else 5.0
            )
            distance_km = distance_input * 1.60934
            distance_m = distance_input * 1609.34

        # Distance rings
        show_rings = st.checkbox("Show distance rings", value=True)
        num_rings = st.slider("Number of rings", 1, 5, 3) if show_rings else 1

        st.divider()

        # Travel mode
        st.subheader("🚗 Travel Mode")

        profiles = VALHALLA_PROFILES if use_valhalla else ORS_PROFILES
        travel_mode = st.selectbox("Mode", list(profiles.keys()))
        profile = profiles[travel_mode]

        st.divider()

        # Colors
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
        can_calculate = use_valhalla or api_key
        calculate_btn = st.button(
            "🚀 Calculate",
            type="primary",
            use_container_width=True,
            disabled=not can_calculate
        )

        if not can_calculate:
            st.warning("Enter API key or start local Valhalla")

    # Main area
    col_map, col_info = st.columns([3, 1])

    with col_map:
        # Determine zoom based on distance
        if distance_km > 500:
            zoom = 5
        elif distance_km > 200:
            zoom = 6
        elif distance_km > 100:
            zoom = 7
        elif distance_km > 50:
            zoom = 8
        elif distance_km > 20:
            zoom = 9
        else:
            zoom = 11

        m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles="cartodbpositron")

        # Starting point
        folium.Marker(
            [lat, lon],
            popup=f"Start: {lat:.4f}, {lon:.4f}",
            tooltip="Starting Point",
            icon=folium.Icon(color='red', icon='play', prefix='fa')
        ).add_to(m)

        # Calculate
        if calculate_btn:
            # Generate distance rings
            if num_rings > 1:
                distances_km_list = [distance_km * (i + 1) / num_rings for i in range(num_rings)]
                distances_m_list = [distance_m * (i + 1) / num_rings for i in range(num_rings)]
            else:
                distances_km_list = [distance_km]
                distances_m_list = [distance_m]

            with st.spinner(f"Calculating reachable area ({distance_km:.0f} km)..."):
                if use_valhalla:
                    result = calculate_isodistance_valhalla(lat, lon, distances_km_list, profile)
                else:
                    result = calculate_isodistance_ors(api_key, lat, lon, distances_m_list, profile)

            if result:
                add_isodistance_to_map(m, result, colors)

                st.session_state['last_result'] = result
                st.session_state['last_params'] = {
                    'lat': lat, 'lon': lon,
                    'distance_km': distance_km,
                    'travel_mode': travel_mode,
                    'backend': 'Valhalla' if use_valhalla else 'ORS'
                }

                # Fit bounds
                if result.get('bbox'):
                    bbox = result['bbox']
                    m.fit_bounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]])

                st.success(f"✓ Calculated {distance_km:.0f} km reachable area!")

        # Show cached result
        elif 'last_result' in st.session_state:
            add_isodistance_to_map(m, st.session_state['last_result'], colors)
            if st.session_state['last_result'].get('bbox'):
                bbox = st.session_state['last_result']['bbox']
                m.fit_bounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]])

        st_folium(m, width=None, height=600, key="main_map")

    with col_info:
        st.subheader("ℹ️ Info")

        backend_name = "Valhalla (Local)" if use_valhalla else "OpenRouteService"
        st.markdown(f"""
        **Current Settings:**
        - 📍 `{lat:.4f}, {lon:.4f}`
        - 📏 `{distance_input:.0f} {distance_unit.lower()}`
        - 🚗 `{travel_mode}`
        - 🖥️ `{backend_name}`
        """)

        if 'last_params' in st.session_state:
            p = st.session_state['last_params']
            st.divider()
            st.markdown(f"""
            **Last Calculation:**
            - {p['distance_km']:.0f} km via {p['backend']}
            """)

        st.divider()

        if use_valhalla:
            st.markdown("""
            **🚀 Valhalla Backend**

            Running locally with **no limits**:
            - Any distance (1000km+)
            - Unlimited queries
            - No API keys needed
            - Works offline

            Data coverage depends on your OSM extract.
            """)
        else:
            st.markdown("""
            **☁️ OpenRouteService API**

            Cloud-based routing:
            - Max 150km distance
            - 2,000 requests/day
            - Requires API key

            For unlimited: run `./setup_valhalla.sh`
            """)


if __name__ == "__main__":
    main()
