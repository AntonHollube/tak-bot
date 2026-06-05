import os
import requests
import urllib3
import socket
import ssl
import hashlib
from datetime import datetime, timezone, timedelta

# Warnungen für selbstsignierte Zertifikate unterdrücken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Server-Konfiguration
TAK_IP = "91.98.138.143"
TAK_SERVER_API = f"https://{TAK_IP}:8443/Marti/sync/upload"
TAK_PORT_STREAM = 8089

# Zertifikate (Pfade ggf. an deine Ordnerstruktur anpassen)
CERT_FILE = "certs/admin_chain.pem"
KEY_FILE = "certs/admin_unencrypted.key"

bild_pfad = "test.jpg"

print("[*] SCHRITT 1: Lade Bild über REST-API hoch...")

# 1. Berechne Hash und Größe lokal (ATAK verlangt das für den Datei-Abgleich!)
file_size = os.path.getsize(bild_pfad)
sha256_hash = hashlib.sha256()
with open(bild_pfad, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
img_hash = sha256_hash.hexdigest()

print(f"[*] Lokaler Datei-Hash: {img_hash}")

# 2. Upload mit TAK-spezifischen Metadaten
# Damit der Server die Datei sauber indiziert, schicken wir diese Daten im Formular mit
payload = {
    'creatorUid': 'TAK-Bot',
    'name': 'test.jpg',
    'hash': img_hash,
    'contentType': 'image/jpeg'
}

try:
    with open(bild_pfad, 'rb') as f:
        # WICHTIG: Tuple ('filename', file_object, 'mime/type') ist für requests nötig!
        files = {'assetfile': ('test.jpg', f, 'image/jpeg')}
        response = requests.post(
            TAK_SERVER_API,
            data=payload,
            files=files,
            cert=(CERT_FILE, KEY_FILE),
            verify=False
        )

    if response.status_code == 200:
        print(f"[+] Upload erfolgreich! Datei ist im TAK-Netzwerk.")
    else:
        print(f"[-] Fehler beim Upload. Status: {response.status_code}\n{response.text}")
        exit(1)

except Exception as e:
    print(f"[-] Ausnahme beim Upload: {e}")
    exit(1)

print("\n[*] SCHRITT 2: Sende QuickPic-Marker über Live-Stream...")

now_dt = datetime.now(timezone.utc)
now = now_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
stale = (now_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

# Die Standard-URL für Datei-Downloads via Hash am TAK-Server
img_url = f"https://{TAK_IP}:8443/Marti/api/files/{img_hash}"

# CoT-XML im nativen "Quick Pic" Format
cot_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0" uid="QuickPic-{img_hash}" type="b-i-x-i" time="{now}" start="{now}" stale="{stale}" how="m-g">
    <point lat="48.5772" lon="13.4775" hae="300" ce="99" le="99"/>
    <detail>
        <uid Droid="TAK-Bot"/>
        <contact callsign="Ortsspitze Cam"/>
        <remarks>Kamerabild der Ortsspitze</remarks>
        
        <link relation="b-i" type="b-i-x-i" url="{img_url}" mime="image/jpeg" hash="{img_hash}" size="{file_size}" name="test.jpg" />
    </detail>
</event>"""

try:
    # Sicheren mTLS-Socket aufbauen
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE 

    with socket.create_connection((TAK_IP, TAK_PORT_STREAM)) as sock:
        with context.wrap_socket(sock, server_hostname=TAK_IP) as ssock:
            ssock.sendall(cot_xml.encode('utf-8'))
    
    print("[+] Perfekter QuickPic-Marker erfolgreich gesendet!")
    
except Exception as e:
    print(f"[-] Fehler beim Senden des Markers: {e}")