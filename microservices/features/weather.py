"""Wetter-Feature: aktuelles Wetter abrufen und als Wind-Grid (H3) auf die Karte legen."""
import logging
import h3
from core.h3_engine import get_search_area
from core.api_connector import fetch_weather
from core.feature_base import parse_level
from core.config import SYMBOLOGY, COLOR_CYAN

def get_wind_direction_abbr(degrees):
    """Konvertiert Gradzahlen in meteorologische Himmelsrichtungen (Kürzel)."""
    if degrees is None or degrees == "N/A":
        return "N/A"
    try:
        # Kompass-Sektoren definieren
        abbr = ["N", "NO", "O", "SO", "S", "SW", "W", "NW", "N"]
        index = round(float(degrees) / 45) % 8 # Sektor berechnen
        return abbr[index]
    except Exception as e:
        logging.warning(f"[-] Parsing-Fehler Himmelsrichtung: {e}")
        return "N/A"

def execute(lat, lon, args):
    """
    Ruft meteorologische Echtzeitdaten ab, parst stündliche Prognosen 
    und generiert ein räumliches Wind-Grid über die H3-Hexagone des Einsatzgebietes.
    """
    logging.info(f"[*] Initialisiere Wetter-Abfrage (Lat: {lat}, Lon: {lon})")
    level = parse_level(args)

    try:
        # API-Abfrage durchfuehren
        weather_data = fetch_weather(lat, lon)
        
        if not weather_data:
            logging.error("[-] Fehlerhafte API-Response.")
            return "Wetterdaten temporaer nicht verfuegbar.", []

        current = weather_data.get("current_weather", {})

        # Aktuelle Parameter extrahieren
        temp = current.get("temperature", "N/A")
        wind_speed_kmh = current.get("windspeed", 0)
        wind_dir = current.get("winddirection", 0)
        wind_abbr = get_wind_direction_abbr(wind_dir)

        # Chat-Ausgabe formatieren
        chat_msg = (
            f"[ Wetter-Lagebild ]\n"
            f"JETZT:\n"
            f"{temp} C | {wind_speed_kmh} km/h (Richtung: {wind_abbr})"
        )

        # Räumliches Wind-Grid generieren
        valid_hexagons = get_search_area(lat, lon, level)
        markers = []

        # Umrechnung für ATAK-Geschwindigkeitsvektoren (m/s)
        wind_speed_mps = round(float(wind_speed_kmh) / 3.6, 1) if wind_speed_kmh != "N/A" else 0

        for index, hex_id in enumerate(valid_hexagons):
            try:
                hex_lat, hex_lon = h3.cell_to_latlng(hex_id)
            except AttributeError:
                hex_lat, hex_lon = h3.h3_to_geo(hex_id) # Fallback alte API

            # Wind-Vektoren für Karte aufbauen
            markers.append({
                'name': f"Wind-{index}",
                'lat': hex_lat,
                'lon': hex_lon,
                'color': COLOR_CYAN,
                'remarks': f"Wetter: {temp} C | Wind: {wind_speed_kmh} km/h ({wind_abbr})",
                'type': SYMBOLOGY.get("weather", "b-m-p-s-m"),
                'course': float(wind_dir) if wind_dir != "N/A" else 0.0,
                'speed': wind_speed_mps
            })

        logging.info("[+] Wetter-Grid erfolgreich erzeugt.")
        return chat_msg, markers

    except Exception as e:
        logging.error(f"[-] Kritischer Fehler im Wetter-Modul: {e}", exc_info=True)
        return f"Systemfehler bei der Wetterverarbeitung: {e}", []