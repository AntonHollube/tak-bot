"""Scanner: laedt KRITIS-Layer (Tunnel, WLAN, Kliniken) via Overpass in den lokalen Cache."""
import json
import os
import logging
from core.api_connector import fetch_overpass

# Layer-Definition für kritische Infrastruktur (KRITIS)
KRITIS_LAYERS = {
    # bridges wird auch von bridge_scanner.py geladen -> doppelter Fetch (bekannt, vgl. Thesis 9.2)
    "bridges": {
        "filename": "bridges.json",
        "query": '[out:json][timeout:25];area["name"="Passau"]->.searchArea;(way["bridge"="yes"]["highway"](area.searchArea););out center;'
    },
    "tunnels": {
        "filename": "tunnels.json",
        "query": '[out:json][timeout:25];area["name"="Passau"]->.searchArea;(way["tunnel"="yes"]["highway"](area.searchArea););out center;'
    },
    "wifi": {
        "filename": "wifi.json",
        "query": '[out:json][timeout:25];area["name"="Passau"]->.searchArea;(node["internet_access"="wlan"](area.searchArea);node["wifi"="yes"](area.searchArea););out center;'
    },
    "hospitals": {
        "filename": "hospitals.json",
        "query": '[out:json][timeout:25];area["name"="Passau"]->.searchArea;(node["amenity"="hospital"](area.searchArea);way["amenity"="hospital"](area.searchArea););out center;'
    }
}

def update_kritis_cache():
    """Laedt alle KRITIS-Layer (Tunnel/WLAN/Kliniken/Bruecken) via Overpass, atomar nach data/."""
    logging.info("[*] Aktualisiere KRITIS-Layer...")

    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True) # Verzeichnis sicherstellen

    for layer_name, config in KRITIS_LAYERS.items():
        logging.info(f"[*] Verarbeite Layer: {layer_name}")
        elements = fetch_overpass(config["query"]) # Daten abrufen
        
        if elements:
            temp_path = os.path.join(data_dir, f"{config['filename']}_temp.json")
            final_path = os.path.join(data_dir, config["filename"])
            
            try:
                # Temporären Dump schreiben
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(elements, f, indent=4, ensure_ascii=False)
                
                # Thread-safe ersetzen
                os.replace(temp_path, final_path)
                logging.info(f"[+] Layer {layer_name}: {len(elements)} Objekte gesichert.")
            except Exception as e:
                logging.error(f"[-] Speicherfehler bei {layer_name}: {e}")
        else:
            logging.warning(f"[-] Layer {layer_name} übersprungen (keine Daten).")

if __name__ == "__main__":
    update_kritis_cache()