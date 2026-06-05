import json
import logging
import os
import h3
from core.h3_engine import get_search_area, H3_RESOLUTION
from core.geo_math import calculate_distance

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')


def load_json_data(filename):
    """Laedt JSON-Daten aus dem lokalen Cache und faengt Dateifehler ab."""
    file_path = os.path.join(DATA_DIR, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"[-] Cache fehlt: {filename} nicht gefunden.")
        return []
    except json.JSONDecodeError:
        logging.error(f"[-] Cache beschaedigt: {filename} nicht parsebar.")
        return []


def extract_coordinates(poi):
    """Extrahiert (lat, lon) aus heterogenen JSON-Schemata (OSM-center / flach)."""
    center = poi.get("center")
    if isinstance(center, dict):
        return center.get("lat"), center.get("lon")
    # dict.get(key, default) liefert auch den Wert 0.0 korrekt zurueck.
    lat = poi.get("latitude", poi.get("lat"))
    lon = poi.get("longitude", poi.get("lon"))
    return lat, lon


def filter_pois_in_radius(filename, user_lat, user_lon, level):
    """Zweistufiger Geofilter: H3-Zellzugehoerigkeit -> Haversine auf Kandidaten."""
    raw_data = load_json_data(filename)
    if not raw_data:
        return []

    valid_hexagons = get_search_area(user_lat, user_lon, level)  # Stufe 1: O(1)-Set
    filtered_pois = []

    for item in raw_data:
        lat, lon = extract_coordinates(item)
        if lat is None or lon is None:
            continue  # Koordinate fehlt -> verwerfen (0.0 bleibt gueltig)
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue  # nicht-numerische Koordinate -> verwerfen

        try:
            poi_hex = h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
        except AttributeError:
            poi_hex = h3.geo_to_h3(lat, lon, H3_RESOLUTION)

        if poi_hex in valid_hexagons:  # Stufe 2: nur Kandidaten erreichen Haversine
            dist = int(calculate_distance(user_lat, user_lon, lat, lon))
            filtered_pois.append({"raw_data": item, "lat": lat, "lon": lon, "dist": dist})

    return sorted(filtered_pois, key=lambda x: x["dist"])