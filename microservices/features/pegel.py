"""Pegel-Feature: Flusspegel im Umkreis abfragen und nach Meldestufe einfaerben."""
from core.feature_base import filter_pois_in_radius, parse_level
from core.config import SYMBOLOGY, COLOR_RED, COLOR_YELLOW, COLOR_BLUE

def execute(lat, lon, args):
    """Fragt Pegel im Umkreis ab und faerbt sie nach behoerdlicher Meldestufe (MHW/MNW) ein."""
    level = parse_level(args)

    entries = filter_pois_in_radius("pegel.json", lat, lon, level)
    markers = []

    for entry in entries:
        p = entry["raw_data"]
        name = p.get("shortname", "Unbekannt")
        water = p.get("water", {}).get("shortname", "Unbekanntes Gewaesser")
        
        wert = "N/A"
        warn_status = "Normal"
        color = COLOR_BLUE # Standard
        
        # Zeitreihen nach Wasserstand durchsuchen
        for ts in p.get("timeseries", []):
            if ts.get("shortname") == "W":
                measurement = ts.get("currentMeasurement", {})
                wert = measurement.get("value", "N/A")
                
                # Dynamische Auswertung der Warnstufen
                state = measurement.get("stateMnwMhw", "normal")
                
                if state == "high":
                    warn_status = "HOCHWASSER (MHW ueberschritten)"
                    color = COLOR_RED
                elif state == "low":
                    warn_status = "Niedrigwasser"
                    color = COLOR_YELLOW
                    
                break # Nur aktuellsten Wert nutzen
                
        if wert == "N/A":
            continue # Ohne Messwert verwerfen
            
        remarks = f"Gewaesser: {water} | Pegel: {wert} cm | Status: {warn_status}"
        
        # Marker aufbauen
        markers.append({
            'name': f"Pegel {name}", 
            'lat': entry["lat"], 
            'lon': entry["lon"],
            'color': color, 
            'status': f"{wert} cm",
            'dist': entry["dist"],
            'remarks': remarks,
            'type': SYMBOLOGY.get("pegel", "b-m-p-s-m") # Punktmarker
        })

    if not markers:
        return f"Keine Pegelstationen im Radius Stufe {level} gefunden.", []

    chat_msg = f"{len(markers)} Pegelstationen im Umkreis (Stufe {level}) abgefragt."
    return chat_msg, markers