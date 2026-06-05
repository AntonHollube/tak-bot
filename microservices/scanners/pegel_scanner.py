import json
import os
from core.api_connector import fetch_pegel

def update_pegel_cache():
    """
    Ruft Echtzeit-Wasserstände der PegelOnline-API ab und 
    persistiert diese lokal für die Offline-Verarbeitung.
    """
    print("[*] Lade Pegelstände (PegelOnline)...")
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
            print(f"[+] {len(stations)} Pegel-Stationen aktualisiert.")
        except Exception as e:
            print(f"[-] I/O-Fehler bei Pegeldaten: {e}")
    else:
        print("[-] Keine Pegeldaten empfangen.")

if __name__ == "__main__":
    update_pegel_cache()