from core.feature_base import filter_pois_in_radius
from core.config import SYMBOLOGY

def execute_tunnel(lat, lon, args):
    """
    Identifiziert und filtert Tunnelbauwerke im Einsatzgebiet zur Gefahrenprävention 
    bei potenziellen Sturzfluten. Verwendet ein graues Farbschema und spezifische 
    CoT-Infrastruktur-Typen zur visuellen Abgrenzung von oberirdischen Straßen.
    """
    level = 1
    if args and args[0].isdigit():
        level = int(args[0]) # Radius anpassen

    matched = filter_pois_in_radius("tunnels.json", lat, lon, level)
    results = []

    for entry in matched:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})
        
        name = tags.get("name", "Unterfuehrung/Tunnel")
        lit = tags.get("lit", "Unbekannt")
        
        results.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': "-8355712", # Dunkelgrau markieren
            'status': "Tunnel", 'dist': entry["dist"],
            'remarks': f"Tunnel/Unterfuehrung | Beleuchtet: {lit} | Distanz: {entry['dist']}m",
            'type': SYMBOLOGY.get("kritis_tunnel", "a-u-U") # MIL-STD Underground
        })

    if not results: 
        return f"Keine Tunnel/Unterfuehrungen im Radius Stufe {level} gefunden.", []
        
    return f"{len(results)} Tunnel/Unterfuehrungen im Umkreis markiert.", results


def execute_wifi(lat, lon, args):
    """
    Lokaliert öffentliche WLAN-Hotspots als Kommunikations-Fallback 
    bei Ausfällen ziviler Mobilfunknetze (Off-Grid-Szenarien).
    Markiert diese taktisch als unbekannte Bodenobjekte in Magenta.
    """
    level = 1
    if args and args[0].isdigit():
        level = int(args[0]) # Radius anpassen

    matched = filter_pois_in_radius("wifi.json", lat, lon, level)
    results = []

    for entry in matched:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})
        
        name = tags.get("name", "Oeffentlicher WLAN Spot")
        operator = tags.get("operator", "Frei/Unbekannt")
        
        results.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': "-65281", # Magenta für Funk
            'status': "WLAN-Hotspot", 'dist': entry["dist"],
            'remarks': f"Notfall-Konnektivitaet | Betreiber: {operator}",
            'type': 'a-u-G' # Unbekanntes Bodenobjekt
        })

    if not results: 
        return f"Keine WLAN-Spots im Radius Stufe {level} gefunden.", []
        
    return f"{len(results)} Kommunikations-WLAN-Hotspots auf Karte uebertragen.", results


def execute_hospital(lat, lon, args):
    """
    Extrahiert medizinische Einrichtungen zur Evakuierungs- und MANV-Planung.
    Implementiert das dedizierte MIL-STD CoT-Symbol (Friend Ground Medical Facility), 
    welches vom ATAK-Client nativ als Sanitätskreuz gerendert wird.
    """
    level = 1
    if args and args[0].isdigit():
        level = int(args[0]) # Radius anpassen

    matched = filter_pois_in_radius("hospitals.json", lat, lon, level)
    results = []

    for entry in matched:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})
        
        name = tags.get("name", "Krankenhaus / Med. Einrichtung")
        emergency = tags.get("emergency", "Unbekannt")
        
        results.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': "-16776961", # Blau (wird ueberschrieben)
            'status': "Krankenhaus", 'dist': entry["dist"],
            'remarks': f"Medizinische Einrichtung | Notaufnahme-Status: {emergency}",
            'type': 'a-n-G-I-M' # MIL-STD Medical Facility
        })

    if not results: 
        return f"Keine Krankenhaeuser im Radius Stufe {level} gefunden.", []
        
    return f"{len(results)} medizinische KRITIS-Einrichtungen ins Lagebild eingespeist.", results