import json
import os
import logging

# Finde das Hauptverzeichnis des Projekts
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "cot_symbology.json")

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