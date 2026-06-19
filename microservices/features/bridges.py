"""Bruecken-Feature: Bruecken im Umkreis nach Traglast (Ampelfarben) markieren."""
import os

from core.feature_base import filter_pois_in_radius, parse_level, slugify
from core.config import SYMBOLOGY, DATA_DIR, COLOR_RED, COLOR_YELLOW, COLOR_GREEN, COLOR_BLUE, COLOR_MAGENTA

# Lokale Bildablage je Brücke (FA7). Dateiname = slugify(Brückenname).<jpg|jpeg|png>.
# Bewusst nur lokal: Features bleiben netzfrei (externe I/O macht der image_scanner, vgl. NFA5/Cache-Aside).
IMG_DIR = os.path.join(DATA_DIR, "bridge_images")


def _find_image(name):
    """Sucht ein hinterlegtes Bild zur Brücke; gibt den Pfad oder None zurück."""
    slug = slugify(name)
    for ext in ("jpg", "jpeg", "png"):
        path = os.path.join(IMG_DIR, f"{slug}.{ext}")
        if os.path.exists(path):
            return path
    return None


def _classify_maxweight(maxweight):
    """Bildet die Traglast auf (Farbe, Status) ab. ARGB-Ampellogik."""
    if maxweight == "Unbekannt":
        return COLOR_BLUE, "Unbekannt"
    try:
        w = float(maxweight.replace('t', '').replace(',', '.').strip())
    except ValueError:
        return COLOR_BLUE, "Unbekannt (Parsefehler)"
    if w >= 30:
        return COLOR_GREEN, "Befahrbar (Schwerlast)"
    if w >= 7.5:
        return COLOR_YELLOW, "Eingeschraenkt"
    return COLOR_RED, "Gesperrt/Kritisch"


def execute(lat, lon, args):
    """Filtert Bruecken im Suchradius und kategorisiert sie nach Traglast."""
    level = parse_level(args)

    entries = filter_pois_in_radius("bridges.json", lat, lon, level)
    markers = []
    seen_names = set()  # OSM fuehrt eine Bruecke oft als mehrere Wege -> je Name nur einmal

    for entry in entries:  # nach Distanz sortiert: die erste (naechste) Instanz gewinnt
        poi = entry["raw_data"]
        tags = poi.get("tags", {})
        name = tags.get("name", "Unbekannte Bruecke")
        # benannte Dubletten ueberspringen; unbenannte Bruecken sind echte Einzelobjekte -> behalten
        if name != "Unbekannte Bruecke":
            if name in seen_names:
                continue
            seen_names.add(name)
        maxweight = tags.get("maxweight", "Unbekannt")
        color, status = _classify_maxweight(maxweight)

        marker = {
            'name': name, 'lat': entry["lat"], 'lon': entry["lon"],
            'color': color, 'status': status, 'dist': entry["dist"],
            'remarks': f"Max Weight: {maxweight} | Status: {status}",
            'type': SYMBOLOGY.get("bridge", "a-u-G")
        }
        # FA7: liegt ein Bild zur Brücke vor, wird es als Marker-Anhang mitgeschickt.
        # Solche Brücken stechen pink heraus (sonst Ampel-/Standardfarbe) + Hinweis in den Remarks.
        image = _find_image(name)
        if image:
            marker['image'] = image
            marker['color'] = COLOR_MAGENTA
            marker['remarks'] += " | Foto-Anhang"
        markers.append(marker)

    if not markers:
        return f"Keine Bruecken im Radius Stufe {level} gefunden.", []
    return f"Sende {len(markers)} Bruecke(n) an das ATAK-Lagebild...", markers
