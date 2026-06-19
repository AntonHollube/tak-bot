"""Zentrale Konfiguration: Pfade, CoT-Symbologie und ARGB-Farbkonstanten."""
import json
import os
import logging

# Finde das Hauptverzeichnis des Projekts
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "cot_symbology.json")
DATA_DIR = os.path.join(ROOT_DIR, "data")  # lokaler JSON-Cache der Scanner

# ARGB-Farbcodes fuer CoT-Marker (so rendert ATAK die Markerfarbe).
COLOR_RED = "-65536"        # Gefahr / gesperrt
COLOR_YELLOW = "-256"       # Warnung / eingeschraenkt
COLOR_GREEN = "-16711936"   # frei / befahrbar
COLOR_BLUE = "-16776961"    # Standard / neutral
COLOR_GRAY = "-8355712"     # Tunnel / unterirdisch
COLOR_MAGENTA = "-65281"    # Funk / WLAN
COLOR_CYAN = "-16711681"    # Wetter / Wind

def load_symbology():
    """Lädt die CoT-Symbole aus der JSON-Datei in den Arbeitsspeicher."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("MIL_STD_2525", {})
    except Exception as e:
        logging.error(f"Konnte cot_symbology.json nicht laden: {e}. Nutze hardcodierte Fallbacks.")
        return {}

# Diese Variable wird nur einmal beim Start geladen und ist dann global verfügbar
SYMBOLOGY = load_symbology()