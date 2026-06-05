import meshtastic.tcp_interface
import archive.atak_pb2 as atak_pb2
import time

def connect_mesh(ip_address):
    """Initialisiert die TCP-Schnittstelle zu einem lokalen Meshtastic-Knoten."""
    try:
        print(f"[*] Verbindungsaufbau zu Meshtastic Node {ip_address}...")
        interface = meshtastic.tcp_interface.TCPInterface(hostname=ip_address)
        return interface # Schnittstelle zurückgeben
    except Exception as e:
        print(f"[-] Meshtastic-Verbindungsfehler: {e}")
        return None

def decode_mesh_packet(packet):
    """Dekodiert eingehende binäre Protobuf-Nachrichten in lesbares CoT-XML."""
    # ATAK Forwarder Port prüfen
    if packet.get('decoded', {}).get('portnum') != 1:
        return None
        
    payload = packet.get('decoded', {}).get('payload')
    if not payload:
        return None
        
    try:
        msg = atak_pb2.TakMessage()
        msg.ParseFromString(payload) # Binärdaten parsen
        return msg.cotEvent.xmlString
    except Exception as e:
        print(f"[-] Protobuf-Dekodierungsfehler: {e}")
        return None

def send_mesh_xml(interface, xml_string):
    """Kapselt ein CoT-XML-Event in Protobuf und sendet es über das Mesh-Netzwerk."""
    try:
        tak_msg = atak_pb2.TakMessage()
        
        # Mesh-Header konfigurieren
        tak_msg.cotEvent.uid = "TAK-Bot-Mesh-Reply"
        tak_msg.cotEvent.type = "b-t-f"
        tak_msg.cotEvent.how = "h-g-i-g-o"
        tak_msg.cotEvent.sendTime = int(time.time() * 1000)
        tak_msg.cotEvent.xmlString = xml_string
        
        payload = tak_msg.SerializeToString() # Serialisieren
        interface.sendData(payload, portNum=1, wantAck=False) # Ins Mesh senden
        return True
    except Exception as e:
        print(f"[-] Übertragungsfehler im Mesh: {e}")
        return False