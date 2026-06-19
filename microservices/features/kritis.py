"""KRITIS-Features: Tunnel, WLAN-Hotspots und Kliniken im Umkreis als Marker."""
from core.feature_base import filter_pois_in_radius, parse_level
from core.config import SYMBOLOGY, COLOR_BLUE, COLOR_GRAY, COLOR_MAGENTA

def execute_tunnel(lat, lon, args):
    """Markiert Tunnel/Unterfuehrungen im Umkreis (relevant bei Sturzfluten)."""
    level = parse_level(args)

    entries = filter_pois_in_radius("tunnels.json", lat, lon, level)
    markers = []

    for entry in entries:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})

        name = tags.get("name", "Unterfuehrung/Tunnel")
        lit = tags.get("lit", "Unbekannt")

        markers.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': COLOR_GRAY,
            'status': "Tunnel", 'dist': entry["dist"],
            'remarks': f"Tunnel/Unterfuehrung | Beleuchtet: {lit} | Distanz: {entry['dist']}m",
            'type': SYMBOLOGY.get("kritis_tunnel", "a-u-G")
        })

    if not markers:
        return f"Keine Tunnel/Unterfuehrungen im Radius Stufe {level} gefunden.", []

    return f"{len(markers)} Tunnel/Unterfuehrungen im Umkreis markiert.", markers


def execute_wifi(lat, lon, args):
    """Markiert oeffentliche WLAN-Hotspots als Kommunikations-Fallback (Off-Grid)."""
    level = parse_level(args)

    entries = filter_pois_in_radius("wifi.json", lat, lon, level)
    markers = []

    for entry in entries:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})

        name = tags.get("name", "Oeffentlicher WLAN Spot")
        operator = tags.get("operator", "Frei/Unbekannt")

        markers.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': COLOR_MAGENTA,
            'status': "WLAN-Hotspot", 'dist': entry["dist"],
            'remarks': f"Notfall-Konnektivitaet | Betreiber: {operator}",
            'type': SYMBOLOGY.get("kritis_wifi", "a-u-G") # Unbekanntes Bodenobjekt
        })

    if not markers:
        return f"Keine WLAN-Spots im Radius Stufe {level} gefunden.", []

    return f"{len(markers)} Kommunikations-WLAN-Hotspots auf Karte uebertragen.", markers


def execute_hospital(lat, lon, args):
    """Markiert Kliniken/med. Einrichtungen (MIL-STD-Symbol, als Sanitaetskreuz gerendert)."""
    level = parse_level(args)

    entries = filter_pois_in_radius("hospitals.json", lat, lon, level)
    markers = []

    for entry in entries:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})

        name = tags.get("name", "Krankenhaus / Med. Einrichtung")
        emergency = tags.get("emergency", "Unbekannt")

        markers.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': COLOR_BLUE,
            'status': "Krankenhaus", 'dist': entry["dist"],
            'remarks': f"Medizinische Einrichtung | Notaufnahme-Status: {emergency}",
            'type': SYMBOLOGY.get("kritis_hospital", "a-n-G-I-M") # MIL-STD Medical Facility
        })

    if not markers:
        return f"Keine Krankenhaeuser im Radius Stufe {level} gefunden.", []

    return f"{len(markers)} medizinische KRITIS-Einrichtungen ins Lagebild eingespeist.", markers