"""
Gemeinsame Basis fuer alle Feature-Module (Bruecken, Pegel, Wetter, KRITIS ...).

Marker-Vertrag
--------------
Ein Feature liefert (chat_text, marker_liste) zurueck. Jeder Marker ist ein dict,
das der bot_router an build_cot_event() weiterreicht. Erwartete Schluessel:

    name    (str)   Pflicht  - Anzeigename / Callsign-Basis des Markers
    lat     (float) Pflicht  - Breitengrad
    lon     (float) Pflicht  - Laengengrad
    type    (str)   optional - CoT-Typ (Default 'a-u-G'), via SYMBOLOGY
    color   (str)   optional - ARGB-Farbe (Default COLOR_BLUE), siehe config.COLOR_*
    remarks (str)   optional - Freitext fuer die ATAK-Detailansicht
    status  (str)   optional - Kurzstatus, nur fuer den remarks-Fallback im Router
    dist    (int)   optional - Distanz in Metern, nur fuer den remarks-Fallback
    course  (float) optional - Kurs in Grad (nur dynamische Objekte: Flug, Wind)
    speed   (float) optional - Geschwindigkeit in m/s (nur dynamische Objekte)
"""

import json
import logging
import os
import re
import h3
from core.h3_engine import get_search_area, H3_RESOLUTION
from core.geo_math import calculate_distance
from core.config import DATA_DIR

_UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def slugify(name):
    """Objektname -> dateisystemfreundlicher Slug (Umlaute aufgeloest, klein, Bindestriche).

    Eine Quelle der Wahrheit fuer Feature (liest <slug>.jpg) und Scanner (schreibt <slug>.jpg).
    """
    s = name.lower()
    for a, b in _UMLAUTS.items():
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def parse_level(args, default=1):
    """Liest die optionale Radius-Stufe (1-3) aus den Befehls-Argumenten."""
    if args and args[0].isdigit():
        return int(args[0])
    return default


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
    # 1. Fall: OSM Node (WLAN, Hotels, einfache Punkte)
    lat = poi.get("lat")
    lon = poi.get("lon")
    
    # 2. Fall: OSM Way / Polygon (Brücken, Tunnel, Flächen)
    # Wenn auf Ebene 1 nichts gefunden wurde, im "center"-Block suchen!
    if lat is None or lon is None:
        center = poi.get("center", {})
        lat = center.get("lat")
        lon = center.get("lon")
        
    return lat, lon


def filter_pois_in_radius(filename, user_lat, user_lon, level):
    """Zweistufiger Geofilter: H3-Zellzugehoerigkeit -> Haversine auf Kandidaten."""
    raw_data = load_json_data(filename)
    if not raw_data:
        return []
    if isinstance(raw_data, dict) and "elements" in raw_data:
        raw_data = raw_data["elements"]


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