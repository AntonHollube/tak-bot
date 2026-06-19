"""REST-Anbindung an den TAK-Server (mTLS): GET/POST und CoT-Versand."""
import logging
import os
import requests
import urllib3

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

def send_cot_xml(cot_xml):
    """Übermittelt ein rohes CoT-XML-Event an den TAK-Server via REST."""
    return post_api("/Marti/api/cot/xml", cot_xml, is_json=False)