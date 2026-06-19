# TAK-Bot

Ein Chat-Bot für den [TAK-Server](https://tak.gov/) (Team Awareness Kit). Nutzer
schreiben im ATAK-Client eine Chat-Nachricht mit einem `!`-Befehl, und der Bot
antwortet im Chat **und** legt passende Marker ins gemeinsame Lagebild – z. B.
Brücken nach Traglast, Flusspegel, Wetter/Wind, kritische Infrastruktur oder
Live-Flugverkehr. Datengrundlage ist die Region **Passau**.

## Architektur

Alles wird über [docker-compose.yml](docker-compose.yml) orchestriert:

| Service             | Startet                  | Aufgabe |
|---------------------|--------------------------|---------|
| `tak-db`            | PostgreSQL 15 + PostGIS  | Datenbank des TAK-Servers (`127.0.0.1:5432`) |
| `tak-server`        | TAK Server (Java 17)     | Der eigentliche TAK-Server (Ports `8089`, `8443`, `8444`, `8446`) |
| `grafana`           | Grafana                  | Visualisierung/Monitoring (`:3000`) |
| `tak-bot`           | `manager.py`             | **Der Chat-Bot** – hält die mTLS-Stream-Verbindung und beantwortet Befehle |
| `tak-worker`        | `task_worker.py`         | Aktualisiert zyklisch die lokalen JSON-Daten-Caches |
| `tak-mesh-gateway`  | `meshtastic_manager.py`  | Meshtastic/LoRa-Gateway (benötigt Hardware unter `/dev/ttyACM0`) |

Ablauf des Bots: `manager.py` verbindet sich per **mTLS** mit dem CoT-Stream des
Servers (Port `8089`), erkennt eingehende Chat-Nachrichten, und gibt Befehle an
`bot_router.py` weiter. Der Router ruft das passende Feature-Modul auf und baut
aus dessen Ergebnis die CoT-Antwort (Chat + Marker), die zurückgesendet wird.

## Befehle

Im ATAK-Chat eingeben. Optionaler Radius als Stufe `1`–`3` (Standard `1`):

| Befehl        | Wirkung |
|---------------|---------|
| `!b [1-3]`    | Brücken (Farbe nach Traglast) |
| `!t [1-3]`    | Tunnel & Unterführungen |
| `!hosp [1-3]` | Kliniken / med. Einrichtungen |
| `!p [1-3]`    | Aktuelle Flusspegel |
| `!w [1-3]`    | Wetter- & Wind-Lagebild |
| `!wifi [1-3]` | Notfall-WLAN-Hotspots |
| `!h`          | Hilfe |

Beispiel: `!t 2` sucht Tunnel im mittleren Umkreis.

## Setup

**Voraussetzungen:** Docker + Docker Compose, eine TAK-Server-Distribution unter
`./tak` (wird in `tak-db` und `tak-server` gemountet) sowie Client-Zertifikate
für den Bot.

1. **Umgebungsvariablen:** `microservices/.env.example` nach `microservices/.env`
   kopieren und anpassen:
   ```env
   TAK_HOST=<TAK-Server-Adresse>
   POSTGRES_PASSWORD=<DB-Passwort>
   ```
2. **Zertifikate:** Das Bot-Client-Zertifikat als `bot.pem` und `bot.key` in
   `microservices/certs/` ablegen (mTLS gegen den TAK-Server).
3. **Starten:**
   ```bash
   docker compose up -d
   ```
   Der Bot wartet beim Start kurz, bis der TAK-Server bereit ist, und verbindet
   sich dann automatisch (mit Reconnect-Logik).

> Hinweis: `.env`, Zertifikate, Logs und die von den Scannern erzeugten
> `data/*.json`-Caches werden über `.gitignore` aus der Versionierung gehalten.

## Projektstruktur

```
microservices/
├── manager.py            # Bot: mTLS-Verbindung + Empfang/Verarbeitung
├── bot_router.py         # Routing der !-Befehle auf die Features
├── task_worker.py        # Hintergrund-Worker (Daten-Caches aktualisieren)
├── meshtastic_manager.py # Meshtastic/LoRa-Gateway
├── cot_symbology.json    # Mapping Feature -> MIL-STD-2525 CoT-Typ
├── core/                 # config, cot_builder, tak_network, api_connector,
│                         #   feature_base, geo_math, h3_engine
├── features/             # bridges, kritis, pegel, weather, help
├── scanners/             # Overpass/PegelOnline-Scanner für die JSON-Caches
├── data/                 # Lokale JSON-Caches (zur Laufzeit erzeugt)
└── certs/                # Client-Zertifikate (nicht im Repo)
```

Ein Feature-Modul stellt `execute(lat, lon, args)` bereit und liefert
`(chat_text, marker_liste)` zurück; das erwartete Marker-Format ist in
[microservices/core/feature_base.py](microservices/core/feature_base.py)
dokumentiert.
