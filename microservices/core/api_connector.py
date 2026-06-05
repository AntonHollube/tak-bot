import requests
import urllib3

# SSL-Warnungen unterdrücken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_overpass(query, user_agent="TAK-Microservice/1.0"):
    """Führt eine Suchabfrage gegen die OpenStreetMap Overpass API aus."""
    url = "http://overpass-api.de/api/interpreter"
    headers = {"User-Agent": user_agent} # Header setzen
    try:
        response = requests.post(url, data={"data": query}, headers=headers, timeout=25)
        response.raise_for_status() # HTTP-Fehler abfangen
        return response.json().get("elements", [])
    except Exception as e:
        print(f"[-] Overpass API Fehler: {e}")
        return []

def fetch_opensky(bbox):
    """Holt Live-Flugdaten für einen definierten geografischen Bereich."""
    lamin, lamax, lomin, lomax = bbox
    url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"
    try:
        headers = {'User-Agent': 'TAK-Bot/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("states", []) # Flugdaten extrahieren
    except Exception as e:
        print(f"[-] OpenSky API Fehler: {e}")
        return []

def fetch_weather(lat, lon):
    """Ruft das aktuelle Wetter sowie eine stündliche Vorhersage ab."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation_probability&forecast_days=2"
    try:
        headers = {'User-Agent': 'TAK-Bot/1.0'}
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[-] Open-Meteo Fehler bei {lat},{lon}: {e}")
        return None

def fetch_pegel():
    """Lädt alle aktuellen Pegelstände der PegelOnline API herunter."""
    url = "https://pegelonline.wsv.de/webservices/rest-api/v2/stations.json?includeTimeseries=true&includeCurrentMeasurement=true"
    try:
        headers = {'User-Agent': 'TAK-Bot/1.0'}
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        return response.json() # JSON zurückgeben
    except Exception as e:
        print(f"[-] PegelOnline API Fehler: {e}")
        return []