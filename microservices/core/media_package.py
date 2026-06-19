"""Bildanhänge an CoT-Markern (FA7) über das TAK Data Package.

Ein Bild erscheint in ATAK/WinTAK nur dann als Anhang am Marker, wenn es als
**Mission/Data Package** ausgeliefert wird — ein bloßer Hash-Verweis (<attachment_list>)
im SA-Event genügt nicht (aus einem echten ATAK-Anhang reverse-engineered). Ablauf:

  1. build_package()      -> ZIP (MANIFEST + <uid>.cot + Bild); Manifest verknüpft Marker und
                             Datei über DENSELBEN uid-Parameter beider <Content>-Einträge.
  2. upload_package()     -> Enterprise-Sync-Upload (POST /Marti/sync/upload?name=...).
  3. build_fileshare_cot()-> b-f-t-r-CoT (String); vom manager über den bestehenden
                             Stream-Socket gesendet -> Client lädt & importiert Marker MIT Anhang.

Bewusst OHNE Upload-Cache: ATAK importiert ein Data Package nur einmal pro Datei-Hash. Damit ein
Marker bei jedem !b (auch nach manuellem Löschen oder Neustart) wieder erscheint, baut jeder Aufruf
ein frisches Paket (neuer Zeitstempel -> neuer Hash) -> ATAK importiert neu, die gleiche Marker-UID
sorgt fürs Aktualisieren statt Dubletten.

Nur für DATEIEN (Bild/aufgezeichnetes Video/Audio). Live-Video läuft über einen RTSP-Alias.
"""
import io
import os
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

import requests
import urllib3

from core.tak_network import BASE_URL, TAK_CERTS, TAK_HOST

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Der Upload laeuft INTERN ueber BASE_URL (z.B. tak-server:8443). Der Fileshare-Link im b-f-t-r-CoT
# muss aber die Adresse tragen, unter der der ATAK-CLIENT den Server erreicht -- sonst kann ATAK den
# Anhang nicht laden (bricht nach ~10 Versuchen ab). Per TAK_PUBLIC_HOST setzen (LAN-IP, ZeroTier-IP
# oder Hostname); Default = TAK_HOST.
PUBLIC_HOST = os.getenv("TAK_PUBLIC_HOST", TAK_HOST)
PUBLIC_BASE_URL = f"https://{PUBLIC_HOST}:8443"


def _ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_package(image_path, callsign, lat, lon, cot_type="a-u-G", color="-1",
                  remarks="", uid=None):
    """Baut das Data-Package-ZIP. Der paket-interne Marker IST der Brücken-Marker.

    Gibt (zip_bytes, uid) zurück. Durch den Zeitstempel im CoT ist jedes Paket eindeutig.
    """
    uid = uid or str(uuid.uuid4())
    media_name = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        media = f.read()

    now = datetime.now(timezone.utc)
    cot = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        f"<event version='2.0' uid='{uid}' type='{cot_type}' how='h-g-i-g-o' "
        f"time='{_ts(now)}' start='{_ts(now)}' stale='{_ts(now + timedelta(days=1))}'>"
        f"<point lat='{lat}' lon='{lon}' hae='0' ce='9999999' le='9999999'/>"
        "<detail><status readiness='true'/><archive/>"
        f"<contact callsign='{callsign}'/><color argb='{color}'/>"
        f"<remarks>{remarks}</remarks></detail></event>"
    )
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<MissionPackageManifest version="2">\n'
        '  <Configuration>\n'
        f'    <Parameter name="uid" value="{uid}"/>\n'
        f'    <Parameter name="name" value="{media_name}"/>\n'
        '    <Parameter name="onReceiveImport" value="true"/>\n'
        '    <Parameter name="onReceiveDelete" value="false"/>\n'
        '  </Configuration>\n'
        '  <Contents>\n'
        f'    <Content ignore="false" zipEntry="{uid}/{uid}.cot">'
        f'<Parameter name="uid" value="{uid}"/></Content>\n'
        f'    <Content ignore="false" zipEntry="{uid}/{media_name}">'
        f'<Parameter name="uid" value="{uid}"/></Content>\n'
        '  </Contents>\n'
        '</MissionPackageManifest>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("MANIFEST/manifest.xml", manifest)
        z.writestr(f"{uid}/{uid}.cot", cot)
        z.writestr(f"{uid}/{media_name}", media)
    return buf.getvalue(), uid


def upload_package(zip_bytes, zip_name):
    """Lädt das ZIP in Enterprise Sync. Gibt den vom Server vergebenen Hash zurück."""
    r = requests.post(f"{BASE_URL}/Marti/sync/upload", params={"name": zip_name},
                      data=zip_bytes, headers={"Content-Type": "application/x-zip-compressed"},
                      cert=TAK_CERTS, verify=False, timeout=120)
    r.raise_for_status()
    return r.json()["Hash"]


def build_fileshare_cot(server_hash, size, zip_name, display, lat, lon,
                        sender_callsign="TAK-Bot", sender_uid="TAK-Bot"):
    """Baut die b-f-t-r-Fileshare-CoT (String). Wird vom manager über den Stream gesendet."""
    now = datetime.now(timezone.utc)
    tu = str(uuid.uuid4())
    url = f"{PUBLIC_BASE_URL}/Marti/sync/content?hash={server_hash}"
    return (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        f"<event version='2.0' uid='{tu}' type='b-f-t-r' how='h-e' "
        f"time='{_ts(now)}' start='{_ts(now)}' stale='{_ts(now + timedelta(minutes=10))}'>"
        f"<point lat='{lat}' lon='{lon}' hae='0' ce='9999999' le='9999999'/>"
        "<detail>"
        f"<fileshare filename='{zip_name}' senderUrl='{url}' sizeInBytes='{size}' "
        f"sha256='{server_hash}' senderUid='{sender_uid}' senderCallsign='{sender_callsign}' name='{display}'/>"
        f"<ackrequest uid='{tu}' ackrequested='true' tag='{display}'/>"
        "</detail></event>"
    )


def attach_image(image_path, callsign, lat, lon, cot_type="a-u-G", color="-1", remarks="", uid=None):
    """Baut ein frisches Data Package, lädt es hoch und gibt die Fileshare-CoT zurück.

    Jeder Aufruf erzeugt ein neues Paket (frischer Hash), damit ATAK den Anhang bei jedem !b
    neu importiert und den Marker (gleiche UID) auch nach dem Löschen wieder anlegt.
    """
    zip_name = f"{os.path.splitext(os.path.basename(image_path))[0]}.zip"
    zip_bytes, _uid = build_package(image_path, callsign, lat, lon, cot_type, color, remarks, uid)
    server_hash = upload_package(zip_bytes, zip_name)
    return build_fileshare_cot(server_hash, len(zip_bytes), zip_name, callsign, lat, lon)
