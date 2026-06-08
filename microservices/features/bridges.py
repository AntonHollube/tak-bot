import os
import requests
from core.feature_base import filter_pois_in_radius
from core.tak_network import upload_file
from core.config import SYMBOLOGY

IMAGE_CACHE = {}
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def process_and_upload_image(image_url, b_lat, b_lon):
    """
    Lädt Bilder von Wikimedia herunter, speichert diese lokal zwischen 
    und überträgt sie an den TAK-Server. Verwendet einen Hash-Cache, 
    um redundante Uploads zu vermeiden.
    """
    if not image_url or "File:" not in image_url:
        return None # URL ungültig
    if image_url in IMAGE_CACHE:
        return IMAGE_CACHE[image_url] # Cache-Hit
        
    try:
        # Direkte Bild-URL extrahieren
        filename = image_url.split("File:")[-1]
        raw_image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
        
        headers = {'User-Agent': 'TAK-Bot-Thesis/1.0'}
        img_response = requests.get(raw_image_url, headers=headers, stream=True, timeout=10)
        img_response.raise_for_status() # HTTP-Fehler prüfen
        
        # Bild lokal speichern
        local_path = os.path.join(TEMP_DIR, filename)
        with open(local_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)
                
        # Datei hochladen und Hash speichern
        file_hash = upload_file(local_path, b_lat, b_lon)
        if file_hash:
            IMAGE_CACHE[image_url] = file_hash
            return file_hash
    except Exception as e:
        print(f"[-] Fehler beim Bild-Upload: {e}")
    return None # Fallback

def _core_logic(lat, lon, args, with_images=False):
    """
    Filtert Brücken im Suchradius und kategorisiert sie anhand ihrer Traglast.
    Generiert spezifische Marker-Daten für die Darstellung in ATAK.
    """
    level = 1
    if args and args[0].isdigit():
        level = int(args[0]) # Radius-Level anpassen

    # H3-Filterung anwenden
    matched_entries = filter_pois_in_radius("bridges.json", lat, lon, level)
    found_bridges = []

    for entry in matched_entries:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})
        
        name = tags.get("name", "Unbekannte Bruecke")
        maxweight = tags.get("maxweight", "Unbekannt")
        
        # Standardwerte initialisieren
        color = "-16776961"
        status = "Normal"
        
        # Traglast-Logik auswerten
        if maxweight != "Unbekannt":
            try:
                w = float(maxweight.replace('t', '').strip()) # Wert parsen
                if w >= 30: 
                    color = "-16711936" # Befahrbar (Schwerlast)
                elif w >= 7.5: 
                    color = "-256"      # Eingeschraenkt
                else: 
                    color = "-65536"    # Gesperrt / Kritisch
                    status = "Kritisch/Gesperrt"
            except ValueError: 
                pass # Parse-Fehler ignorieren

        image_link = tags.get("image", "")
        image_hash = None
        remarks = f"Max Weight: {maxweight} | Status: {status}"
        
        # Optionaler Bild-Upload
        if with_images and image_link:
            image_hash = process_and_upload_image(image_link, entry["lat"], entry["lon"])
            if image_hash:
                remarks += " | (Bild in Attachments)"

        # Marker-Objekt aufbauen
        found_bridges.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': color, 'status': status, 'dist': entry["dist"],
            'remarks': remarks, 'image_hash': image_hash,
            'type': SYMBOLOGY.get("bridge", "a-u-G") # Punktmarker
        })

    if not found_bridges: 
        return f"Keine Bruecken im Radius Stufe {level} gefunden.", []
        
    return f"Sende {len(found_bridges)} Bruecke(n) an das ATAK-Lagebild...", found_bridges

def execute(lat, lon, args):
    """Führt die Standard-Brückensuche aus."""
    return _core_logic(lat, lon, args, with_images=False)

def execute_with_images(lat, lon, args):
    """Führt die Brückensuche inklusive asynchronem Bild-Download aus."""
    return _core_logic(lat, lon, args, with_images=True)