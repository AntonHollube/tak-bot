import os
import logging
import requests
from core.feature_base import filter_pois_in_radius
from core.tak_network import upload_file
from core.config import SYMBOLOGY

IMAGE_CACHE = {}
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)


def process_and_upload_image(image_url, b_lat, b_lon):
    """Laedt ein Wikimedia-Bild, laedt es zum TAK-Server hoch und cached den Hash."""
    if not image_url or "File:" not in image_url:
        return None
    if image_url in IMAGE_CACHE:
        return IMAGE_CACHE[image_url]

    local_path = None
    try:
        filename = image_url.split("File:")[-1]
        raw_image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
        headers = {'User-Agent': 'TAK-Bot-Thesis/1.0'}
        img_response = requests.get(raw_image_url, headers=headers, stream=True, timeout=10)
        img_response.raise_for_status()

        local_path = os.path.join(TEMP_DIR, os.path.basename(filename))
        with open(local_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)

        file_hash = upload_file(local_path, b_lat, b_lon)
        if file_hash:
            IMAGE_CACHE[image_url] = file_hash
            return file_hash
    except Exception as e:
        logging.error(f"[-] Fehler beim Bild-Upload: {e}")
    finally:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)  # Temp-Datei aufraeumen
            except OSError:
                pass
    return None


def _classify_maxweight(maxweight):
    """Bildet die Traglast auf (Farbe, Status) ab. ARGB-Ampellogik."""
    if maxweight == "Unbekannt":
        return "-16776961", "Unbekannt"          # Blau
    try:
        w = float(maxweight.replace('t', '').replace(',', '.').strip())
    except ValueError:
        return "-16776961", "Unbekannt (Parsefehler)"
    if w >= 30:
        return "-16711936", "Befahrbar (Schwerlast)"   # Gruen
    if w >= 7.5:
        return "-256", "Eingeschraenkt"                 # Gelb
    return "-65536", "Gesperrt/Kritisch"                # Rot


def _core_logic(lat, lon, args, with_images=False):
    """Filtert Bruecken im Suchradius und kategorisiert sie nach Traglast."""
    level = 1
    if args and args[0].isdigit():
        level = int(args[0])

    matched_entries = filter_pois_in_radius("bridges.json", lat, lon, level)
    found_bridges = []

    for entry in matched_entries:
        poi = entry["raw_data"]
        tags = poi.get("tags", {})
        name = tags.get("name", "Unbekannte Bruecke")
        maxweight = tags.get("maxweight", "Unbekannt")        
        color, status = _classify_maxweight(maxweight)

        image_link = tags.get("image", "")
        image_hash = None
        remarks = f"Max Weight: {maxweight} | Status: {status}"

        if with_images and image_link:
            image_hash = process_and_upload_image(image_link, entry["lat"], entry["lon"])
            if image_hash:
                remarks += " | (Bild in Attachments)"

        found_bridges.append({
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': color, 'status': status, 'dist': entry["dist"],
            'remarks': remarks, 'image_hash': image_hash,
            'type': SYMBOLOGY.get("bridge", "S*G*IMNB--H****")
        })

    if not found_bridges:
        return f"Keine Bruecken im Radius Stufe {level} gefunden.", []
    return f"Sende {len(found_bridges)} Bruecke(n) an das ATAK-Lagebild...", found_bridges


def execute(lat, lon, args):
    return _core_logic(lat, lon, args, with_images=False)


def execute_with_images(lat, lon, args):
    return _core_logic(lat, lon, args, with_images=True)