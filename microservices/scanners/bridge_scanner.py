"""Scanner: laedt Bruecken-Daten via Overpass und schreibt sie atomar in den lokalen Cache."""
import json
import os
import logging
from core.api_connector import fetch_overpass

def update_bridge_cache():
    """
    Aktualisiert den lokalen Zwischenspeicher für Brückenbauwerke
    über die OpenStreetMap Overpass-API. Verwendet atomares Speichern
    zur Vermeidung von Dateikorruption während Schreibvorgängen.
    """
    logging.info("[*] Lade Brückendaten (Overpass)...")
    
    # Abfrage für das Einsatzgebiet
    query = """
    [out:json][timeout:25];
    area["name"="Passau"]->.searchArea;
    (way["bridge"="yes"]["highway"](area.searchArea););
    out center;
    """
    bridges = fetch_overpass(query) # API-Call ausführen
    
    if bridges:
        temp_path = "data/bridges_temp.json"
        final_path = "data/bridges.json"
        
        try:
            # Pufferdatei anlegen
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(bridges, f, indent=4)
            
            # Atomar überschreiben
            os.replace(temp_path, final_path)
            logging.info(f"[+] {len(bridges)} Brücken erfolgreich gesichert.")

        except Exception as e:
            logging.error(f"[-] I/O-Fehler bei Brückendaten: {e}")
    else:
        logging.warning("[-] Keine API-Antwort erhalten.")

if __name__ == "__main__":
    update_bridge_cache()