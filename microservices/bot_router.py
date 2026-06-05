import logging
import uuid
from datetime import datetime, timezone, timedelta

from core.cot_builder import build_cot_event
from core.tak_network import get_api  
from features import bridges, help, weather, pegel, airplanes, kritis

# Mapping von Chat-Befehlen auf die Module
COMMAND_REGISTRY = {
    "!b": bridges.execute,
    "!bridge": bridges.execute,
    "!b+": bridges.execute_with_images,
    "!w": weather.execute,       
    "!weather": weather.execute, 
    "!p": pegel.execute,
    "!pegel": pegel.execute,
    "!h": help.execute,
    "!help": help.execute,
    "!a": airplanes.execute,         
    "!airplane": airplanes.execute,
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

def build_chat_xml(message):
    """Erstellt ein valides CoT-XML für den globalen Chat-Broadcast."""
    now_dt = datetime.now(timezone.utc)
    stale_dt = now_dt + timedelta(minutes=10) # 10 Min Gültigkeit
    
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    stale = stale_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    msg_id = str(uuid.uuid4()) # Eindeutige ID
    
    # Sanitization gegen defekte XML-Tags
    safe_message = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Formatieres CoT-Event zurückgeben
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0" uid="GeoChat.TAK-Bot.AllChatRooms.{msg_id}" type="b-t-f" time="{now}" start="{now}" stale="{stale}" how="h-g-i-g-o">
    <point lat="0.0" lon="0.0" hae="0.0" ce="9999999.0" le="9999999.0"/>
    <detail>
        <__chat parent="RootContactGroup" groupOwner="false" messageId="{msg_id}" chatroom="Alle Chaträume" id="All Chat Rooms" senderCallsign="TAK-Bot">
            <chatgrp uid0="TAK-Bot" uid1="All Chat Rooms" id="All Chat Rooms"/>
        </__chat>
        <remarks source="BAO.F.ATAK.TAK-Bot" to="All Chat Rooms" time="{now}">{safe_message}</remarks>
    </detail>
</event>"""

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
        
        chat_msg, marker_data = COMMAND_REGISTRY[base_cmd](lat, lon, args)
        
        chat_xml = None
        if chat_msg:
            logging.info(f"[*] Generiere Chat-Antwort für {base_cmd}") 
            chat_xml = build_chat_xml(chat_msg) # Chat-Antwort generieren
        
        marker_xmls = []
        # Marker aus den Modul-Daten aufbauen
        for m in marker_data:
            fallback_remarks = f"Status: {m.get('status', 'N/A')} | Distanz: {m.get('dist', '0')}m"
            
            xml = build_cot_event(
                uid=f"bot-mark-{m['name']}-{m['lat']}",
                cot_type=m.get('type', 'b-m-p-s-m'),
                lat=m['lat'],
                lon=m['lon'],
                callsign=f"{m['name']} (Bot)",
                remarks=m.get('remarks', fallback_remarks),
                color=m.get('color', '-16776961'),
                course=m.get('course'),   
                speed_mps=m.get('speed'),
                image_hash=m.get('image_hash')   
            )
            marker_xmls.append(xml)
            
        return chat_xml, marker_xmls
    
    # Fallback bei unbekannten Befehlen
    logging.info(f"[*] Befehl '{base_cmd}' unbekannt.")
    help_msg, _ = help.execute(lat, lon, [])
    return build_chat_xml(f"Befehl '{base_cmd}' unbekannt.\n{help_msg}"), []