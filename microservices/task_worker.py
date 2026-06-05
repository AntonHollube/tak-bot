import logging
import sys
import time
import os
import json
from core.api_connector import fetch_weather
from manager import ROOT_DIR
from scanners.kritis_scanner import update_kritis_cache
from scanners.pegel_scanner import update_pegel_cache
from features.airplanes import push_live_traffic
from dotenv import load_dotenv

load_dotenv() # .env-Datei laden

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

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
    logging.info("[*] Initiale Daten-Aktualisierung (KRITIS & Pegel)...")
    update_kritis_cache()
    update_pegel_cache()
    
    while True:
        try:
            # Viertelstündlicher Intervall
            if minutes_passed > 0 and minutes_passed % 15 == 0:
                logging.info(f"[*] Führe 15-Minuten-Jobs aus (Minute {minutes_passed})")
                update_pegel_cache() # Pegelstände updaten

                # Flugzeug-Tracking updaten (falls Modul aktiv)
                state_file = os.path.join(DATA_DIR, "airplane_state.json")
                if os.path.exists(state_file):
                    try:
                        with open(state_file, "r") as f:
                            state = json.load(f)
                            if state.get("active", False):
                                push_live_traffic(state.get("lat"), state.get("lon"))
                    except Exception as e:
                        logging.error(f"[-] Fehler beim Flugzeug-Tracker: {e}")

            # Täglicher Intervall (1440 Minuten)
            if minutes_passed > 0 and minutes_passed % 1440 == 0:
                logging.info(f"[*] Führe tägliche Jobs aus (Minute {minutes_passed})")
                update_kritis_cache() # Overpass-Layer updaten
                
            time.sleep(60) # Genau 1 Minute schlafen
            minutes_passed += 1
            
        except Exception as e:
            logging.error(f"[!] Fehler in der Scheduler-Loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_scheduler()