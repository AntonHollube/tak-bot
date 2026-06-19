"""Hintergrund-Worker: aktualisiert zyklisch die JSON-Daten-Caches (KRITIS, Bruecken, Pegel)."""
import logging
import sys
import time
import os
from manager import ROOT_DIR
from scanners.kritis_scanner import update_kritis_cache
from scanners.pegel_scanner import update_pegel_cache
from scanners.bridge_scanner import update_bridge_cache
from scanners.image_scanner import update_bridge_images
from dotenv import load_dotenv

load_dotenv() # .env-Datei laden

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(levelname)s: %(message)s', 
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, "logs/task_worker.log")), 
        logging.StreamHandler(sys.stdout)])


def run_scheduler():
    """
    Asynchroner Scheduler für Hintergrund-Aufgaben.
    Aktualisiert gecachte Daten zyklisch über externe APIs,
    um den primären TAK-Manager nicht zu blockieren.
    """
    logging.info("[*] Task-Worker gestartet.")
    minutes_passed = 0
    
    # Initiale Befüllung der JSON-Dumps
    logging.info("[*] Initiale Daten-Aktualisierung (KRITIS, Brücken & Pegel)...")
    update_kritis_cache()
    update_bridge_cache()
    update_bridge_images()  # FA7: Brücken-Bilder (Wikimedia) nach dem Brücken-Cache
    update_pegel_cache()
    
    while True:
        try:
            # Viertelstündlicher Intervall
            if minutes_passed > 0 and minutes_passed % 15 == 0:
                logging.info(f"[*] Führe 15-Minuten-Jobs aus (Minute {minutes_passed})")
                update_pegel_cache() # Pegelstände updaten

            # Täglicher Intervall (1440 Minuten)
            if minutes_passed > 0 and minutes_passed % 1440 == 0:
                logging.info(f"[*] Führe tägliche Jobs aus (Minute {minutes_passed})")
                update_kritis_cache()  # Overpass-Layer updaten
                update_bridge_cache()  # Brücken-Layer updaten
                update_bridge_images()  # FA7: neue/fehlende Brücken-Bilder nachziehen
                
            time.sleep(60) # Genau 1 Minute schlafen
            minutes_passed += 1
            
        except Exception as e:
            logging.error(f"[!] Fehler in der Scheduler-Loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_scheduler()