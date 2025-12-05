"""
Isodistance Map - Streamlit App

This app calculates how far you could travel along road networks from a starting point
and visualizes the reachable area on a map.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from scipy.spatial import ConvexHull
import numpy as np
import geopandas as gpd
from folium.plugins import Draw

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False

# Page configuration
st.set_page_config(
    page_title="Isodistance Map",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Isodistance Map Calculator")
st.markdown("""
This app shows you the actual area you could cover traveling a certain distance along roads.
Unlike a simple radius circle, this calculates reachable areas using real road networks.
""")


def get_network_graph(center_lat: float, center_lon: float, distance_km: float) -> nx.MultiDiGraph:
    """
    Download road network graph for the area.
    We need to download a slightly larger area to ensure we capture all reachable roads.
    """
    # Buffer the distance to ensure we get enough network
    buffer_distance = distance_km * 1000 * 1.3  # Convert to meters with buffer

    # Cap the download size to prevent very long downloads
    max_distance = 50000  # 50km max download radius
    buffer_distance = min(buffer_distance, max_distance)

    try:
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=buffer_distance,
            network_type='drive',  # Use 'walk' for walking, 'bike' for cycling
            simplify=True
        )
        return G
    except Exception as e:
        st.error(f"Error downloading road network: {e}")
        return None


def calculate_isodistance(G: nx.MultiDiGraph, center_lat: float, center_lon: float,
                          distance_m: float) -> list:
    """
    Calculate all nodes reachable within the given distance from the center point.
    Returns list of (lat, lon) tuples for reachable nodes.
    """
    # Find the nearest node to our center point
    center_node = ox.nearest_nodes(G, center_lon, center_lat)

    # Calculate shortest path distances from center to all nodes
    # Using Dijkstra's algorithm with edge length as weight
    distances = nx.single_source_dijkstra_path_length(G, center_node, cutoff=distance_m, weight='length')

    # Get coordinates of all reachable nodes
    reachable_points = []
    for node_id in distances.keys():
        node_data = G.nodes[node_id]
        reachable_points.append((node_data['y'], node_data['x']))  # lat, lon

    return reachable_points


def create_isodistance_polygon(points: list, method: str = 'concave') -> Polygon:
    """
    Create a polygon from the reachable points.
    """
    if len(points) < 3:
        return None

    points_array = np.array(points)

    if method == 'convex':
        # Simple convex hull
        try:
            hull = ConvexHull(points_array)
            hull_points = points_array[hull.vertices]
            return Polygon(hull_points)
        except Exception:
            return None
    else:
        # Concave hull using alpha shape (better representation)
        try:
            # Create a GeoDataFrame with points
            geometry = [Point(lon, lat) for lat, lon in points]
            gdf = gpd.GeoDataFrame(geometry=geometry, crs="EPSG:4326")

            # Buffer each point slightly and union them for a more accurate shape
            # The buffer size is proportional to the density of points
            if len(points) > 0:
                # Calculate approximate point density
                lat_range = points_array[:, 0].max() - points_array[:, 0].min()
                lon_range = points_array[:, 1].max() - points_array[:, 1].min()
                area = max(lat_range, 0.001) * max(lon_range, 0.001)
                buffer_size = np.sqrt(area / len(points)) * 1.5
                buffer_size = max(buffer_size, 0.0005)  # Minimum buffer
                buffer_size = min(buffer_size, 0.01)    # Maximum buffer

                # Buffer and union
                buffered = gdf.geometry.buffer(buffer_size)
                unified = unary_union(buffered)

                # Simplify the result
                simplified = unified.simplify(buffer_size / 2)
                return simplified
        except Exception as e:
            # Fall back to convex hull
            try:
                hull = ConvexHull(points_array)
                hull_points = points_array[hull.vertices]
                return Polygon([(p[1], p[0]) for p in hull_points])  # lon, lat for Polygon
            except Exception:
                return None

    return None


def add_polygon_to_map(m: folium.Map, polygon, color: str = '#3388ff',
                       fill_opacity: float = 0.35):
    """
    Add a polygon (or multipolygon) to the folium map.
    """
    if polygon is None:
        return

    if isinstance(polygon, MultiPolygon):
        for poly in polygon.geoms:
            coords = [(lat, lon) for lon, lat in poly.exterior.coords]
            folium.Polygon(
                locations=coords,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=fill_opacity,
                popup="Reachable Area"
            ).add_to(m)
    elif isinstance(polygon, Polygon):
        coords = [(lat, lon) for lon, lat in polygon.exterior.coords]
        folium.Polygon(
            locations=coords,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity,
            popup="Reachable Area"
        ).add_to(m)


def main():
    # Sidebar for inputs
    with st.sidebar:
        st.header("⚙️ Settings")

        st.subheader("📍 Starting Location")

        # Location input method
        location_method = st.radio(
            "Choose input method:",
            ["Enter coordinates", "Search by place name", "Click on map"]
        )

        if location_method == "Enter coordinates":
            col1, col2 = st.columns(2)
            with col1:
                lat = st.number_input("Latitude", value=51.5074, format="%.6f",
                                      min_value=-90.0, max_value=90.0)
            with col2:
                lon = st.number_input("Longitude", value=-0.1278, format="%.6f",
                                      min_value=-180.0, max_value=180.0)

        elif location_method == "Search by place name":
            place_name = st.text_input("Enter place name", "London, UK")
            if place_name:
                try:
                    location = ox.geocode(place_name)
                    lat, lon = location
                    st.success(f"Found: {lat:.4f}, {lon:.4f}")
                except Exception as e:
                    st.error("Could not find location. Please try another search.")
                    lat, lon = 51.5074, -0.1278
            else:
                lat, lon = 51.5074, -0.1278

        else:  # Click on map
            st.info("Click on the map to set your starting point")
            lat = st.session_state.get('clicked_lat', 51.5074)
            lon = st.session_state.get('clicked_lon', -0.1278)
            st.write(f"Current: {lat:.4f}, {lon:.4f}")

        st.divider()

        st.subheader("📏 Distance")

        # Distance input
        distance_unit = st.selectbox("Unit", ["Kilometers", "Miles", "Meters"])

        if distance_unit == "Kilometers":
            distance_input = st.number_input("Distance (km)", min_value=0.1, max_value=100.0,
                                             value=5.0, step=0.5)
            distance_m = distance_input * 1000
        elif distance_unit == "Miles":
            distance_input = st.number_input("Distance (miles)", min_value=0.1, max_value=62.0,
                                             value=3.0, step=0.5)
            distance_m = distance_input * 1609.34
        else:
            distance_input = st.number_input("Distance (meters)", min_value=100, max_value=100000,
                                             value=5000, step=100)
            distance_m = distance_input

        st.divider()

        st.subheader("🎨 Display Options")

        # Network type
        network_type = st.selectbox(
            "Travel mode",
            ["Drive", "Walk", "Bike", "All roads"],
            help="Type of road network to use"
        )
        network_type_map = {
            "Drive": "drive",
            "Walk": "walk",
            "Bike": "bike",
            "All roads": "all"
        }

        # Color picker
        area_color = st.color_picker("Area color", "#3388ff")

        # Opacity
        fill_opacity = st.slider("Fill opacity", 0.1, 0.8, 0.35)

        # Polygon method
        polygon_method = st.selectbox(
            "Shape method",
            ["Smooth (concave)", "Simple (convex)"],
            help="How to draw the reachable area boundary"
        )

        st.divider()

        # Calculate button
        calculate_btn = st.button("🚀 Calculate Reachable Area", type="primary",
                                  use_container_width=True)

    # Main content area
    col_map, col_info = st.columns([3, 1])

    with col_map:
        # Create the base map
        m = folium.Map(location=[lat, lon], zoom_start=12)

        # Add marker for starting point
        folium.Marker(
            [lat, lon],
            popup=f"Start: ({lat:.4f}, {lon:.4f})",
            tooltip="Starting Point",
            icon=folium.Icon(color='red', icon='play')
        ).add_to(m)

        # Add draw control for clicking
        if location_method == "Click on map":
            Draw(
                draw_options={
                    'polyline': False,
                    'polygon': False,
                    'circle': False,
                    'rectangle': False,
                    'circlemarker': False,
                    'marker': True
                },
                edit_options={'edit': False}
            ).add_to(m)

        # Handle calculation
        if calculate_btn:
            with st.spinner("Downloading road network... This may take a moment."):
                # Download network
                try:
                    G = ox.graph_from_point(
                        (lat, lon),
                        dist=min(distance_m * 1.3, 50000),
                        network_type=network_type_map[network_type],
                        simplify=True
                    )
                except Exception as e:
                    st.error(f"Error downloading road network: {e}")
                    G = None

            if G is not None:
                with st.spinner("Calculating reachable area..."):
                    # Calculate isodistance
                    reachable_points = calculate_isodistance(G, lat, lon, distance_m)

                    if len(reachable_points) >= 3:
                        # Create polygon
                        method = 'concave' if 'concave' in polygon_method.lower() else 'convex'
                        polygon = create_isodistance_polygon(reachable_points, method)

                        # Add to map
                        add_polygon_to_map(m, polygon, area_color, fill_opacity)

                        # Add points as a subtle layer
                        for point in reachable_points[::max(1, len(reachable_points)//200)]:
                            folium.CircleMarker(
                                location=point,
                                radius=2,
                                color=area_color,
                                fill=True,
                                opacity=0.3
                            ).add_to(m)

                        # Fit bounds
                        if polygon is not None:
                            bounds = polygon.bounds  # minx, miny, maxx, maxy
                            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

                        # Store results in session state
                        st.session_state['last_calculation'] = {
                            'num_points': len(reachable_points),
                            'distance_m': distance_m,
                            'network_type': network_type
                        }

                        st.success(f"Found {len(reachable_points)} reachable road intersections!")
                    else:
                        st.warning("Not enough road network data found for this location.")

        # Display the map
        map_data = st_folium(m, width=None, height=600, key="main_map")

        # Handle map clicks
        if map_data and map_data.get('last_clicked'):
            clicked = map_data['last_clicked']
            st.session_state['clicked_lat'] = clicked['lat']
            st.session_state['clicked_lon'] = clicked['lng']

    with col_info:
        st.subheader("ℹ️ Information")

        st.markdown(f"""
        **Current Settings:**
        - 📍 Location: ({lat:.4f}, {lon:.4f})
        - 📏 Distance: {distance_input} {distance_unit.lower()}
        - 🚗 Mode: {network_type}
        """)

        if 'last_calculation' in st.session_state:
            calc = st.session_state['last_calculation']
            st.markdown(f"""
            **Last Calculation:**
            - Road points found: {calc['num_points']}
            - Distance used: {calc['distance_m']/1000:.1f} km
            """)

        st.divider()

        st.markdown("""
        **How it works:**
        1. Downloads real road network data from OpenStreetMap
        2. Calculates all reachable points within your distance using Dijkstra's algorithm
        3. Creates a polygon encompassing the reachable area

        **Tips:**
        - Larger distances take longer to calculate
        - Urban areas have denser road networks
        - Try different travel modes for different results
        """)


if __name__ == "__main__":
    main()
