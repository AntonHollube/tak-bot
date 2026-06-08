import logging
import os
import requests
import urllib3
import hashlib

# SSL-Warnungen unterdrücken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfiguration laden
TAK_HOST = os.getenv("TAK_HOST", "127.0.0.1")
TAK_PORT = 8443
BASE_URL = f"https://{TAK_HOST}:{TAK_PORT}"

# Zertifikatspfade ermitteln
HELPER_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(HELPER_DIR)
CERT_DIR = os.path.join(BASE_DIR, "certs")

CLIENT_CERT = os.path.join(CERT_DIR, "bot.pem")
CLIENT_KEY = os.path.join(CERT_DIR, "bot.key") 

TAK_CERTS = (CLIENT_CERT, CLIENT_KEY)

def get_api(endpoint):
    """Führt eine standardisierte HTTP-GET-Anfrage an die TAK-REST-API aus."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, cert=TAK_CERTS, verify=False, timeout=10)
        response.raise_for_status() # HTTP-Status prüfen
        return response.json()
    except Exception as e:
        logging.error(f"[-] GET-Request fehlgeschlagen ({endpoint}): {e}")
        return None

def post_api(endpoint, payload, is_json=True):
    """Führt eine standardisierte HTTP-POST-Anfrage an die TAK-REST-API aus."""
    url = f"{BASE_URL}{endpoint}"
    try:
        if is_json:
            response = requests.post(url, json=payload, cert=TAK_CERTS, verify=False, timeout=10)
        else:
            # Fallback für XML-Payloads
            headers = {'Content-Type': 'application/xml'}
            response = requests.post(url, data=payload, headers=headers, cert=TAK_CERTS, verify=False, timeout=10)
        
        response.raise_for_status()
        
        try:
            return response.json() # JSON-Antwort parsen
        except ValueError:
            return response.text # Plain-Text-Antwort
    except Exception as e:
        logging.error(f"[-] POST-Request fehlgeschlagen ({endpoint}): {e}")
        return None

def send_cot_xml(cot_xml, ip=TAK_HOST, port=TAK_PORT):
    """Übermittelt ein rohes CoT-XML-Event an den TAK-Server via REST."""
    return post_api("/Marti/api/cot/xml", cot_xml, is_json=False)

def upload_file(file_path, lat, lon):
    """
    Berechnet den SHA-256-Hash einer Datei und lädt diese 
    geokodiert auf den TAK-Server hoch.
    """
    url = f"{BASE_URL}/Marti/sync/upload"
    file_name = os.path.basename(file_path)
    
    # Lokalen SHA-256-Hash berechnen
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    file_hash = sha256_hash.hexdigest()

    # Formular-Daten für ATAK aufbauen
    payload = {
        'Name': file_name,
        'Latitude': str(lat),
        'Longitude': str(lon),
        'Groups': '',
        'DownloadPath': ''
    }

    try:
        with open(file_path, 'rb') as f:
            files = {'assetfile': (file_name, f, 'image/jpeg')} # Dateianhang definieren
            
            logging.info(f"[*] Starte Datei-Upload ({file_hash[:8]}...)")
            response = requests.post(url, data=payload, files=files, cert=TAK_CERTS, verify=False, timeout=30)
            
            if response.status_code == 200:
                logging.info("[+] Datei erfolgreich auf TAK-Server bereitgestellt.")
                return file_hash 
            else:
                logging.error(f"[-] Upload-Fehler (Code {response.status_code})")
                return None
                
    except Exception as e:
        logging.error(f"[-] Kritischer Fehler beim Datei-Upload: {e}")
        return None