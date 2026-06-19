"""Routet eingehende !-Chat-Befehle an die Feature-Module und baut die CoT-Antworten."""
import logging

from core.cot_builder import build_cot_event, build_chat_event
from core.tak_network import get_api
from core.config import COLOR_BLUE
from core import media_package
from features import bridges, help, weather, pegel, kritis

# Mapping von Chat-Befehlen auf die Module
COMMAND_REGISTRY = {
    "!b": bridges.execute,
    "!bridge": bridges.execute,
    "!w": weather.execute,
    "!weather": weather.execute, 
    "!p": pegel.execute,
    "!pegel": pegel.execute,
    "!h": help.execute,
    "!help": help.execute,
"!t": kritis.execute_tunnel,
    "!tunnel": kritis.execute_tunnel,
    "!wifi": kritis.execute_wifi,
    "!wlan": kritis.execute_wifi,
    "!hosp": kritis.execute_hospital,
    "!klinik": kritis.execute_hospital,
}

def get_real_location(uid):
    """Ermittelt die letzte bekannte GPS-Position eines Nutzers über die TAK REST-API."""
    try:
        response = get_api(f"/Marti/api/cot/xml/{uid}") # API Call
        if response:
            # JSON-Struktur auslesen
            event_data = response[0] if isinstance(response, list) else response.get("data", [response])[0]
            
            point = event_data.get("point", {})
            lat = float(point.get("lat", 0.0))
            lon = float(point.get("lon", 0.0))
            
            if lat != 0.0 and lon != 0.0:
                return lat, lon # Korrekte Koordinaten
            else:
                logging.error(f"[-] UID {uid}: Keine gültigen Koordinaten in der API-Antwort.")
    except Exception as e:
        logging.error(f"[-] Fehler beim Location-Lookup für {uid}: {e}")
    
    return 0.0, 0.0 # Fallback

def route_command(cmd_string, lat, lon, target_uid):
    """Leitet eingehende Befehle an das passende Feature-Modul weiter."""
    parts = cmd_string.split()
    if not parts:
        return None, []

    base_cmd = parts[0].lower() # Befehl extrahieren
    args = parts[1:]

    # Position nachträglich holen, falls im Chat-Event fehlend
    if lat == 0.0 and lon == 0.0:
        lat, lon = get_real_location(target_uid)

    if base_cmd in COMMAND_REGISTRY:
        logging.info(f"[*] Führe {base_cmd} aus (Lat: {lat}, Lon: {lon}, UID: {target_uid})")
        
        chat_msg, markers = COMMAND_REGISTRY[base_cmd](lat, lon, args)

        chat_xml = None
        if chat_msg:
            logging.info(f"[*] Generiere Chat-Antwort für {base_cmd}")
            chat_xml = build_chat_event(chat_msg) # Chat-Antwort generieren

        marker_xmls = []
        # Marker aus den Modul-Daten aufbauen
        for m in markers:
            fallback_remarks = f"Status: {m.get('status', 'N/A')} | Distanz: {m.get('dist', '0')}m"
            safe_uid = f"bot-mark-{m['lat']}-{m['lon']}"
            callsign = f"{m['name']} (Bot)"
            remarks = m.get('remarks', fallback_remarks)

            # FA7: Marker mit hinterlegtem Bild als Data-Package-Anhang ausliefern.
            # Der paket-interne Marker trägt dieselbe ortsbasierte UID -> idempotent (kein Dublett).
            if m.get('image'):
                try:
                    marker_xmls.append(media_package.attach_image(
                        image_path=m['image'], callsign=callsign,
                        lat=m['lat'], lon=m['lon'],
                        cot_type=m.get('type', 'a-u-G'),
                        color=m.get('color', COLOR_BLUE),
                        remarks=remarks, uid=safe_uid,
                    ))
                    continue  # Plain-Marker entfällt; der Anhang-Marker ersetzt ihn
                except Exception as e:
                    logging.error(f"[-] Bildanhang fehlgeschlagen ({m['name']}): {e}; sende Plain-Marker.")

            marker_xmls.append(build_cot_event(
                uid=safe_uid,
                cot_type=m.get('type', 'a-u-G'),
                lat=m['lat'],
                lon=m['lon'],
                callsign=callsign,
                remarks=remarks,
                color=m.get('color', COLOR_BLUE),
                course=m.get('course'),
                speed_mps=m.get('speed')
            ))

        return chat_xml, marker_xmls
    
    # Fallback bei unbekannten Befehlen
    logging.info(f"[*] Befehl '{base_cmd}' unbekannt.")
    help_msg, _ = help.execute(lat, lon, [])
    return build_chat_event(f"Befehl '{base_cmd}' unbekannt.\n{help_msg}"), []