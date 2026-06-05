import h3
from core.h3_engine import get_search_area
from core.api_connector import fetch_weather
import traceback 
from core.config import SYMBOLOGY

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
        print(f"[-] Parsing-Fehler Himmelsrichtung: {e}")
        return "N/A"

def execute(lat, lon, args):
    """
    Ruft meteorologische Echtzeitdaten ab, parst stündliche Prognosen 
    und generiert ein räumliches Wind-Grid über die H3-Hexagone des Einsatzgebietes.
    """
    print(f"[*] Initialisiere Wetter-Abfrage (Lat: {lat}, Lon: {lon})")
    level = 1
    if args and args[0].isdigit():
        level = int(args[0]) # Radius anpassen

    try:
        # API-Abfrage durchfuehren
        weather_data = fetch_weather(lat, lon)
        
        if not weather_data:
            print("[-] Fehlerhafte API-Response.")
            return "Wetterdaten temporaer nicht verfuegbar.", []

        current = weather_data.get("current_weather", {})
        hourly = weather_data.get("hourly", {})

        # Aktuelle Parameter extrahieren
        temp = current.get("temperature", "N/A")
        wind_speed_kmh = current.get("windspeed", 0)
        wind_dir = current.get("winddirection", 0)
        wind_abbr = get_wind_direction_abbr(wind_dir)

        # Zeitliche Prognose (+1h) ermitteln
        current_time_str = current.get("time") 
        forecast_temp = "N/A"
        forecast_rain = "N/A"
        
        if current_time_str and "time" in hourly:
            try:
                current_idx = hourly["time"].index(current_time_str)
                next_idx = current_idx + 1 # +1 Stunde
                forecast_temp = hourly["temperature_2m"][next_idx]
                forecast_rain = hourly["precipitation_probability"][next_idx]
            except (ValueError, IndexError):
                print("[-] Prognose-Index out of bounds.")

        # Chat-Ausgabe formatieren
        chat_msg = (
            f"[ Wetter-Lagebild ]\n"
            f"JETZT:\n"
            f"{temp} C | {wind_speed_kmh} km/h (Richtung: {wind_abbr})\n"
            #f"IN 1 STUNDE:\n"
            #f"{forecast_temp} C | Regenrisiko: {forecast_rain}%"
        )

        # Räumliches Wind-Grid generieren
        valid_hexagons = get_search_area(lat, lon, level)
        marker_data = []
        
        # Umrechnung für ATAK-Geschwindigkeitsvektoren (m/s)
        wind_speed_mps = round(float(wind_speed_kmh) / 3.6, 1) if wind_speed_kmh != "N/A" else 0
        
        for index, hex_id in enumerate(valid_hexagons):
            try:
                hex_lat, hex_lon = h3.cell_to_latlng(hex_id)
            except AttributeError:
                hex_lat, hex_lon = h3.h3_to_geo(hex_id) # Fallback alte API

            # Wind-Vektoren für Karte aufbauen
            marker_data.append({
                'name': f"Wind-{index}",
                'lat': hex_lat,
                'lon': hex_lon,
                'color': "-16711681", # Cyan für Winddaten
                'remarks': f"Wetter: {temp} C | Wind: {wind_speed_kmh} km/h ({wind_abbr})",
                'type': SYMBOLOGY.get("weather", "b-m-p-s-m"),   
                'course': float(wind_dir) if wind_dir != "N/A" else 0.0,
                'speed': wind_speed_mps
            })

        print("[+] Wetter-Grid erfolgreich erzeugt.")
        return chat_msg, marker_data

    except Exception as e:
        print(f"[-] Kritischer Fehler im Wetter-Modul: {e}")
        traceback.print_exc()
        return f"Systemfehler bei der Wetterverarbeitung: {e}", []