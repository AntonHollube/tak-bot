"""Anbindung externer Datenquellen: OSM Overpass, OpenSky, Open-Meteo, PegelOnline."""
import logging
import requests


def fetch_overpass(query, user_agent="TAK-Microservice/1.0"):
    """Suchabfrage gegen die OpenStreetMap Overpass API."""
    url = "https://overpass-api.de/api/interpreter"
    try:
        response = requests.post(url, data={"data": query},
                                 headers={"User-Agent": user_agent}, timeout=25)
        response.raise_for_status()
        return response.json().get("elements", [])
    except Exception as e:
        logging.error(f"[-] Overpass API Fehler: {e}")
        return []


def fetch_weather(lat, lon):
    """Aktuelles Wetter von Open-Meteo."""
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&current_weather=true")
    try:
        response = requests.get(url, headers={'User-Agent': 'TAK-Bot/1.0'}, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"[-] Open-Meteo Fehler bei {lat},{lon}: {e}")
        return None


def fetch_pegel():
    """Alle aktuellen Pegelstaende der PegelOnline API."""
    url = ("https://pegelonline.wsv.de/webservices/rest-api/v2/stations.json"
           "?includeTimeseries=true&includeCurrentMeasurement=true")
    try:
        response = requests.get(url, headers={'User-Agent': 'TAK-Bot/1.0'}, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"[-] PegelOnline API Fehler: {e}")
        return []