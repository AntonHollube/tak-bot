import os
import json
from core.api_connector import fetch_opensky
from core.cot_builder import build_cot_event
from core.tak_network import send_cot_xml
from core.config import SYMBOLOGY

# Dateipfad für die Zustandsspeicherung
STATE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'airplane_state.json')

def push_live_traffic(lat, lon):
    """Fragt Live-Flugdaten ab und überträgt diese als Marker in das TAK-Netzwerk."""
    # Bounding Box definieren (ca. 50km)
    offset = 0.5 
    bbox = (lat - offset, lat + offset, lon - offset, lon + offset) 
    states = fetch_opensky(bbox) # API-Aufruf
    
    if not states:
        return

    # Limitierung auf 40 Objekte zur Vermeidung von Client-Freezes
    for s in states[:40]: 
        icao24 = s[0]
        callsign = str(s[1]).strip() if s[1] else "UNKNOWN"
        p_lon = s[5]
        p_lat = s[6]
        alt = s[7] if s[7] else 0
        speed = s[9] if s[9] else 0.0
        course = s[10] if s[10] else 0.0

        if p_lon is None or p_lat is None:
            continue # Ungültige Daten überspringen

        # CoT-Event generieren
        xml = build_cot_event(
            uid=f"flight-{icao24}", 
            cot_type=SYMBOLOGY.get("airplane", "a-n-A-C"),
            lat=p_lat,
            lon=p_lon,
            hae=alt,
            callsign=callsign,
            remarks=f"Live Telemetry | Speed: {speed} m/s",
            color="-256", 
            course=course,
            speed_mps=speed,
            stale_minutes=2 # Kurze Gültigkeit
        )
        send_cot_xml(xml) # Event senden

def execute(lat, lon, args):
    """Aktiviert oder deaktiviert das kontinuierliche Flugzeug-Tracking."""
    is_active = False
    
    # Vorherigen Zustand einlesen
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                is_active = json.load(f).get("active", False)
        except Exception:
            pass # Fehler ignorieren
            
    # Zustand invertieren
    new_state = not is_active
    
    # Neuen Zustand persistieren
    with open(STATE_FILE, "w") as f:
        json.dump({"active": new_state, "lat": lat, "lon": lon}, f)
        
    if new_state:
        # Initiale Ausführung erzwingen
        push_live_traffic(lat, lon)
        return "Tracking aktiviert (Updates minütlich im Hintergrund)", []
    else:
        return "Tracking deaktiviert", []