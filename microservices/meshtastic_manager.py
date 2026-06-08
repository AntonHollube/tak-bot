import sys
import time
import json
import os
from pubsub import pub
import meshtastic.serial_interface
import logging
from core.api_connector import fetch_weather
from core.geo_math import calculate_distance, calculate_bearing
from manager import ROOT_DIR
from dotenv import load_dotenv
import csv
from datetime import datetime, timezone

load_dotenv() # .env-Datei laden


# Optionales Link-Logging (nur aktiv, wenn MESH_LOG_CSV gesetzt ist)
MESH_LOG_CSV   = os.getenv("MESH_LOG_CSV")            # z.B. "mesh_measurements.csv"
MESH_LOG_LABEL = os.getenv("MESH_LOG_LABEL", "")      # z.B. "LoS_500m"
_CSV_FIELDS = ["timestamp_iso","epoch","label","from_id","portnum",
               "rx_rssi","rx_snr","hop_limit","lat","lon","text"]

def _log_packet(packet):
    if not MESH_LOG_CSV:
        return
    decoded = packet.get('decoded', {}) or {}
    portnum = decoded.get('portnum', "")
    text = decoded.get('text', "") if portnum == 'TEXT_MESSAGE_APP' else ""
    pos  = decoded.get('position', {}) or {}
    try:
        new_file = not os.path.exists(MESH_LOG_CSV) or os.path.getsize(MESH_LOG_CSV) == 0
        with open(MESH_LOG_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
            if new_file:
                w.writeheader()
            w.writerow({
                "timestamp_iso": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "epoch": round(time.time(), 3),
                "label": MESH_LOG_LABEL,
                "from_id": packet.get('fromId', ""),
                "portnum": portnum,
                "rx_rssi": packet.get('rxRssi'),
                "rx_snr": packet.get('rxSnr'),
                "hop_limit": packet.get('hopLimit'),
                "lat": pos.get('latitude'),
                "lon": pos.get('longitude'),
                "text": text,
            })
    except Exception as e:
        logging.error(f"[-] CSV-Log-Fehler: {e}")

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(levelname)s: %(message)s', 
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, "manager.log")), 
        logging.StreamHandler(sys.stdout)])


def get_compass_direction(degrees):
    """Konvertiert den berechneten Azimut-Winkel in Himmelsrichtungen."""
    if degrees is None:
        return "N/A"
    abbr = ["N", "NO", "O", "SO", "S", "SW", "W", "NW", "N"]
    return abbr[round(float(degrees) / 45) % 8]

def get_closest_poi(lat, lon, filename, poi_type):
    """
    Ermittelt das nächstgelegene Objekt über geodätische Distanz.
    Unterstützt dynamisch verschiedene JSON-Schemata (OSM Nodes, OSM Ways, PegelOnline).
    """
    json_path = os.path.join(os.path.dirname(__file__), 'data', filename)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"Fehler bei {poi_type}: {e}"

    closest_item = None
    min_dist = float('inf')

    for item in data:
        try:
            # Dynamische Extraktion für verschiedene API-Antwortformate
            lat_val = item.get("lat") or item.get("latitude") or item.get("center", {}).get("lat")
            lon_val = item.get("lon") or item.get("longitude") or item.get("center", {}).get("lon")
            
            if lat_val is None or lon_val is None:
                continue

            i_lat = float(lat_val)
            i_lon = float(lon_val)
        except (TypeError, ValueError):
            continue # Fehlerhafte Datensätze überspringen

        dist = calculate_distance(lat, lon, i_lat, i_lon)
        if dist < min_dist:
            min_dist = dist
            closest_item = item

    if closest_item:
        name = closest_item.get("shortname") or closest_item.get("tags", {}).get("name", "Unbekannt")
        
        # Erneute Extraktion für die Peilungsberechnung
        c_lat_val = closest_item.get("lat") or closest_item.get("latitude") or closest_item.get("center", {}).get("lat")
        c_lon_val = closest_item.get("lon") or closest_item.get("longitude") or closest_item.get("center", {}).get("lon")
        
        bearing = calculate_bearing(lat, lon, float(c_lat_val), float(c_lon_val))
        direction = get_compass_direction(bearing)
        dist_km = round(min_dist / 1000, 1)
        
        # Spezifische Daten-Extraktion
        extra_info = ""
        if filename == "pegel.json":
            for ts in closest_item.get("timeseries", []):
                if ts.get("shortname") == "W":
                    wert = ts.get("currentMeasurement", {}).get("value", "N/A")
                    extra_info = f" ({wert} cm)"
                    break
        
        return f"{poi_type} {name}{extra_info}: {dist_km}km Richtung {direction}"
        
    return f"Keine Daten fuer {poi_type} gefunden."

def on_receive(packet, interface):
    """Verarbeitet eingehende LoRa-Textnachrichten und routet die Befehle."""
    decoded = packet.get('decoded', {})
    if decoded.get('portnum') != 'TEXT_MESSAGE_APP':
        return

    text = decoded.get('text', '').strip()
    sender_id = packet.get('fromId')
    
    # Loopback-Schutz
    if sender_id == interface.getMyNodeInfo().get('user', {}).get('id'):
        return

    node_info = interface.nodes.get(sender_id, {})
    position = node_info.get('position', {})
    lat = position.get('latitude', 0.0)
    lon = position.get('longitude', 0.0)

    # Fallback bei fehlendem GPS-Fix
    if lat == 0.0 or lon == 0.0:
        lat, lon = 48.5748, 13.3802 

    reply_msg = ""
    cmd = text.lower()

    # Kommando-Routing (Prefix-sicher)
    if cmd.startswith('?w'):
        logging.info("[*] LoRa RX: '?w'. Lade Wetter...")
        weather_data = fetch_weather(lat, lon)
        if weather_data:
            temp = weather_data.get("current_weather", {}).get("temperature", "N/A")
            wind = weather_data.get("current_weather", {}).get("windspeed", "N/A")
            reply_msg = f"Wetter: {temp}C, {wind} km/h"
        else:
            reply_msg = "Wetter-API offline."

    elif cmd.startswith('?p'):
        logging.info("[*] LoRa RX: '?p'. Suche Pegel...")
        reply_msg = get_closest_poi(lat, lon, "pegel.json", "Pegel")
        
    elif cmd.startswith('?k'):
        logging.info("[*] LoRa RX: '?k'. Suche Klinik...")
        reply_msg = get_closest_poi(lat, lon, "hospitals.json", "Klinik")
        
    elif cmd.startswith('?i'):
        logging.info("[*] LoRa RX: '?i'. Suche Hotspot...")
        reply_msg = get_closest_poi(lat, lon, "wifi.json", "WLAN")

    elif cmd.startswith('?o'):
        logging.info("[*] LoRa RX: '?o'. Sende Position...")
        p_lat = position.get('latitude')
        p_lon = position.get('longitude')
        alt   = position.get('altitude')
        sats  = position.get('satsInView')
        if p_lat and p_lon:
            alt_str  = f", {alt} m" if alt is not None else ""
            sats_str = f" ({sats} Sat)" if sats is not None else ""
            reply_msg = f"Position: {p_lat:.5f}, {p_lon:.5f}{alt_str}{sats_str}"
        else:
            reply_msg = "Kein GPS-Fix verfuegbar."       

    if reply_msg:
        logging.info(f"[*] LoRa TX: '{reply_msg}'")
        time.sleep(1) # Rx/Tx-Switching Delay für LoRa-Hardware
        interface.sendText(reply_msg)
        logging.info("[+] Uebertragung abgeschlossen.")

def start_mesh_gateway():
    """Initialisiert das dedizierte Meshtastic-Edge-Gateway."""
    # Linux:
    port = os.getenv("MESH_PORT", "/dev/ttyACM0") 
    # port = "COM5" 
    logging.info(f"[*] Starte autarkes Meshtastic-Gateway an {port}...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(port)
        pub.subscribe(on_receive, "meshtastic.receive")
        logging.info("[+] Service aktiv. Lausche auf ?w, ?p, ?k, ?h.")
        
        while True:
            time.sleep(1) # Thread am Leben halten
    except Exception as e:
        logging.error(f"[-] Hardware-Fehler: {e}")

if __name__ == "__main__":
    start_mesh_gateway()