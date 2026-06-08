
"""
measure_logger.py — Passiver Mitschnitt von Meshtastic-Empfangsdaten fuer Feldtests.

Lauscht am seriellen Meshtastic-Transceiver und protokolliert fuer jedes
empfangene Paket Signalguete (RSSI/SNR), Hop-Limit, Absender, Portnum sowie –
falls vorhanden – Text bzw. GPS-Position in eine CSV-Datei.

Verwendung (pro Wegpunkt eine Sitzung mit passendem Label, an dieselbe CSV anfuegen):

    python measure_logger.py --label LoS_500m
    python measure_logger.py --label NLoS_1000m --out messung.csv

Auswertung spaeter z. B. mit pandas/matplotlib: nach 'label' gruppieren,
RSSI/SNR mitteln, PDR aus der Anzahl der "test N"-Nachrichten je Wegpunkt.

Beenden mit STRG+C.
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone

from pubsub import pub
import meshtastic.serial_interface


CSV_FIELDS = [
    "timestamp_iso",   # lesbarer Zeitstempel (lokale Zeit)
    "epoch",           # Unix-Zeit (fuer Latenz-/Sortierauswertung)
    "label",           # Szenario + Distanz, z. B. "NLoS_500m"
    "from_id",         # Absender-Knoten (!hex)
    "portnum",         # z. B. TEXT_MESSAGE_APP, POSITION_APP
    "rx_rssi",         # Signalstaerke am Empfaenger in dBm
    "rx_snr",          # Signal-Rausch-Verhaeltnis in dB
    "hop_limit",       # verbleibende Hops
    "lat",             # GPS-Breite (nur bei Positionspaketen)
    "lon",             # GPS-Laenge (nur bei Positionspaketen)
    "text",            # Nachrichtentext (nur bei Textpaketen)
]


class MeasurementLogger:
    def __init__(self, out_path, label):
        self.out_path = out_path
        self.label = label
        self.count = 0
        self._first_packet_dumped = False

        # Header nur schreiben, wenn die Datei neu ist (Anfuegen ueber mehrere Laeufe)
        file_is_new = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
        self._fh = open(out_path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=CSV_FIELDS)
        if file_is_new:
            self._writer.writeheader()
            self._fh.flush()

    @staticmethod
    def _extract_position(decoded):
        """Liest lat/lon aus einem Positionspaket, robust gegen Formatunterschiede."""
        pos = decoded.get("position", {}) or {}
        lat = pos.get("latitude")
        lon = pos.get("longitude")
        # Fallback: einige Firmwares liefern nur Integer-Grad (1e-7)
        if lat is None and pos.get("latitudeI") is not None:
            lat = pos["latitudeI"] / 1e7
        if lon is None and pos.get("longitudeI") is not None:
            lon = pos["longitudeI"] / 1e7
        return lat, lon

    def on_receive(self, packet, interface):
        # Beim allerersten Paket einmal die komplette Struktur ausgeben,
        # damit die exakten Schluessel (rxRssi/rxSnr/...) verifiziert werden koennen.
        if not self._first_packet_dumped:
            print("\n[DEBUG] Erstes Rohpaket zur Schluessel-Verifikation:")
            print(packet)
            print("[DEBUG] -- Ende Rohpaket --\n")
            self._first_packet_dumped = True

        decoded = packet.get("decoded", {}) or {}
        portnum = decoded.get("portnum", "")

        text = decoded.get("text", "") if portnum == "TEXT_MESSAGE_APP" else ""
        lat, lon = self._extract_position(decoded) if portnum == "POSITION_APP" else (None, None)

        now = datetime.now(timezone.utc).astimezone()
        row = {
            "timestamp_iso": now.strftime("%Y-%m-%d %H:%M:%S"),
            "epoch": round(time.time(), 3),
            "label": self.label,
            "from_id": packet.get("fromId", ""),
            "portnum": portnum,
            "rx_rssi": packet.get("rxRssi"),
            "rx_snr": packet.get("rxSnr"),
            "hop_limit": packet.get("hopLimit"),
            "lat": lat,
            "lon": lon,
            "text": text,
        }

        self._writer.writerow(row)
        self._fh.flush()              # sofort sichern – wichtig im Feld
        os.fsync(self._fh.fileno())

        self.count += 1
        # Live-Ausgabe zum Mithoeren im Feld
        extra = f' "{text}"' if text else (f" @{lat:.5f},{lon:.5f}" if lat and lon else "")
        print(f"[{self.count:03d}] {row['from_id']:<12} "
              f"RSSI={row['rx_rssi']} dBm  SNR={row['rx_snr']} dB  "
              f"{portnum}{extra}")

    def close(self):
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Meshtastic RSSI/SNR Feld-Logger")
    parser.add_argument("--port", default="COM5",
                        help="Serieller Port des Transceivers (Default: $MESH_PORT oder /dev/ttyUSB0)")
    parser.add_argument("--out", default="mesh_measurements.csv",
                        help="Ziel-CSV (wird angefuegt)")
    parser.add_argument("--label", default="",
                        help='Szenario-Label fuer diesen Wegpunkt, z. B. "LoS_500m"')
    args = parser.parse_args()

    print("=" * 60)
    print("Meshtastic Feld-Logger")
    print(f"  Port : {args.port}")
    print(f"  CSV  : {args.out}")
    print(f"  Label: {args.label or '(leer)'}")
    print("=" * 60)
    print("Lausche... (Beenden mit STRG+C)\n")

    logger = MeasurementLogger(args.out, args.label)

    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=args.port)
    except Exception as e:
        print(f"[FEHLER] Konnte Transceiver an {args.port} nicht oeffnen: {e}")
        print("Tipp: Port pruefen mit 'ls -l /dev/ttyUSB* /dev/ttyACM*' bzw. 'dmesg | tail'.")
        logger.close()
        sys.exit(1)

    pub.subscribe(logger.on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[+] Beendet. {logger.count} Pakete in '{args.out}' gesichert.")
    finally:
        logger.close()
        try:
            interface.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()