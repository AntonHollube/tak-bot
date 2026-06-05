import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# Host-IP laden
TAK_HOST = os.getenv("TAK_HOST", "127.0.0.1")

def build_cot_event(uid, cot_type, lat, lon, callsign, remarks="", color="-16776961", stale_minutes=60, hae="0", course=None, speed_mps=None, extra_detail="", image_hash=None):
    """Generiert ein valides Cursor-on-Target (CoT) XML-Event."""
    now = datetime.now(timezone.utc) # Aktuelle Zeit
    stale = now + timedelta(minutes=stale_minutes) # Ablaufzeit berechnen
    
    time_str = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    stale_str = stale.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    event = ET.Element("event", {
        "version": "2.0",
        "uid": str(uid),
        "type": str(cot_type),
        "time": time_str,
        "start": time_str,
        "stale": stale_str,
        "how": "m-g",
    })

    ET.SubElement(event, "point", {
        "lat": str(lat),
        "lon": str(lon),
        "hae": str(hae),
        "ce": "9999999.0",
        "le": "9999999.0"
    })

    detail = ET.SubElement(event, "detail")

    remarks.elem = ET.SubElement(detail, "remarks")
    remarks.elem.text = str(remarks)

    ET.SubElement(detail, "color", {"argb": str(color)})
    ET.SubElement(detail, "contact", {"callsign": str(callsign)})
    if course is not None and speed_mps is not None:
        ET.SubElement(detail, "track", {
            "course": str(course),
            "speed": str(speed_mps)
        })
    
    xml_string = ET.tostring(event, encoding="unicode")

    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n{xml_string}'