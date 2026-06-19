"""Scanner: laedt aktuelle Pegelstaende (PegelOnline) und schreibt sie atomar in den lokalen Cache."""
import json
import os
import logging
from core.api_connector import fetch_pegel

def update_pegel_cache():
    """Laedt aktuelle Pegelstaende und schreibt sie atomar in data/pegel.json."""
    logging.info("[*] Lade Pegelstände (PegelOnline)...")
    stations = fetch_pegel() # API-Call ausführen
    
    if stations:
        temp_path = "data/pegel_temp.json"
        final_path = "data/pegel.json"
        
        try:
            # Datei zwischenspeichern
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(stations, f, indent=4)
                
            # Atomarer Dateiaustausch
            os.replace(temp_path, final_path)
            logging.info(f"[+] {len(stations)} Pegel-Stationen aktualisiert.")
        except Exception as e:
            logging.error(f"[-] I/O-Fehler bei Pegeldaten: {e}")
    else:
        logging.warning("[-] Keine Pegeldaten empfangen.")

if __name__ == "__main__":
    update_pegel_cache()