import os
import sys
import time
import ssl
import socket
import threading
import queue
import logging
from dotenv import load_dotenv
import xml.etree.ElementTree as ET



# Erweitert den Suchpfad für Modul-Imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(levelname)s: %(message)s', 
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, "logs/manager.log")), 
        logging.StreamHandler(sys.stdout)])

from bot_router import route_command

load_dotenv() # .env-Datei laden

TAK_HOST = os.getenv("TAK_HOST", "127.0.0.1")
TAK_STREAM_PORT = 8089

# Pfade für mTLS-Zertifikate
CERT_DIR = os.path.join(ROOT_DIR, "certs")
CLIENT_CERT = os.path.join(CERT_DIR, "admin_chain.pem")
CLIENT_KEY = os.path.join(CERT_DIR, "admin_unencrypted.key")

xml_queue = queue.Queue(maxsize=100) 


def handle_incoming_xml(xml_string, ssock):
    """Parst eingehende CoT-Events und wertet Chat-Nachrichten aus."""
    try:
        if "__chat" not in xml_string:
            return # Nur Chats relevant
            
        root = ET.fromstring(xml_string)
        
        # Absender-UID aus ChatGroup auslesen
        sender_uid = ""
        detail = root.find("detail")
        if detail is not None:
            chat = detail.find("__chat")
            if chat is not None:
                chatgrp = chat.find("chatgrp")
                if chatgrp is not None:
                    sender_uid = chatgrp.attrib.get("uid0", "")

        point = root.find("point")
        lat = float(point.attrib.get("lat", 0)) if point is not None else 0.0
        lon = float(point.attrib.get("lon", 0)) if point is not None else 0.0
        
        # Befehlssuche in den Remarks
        if detail is not None:
            remarks = detail.find("remarks")
            if remarks is not None and remarks.text:
                cmd_string = remarks.text.strip()
                
                if cmd_string.startswith("!"):
                    logging.info(f"Bot-Kommando empfangen von {sender_uid}: {cmd_string}")
                    
                    # Logik ans Routing übergeben
                    chat_xml, marker_xmls = route_command(cmd_string, lat, lon, sender_uid)
                    
                    # Chat-Nachricht senden
                    if chat_xml:
                        ssock.sendall(chat_xml.encode('utf-8'))
                        time.sleep(0.1) # Flood-Schutz
                        
                    # Karten-Marker senden
                    for m_xml in marker_xmls:
                        ssock.sendall(m_xml.encode('utf-8'))
                        time.sleep(0.05)
                        
    except Exception as e:
        logging.error(f"Fehler im XML-Handler: {e}")

def network_reader_thread(ssock):
    """Liest kontinuierlich Daten aus dem Socket und schiebt sie in die Queue."""
    logging.info("[+] Network-Reader-Thread gestartet.")
    buffer = ""
    
    while True:
        try:
            data = ssock.recv(4096) # Blockierend lauschen
            if not data:
                logging.info("[!] Verbindung vom TAK-Server geschlossen (EOF).")
                break
                
            buffer += data.decode("utf-8", errors="ignore")
            
            # Buffer splitten für komplette XML-Pakete
            while "</event>" in buffer:
                event_str, buffer = buffer.split("</event>", 1)
                event_xml = event_str + "</event>"
                try:
                    xml_queue.put(event_xml, timeout=2) # In die Queue schieben
                except queue.Full:
                    logging.warning("[-] Warnung: XML-Queue ist voll. Verarbeitung kommt nicht hinterher.")

        except socket.timeout:
            continue # Ignorieren und weiterlauschen
        except Exception as e:
            logging.error(f"[!] Fehler im Empfangs-Thread: {e}")
            break

def message_processor_thread(ssock):
    """Verarbeitet XML-Events aus der Queue und führt die Logik aus."""
    logging.info("[+] Message-Processor-Thread gestartet.")
    
    while True:
        try:
            event_xml = xml_queue.get()
            handle_incoming_xml(event_xml, ssock)
            xml_queue.task_done()
        except Exception as e:
            logging.error(f"[!] Fehler im Verarbeitungs-Thread: {e}")

def start_manager():
    """Initialisiert die TLS-Verbindung zum TAK-Server und startet den Worker-Thread."""
    logging.info("==================================================")
    logging.info("TAK-Microservices: Bot-Manager")
    logging.info("==================================================")
    
    # TLS-Kontext konfigurieren
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE # Self-signed erlauben
    
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            logging.info(f"[*] Verbinde mit {TAK_HOST}:{TAK_STREAM_PORT} ...")
            
            sock.settimeout(10.0) # Handshake-Timeout
            sock.connect((TAK_HOST, TAK_STREAM_PORT))
            
            # Socket mit SSL/TLS absichern
            ssock = context.wrap_socket(sock, server_hostname=TAK_HOST)
            
            ssock.settimeout(None) # Timeout für recv() aufheben
            logging.info("[+] Erfolgreich verbunden.")
            
            # Threads starten
            reader_thread = threading.Thread(target=network_reader_thread, args=(ssock,), daemon=True)
            processor_thread = threading.Thread(target=message_processor_thread, args=(ssock,), daemon=True)
            
            reader_thread.start()
            processor_thread.start()
            
            # Main-Thread überwacht die Worker-Threads
            while reader_thread.is_alive() and processor_thread.is_alive():
                time.sleep(1)
                
        except (socket.error, ConnectionRefusedError, ssl.SSLError) as e:
            logging.error(f"[-] Verbindungsfehler: {e}. Retrying in 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("\n[-] Beendet durch User.")
            break
        except Exception as e:
            logging.error(f"[!] Unerwarteter Fehler: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_manager()