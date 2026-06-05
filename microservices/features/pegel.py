from core.feature_base import filter_pois_in_radius
from core.config import SYMBOLOGY

def execute(lat, lon, args):
    """
    Fragt Wasserstandsdaten ab und klassifiziert diese dynamisch anhand 
    der behördlichen Meldestufen (MHW/MNW). Generiert farbcodierte 
    Warnmarker für das taktische Lagebild.
    """
    level = 1
    if args and args[0].isdigit():
        level = int(args[0]) # Radius anpassen

    matched_entries = filter_pois_in_radius("pegel.json", lat, lon, level)
    found_pegel = []

    for entry in matched_entries:
        p = entry["raw_data"]
        name = p.get("shortname", "Unbekannt")
        water = p.get("water", {}).get("shortname", "Unbekanntes Gewaesser")
        
        wert = "N/A"
        warn_status = "Normal"
        color = "-16776961" # Standard: Blau
        
        # Zeitreihen nach Wasserstand durchsuchen
        for ts in p.get("timeseries", []):
            if ts.get("shortname") == "W":
                measurement = ts.get("currentMeasurement", {})
                wert = measurement.get("value", "N/A")
                
                # Dynamische Auswertung der Warnstufen
                state = measurement.get("stateMnwMhw", "normal")
                
                if state == "high":
                    warn_status = "HOCHWASSER (MHW ueberschritten)"
                    color = "-65536" # Rot: Gefahr
                elif state == "low":
                    warn_status = "Niedrigwasser"
                    color = "-256"   # Gelb: Warnung
                    
                break # Nur aktuellsten Wert nutzen
                
        if wert == "N/A":
            continue # Ohne Messwert verwerfen
            
        remarks = f"Gewaesser: {water} | Pegel: {wert} cm | Status: {warn_status}"
        
        # Marker aufbauen
        found_pegel.append({
            'name': f"Pegel {name}", 
            'lat': entry["lat"], 
            'lon': entry["lon"],
            'color': color, 
            'status': f"{wert} cm",
            'dist': entry["dist"],
            'remarks': remarks,
            'type': SYMBOLOGY.get("pegel", "b-m-p-s-m") # Punktmarker
        })

    if not found_pegel:
        return f"Keine Pegelstationen im Radius Stufe {level} gefunden.", []
        
    chat_msg = f"{len(found_pegel)} Pegelstationen im Umkreis (Stufe {level}) abgefragt."
    return chat_msg, found_pegel