"""Baut Cursor-on-Target (CoT) XML: Marker-Events und globale Chat-Nachrichten."""
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from core.config import COLOR_BLUE


def build_cot_event(uid, cot_type, lat, lon, callsign, remarks="", color=COLOR_BLUE,
                    stale_minutes=60, hae="0", course=None, speed_mps=None):
    """Generiert ein valides Cursor-on-Target (CoT) XML-Event."""
    now = datetime.now(timezone.utc)
    stale = now + timedelta(minutes=stale_minutes)

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
        "le": "9999999.0",
    })

    detail = ET.SubElement(event, "detail")

    # zuvor 'remarks.elem = ...' -> AttributeError auf str (crashte jeden Aufruf).
    remarks_elem = ET.SubElement(detail, "remarks")
    remarks_elem.text = str(remarks)

    ET.SubElement(detail, "color", {"argb": str(color)})
    ET.SubElement(detail, "contact", {"callsign": str(callsign)})

    # Kinematische Attribute nur bei dynamischen Objekten (Flugzeuge, Wind).
    if course is not None and speed_mps is not None:
        ET.SubElement(detail, "track", {
            "course": str(course),
            "speed": str(speed_mps),
        })

    xml_string = ET.tostring(event, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n{xml_string}'


def build_chat_event(message, sender="TAK-Bot"):
    """Erstellt ein CoT-GeoChat-Event fuer den globalen Broadcast (Alle Chaträume).

    Nutzt ElementTree, damit Sonderzeichen (&, <, >) im Text automatisch
    XML-konform escaped werden.
    """
    now = datetime.now(timezone.utc)
    stale = now + timedelta(minutes=10)  # 10 Min Gueltigkeit

    time_str = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    stale_str = stale.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    msg_id = str(uuid.uuid4())

    event = ET.Element("event", {
        "version": "2.0",
        "uid": f"GeoChat.{sender}.AllChatRooms.{msg_id}",
        "type": "b-t-f",
        "time": time_str,
        "start": time_str,
        "stale": stale_str,
        "how": "h-g-i-g-o",
    })

    ET.SubElement(event, "point", {
        "lat": "0.0", "lon": "0.0", "hae": "0.0",
        "ce": "9999999.0", "le": "9999999.0",
    })

    detail = ET.SubElement(event, "detail")
    chat = ET.SubElement(detail, "__chat", {
        "parent": "RootContactGroup",
        "groupOwner": "false",
        "messageId": msg_id,
        "chatroom": "Alle Chaträume",
        "id": "All Chat Rooms",
        "senderCallsign": sender,
    })
    ET.SubElement(chat, "chatgrp", {
        "uid0": sender, "uid1": "All Chat Rooms", "id": "All Chat Rooms",
    })

    remarks_elem = ET.SubElement(detail, "remarks", {
        "source": "BAO.F.ATAK.TAK-Bot",
        "to": "All Chat Rooms",
        "time": time_str,
    })
    remarks_elem.text = str(message)

    xml_string = ET.tostring(event, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_string}'