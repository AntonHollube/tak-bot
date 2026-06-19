"""Scanner: beschafft je Bruecke automatisiert ein lizenzfreies Bild (FA7).

Overpass liefert kaum Bildverweise (in Passau ~7 von ~210 benannten Bruecken). Dieser Scanner
fuellt die Luecke ueber den Wikimedia-Stack, in Prioritaet:

  1. OSM-Tag ``image``              - direkter Link bzw. Commons-Dateiseite
  2. OSM-Tag ``wikidata`` (P18)     - hinterlegtes Bild der Wikidata-Entitaet
  3. OSM-Tag ``wikipedia``          - Vorschaubild der Wikipedia-Seite (REST summary)
  4. Commons-Geosuche nach Koordinate - georeferenzierte Fotos in Bruecken-Naehe

Treffer werden als ``data/bridge_images/<slug>.<jpg|png>`` abgelegt (genau dort liest das
Bruecken-Feature, siehe features/bridges.py). Provenienz/Lizenz/Quelle landen in
``data/bridge_images/index.json``; ein Negativ-Cache verhindert taegliche Wiederholabfragen fuer
Bruecken ohne Foto. Alle Quellen sind frei lizenziert (Attribution ueber die Commons-/Wikipedia-Seite).
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote, unquote

import requests

from core.config import DATA_DIR
from core.feature_base import load_json_data, slugify

IMG_DIR = os.path.join(DATA_DIR, "bridge_images")
INDEX_FILE = os.path.join(IMG_DIR, "index.json")

# Wikimedia verlangt einen aussagekraeftigen User-Agent mit Kontakt.
UA = {"User-Agent": "TAK-Bot/1.0 (Bachelorarbeit Hollube; anton.hollube@gmail.com)"}
REQUEST_PAUSE = 0.5        # Hoeflichkeitspause zwischen Netz-Aufrufen (s)
NEG_CACHE_DAYS = 14        # so lange kein erneuter Versuch fuer Bruecken ohne Foto
GEOSEARCH_RADIUS_M = 150
THUMB_WIDTH = 1024
MIN_BYTES = 3000           # winzige Fehler-/Platzhalterbilder verwerfen


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_index():
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _save_index(index):
    os.makedirs(IMG_DIR, exist_ok=True)
    tmp = INDEX_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    os.replace(tmp, INDEX_FILE)  # atomar, wie die uebrigen Caches (NFA6)


def _existing_image(slug):
    for ext in ("jpg", "jpeg", "png"):
        path = os.path.join(IMG_DIR, f"{slug}.{ext}")
        if os.path.exists(path):
            return path
    return None


def _neg_cache_fresh(entry):
    if not entry or entry.get("found") is not False:
        return False
    try:
        checked = datetime.fromisoformat(entry["checked_at"])
    except (KeyError, ValueError):
        return False
    age_days = (datetime.now(timezone.utc) - checked).days
    return age_days < NEG_CACHE_DAYS


def _commons_filepath(filename):
    """Commons-Dateiname (mit/ohne 'File:'-Praefix) -> direkte Bild-URL (Thumbnail)."""
    name = filename.split("File:", 1)[-1].split("Datei:", 1)[-1]
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(name)}?width={THUMB_WIDTH}"


def _from_image_tag(tags):
    val = tags.get("image")
    if not val:
        return None
    if "commons.wikimedia.org" in val and ("File:" in val or "Datei:" in val):
        fname = unquote(val.split("File:", 1)[-1].split("Datei:", 1)[-1])
        return _commons_filepath(fname), "osm-image-tag", val
    if val.lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png"):
        return val, "osm-image-tag", val
    return None


def _from_wikidata(tags):
    qid = tags.get("wikidata")
    if not qid:
        return None
    try:
        r = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
                         headers=UA, timeout=15)
        r.raise_for_status()
        claims = r.json()["entities"][qid]["claims"]
        fname = claims["P18"][0]["mainsnak"]["datavalue"]["value"]
        return _commons_filepath(fname), "wikidata-P18", f"https://www.wikidata.org/wiki/{qid}"
    except (requests.RequestException, KeyError, IndexError):
        return None


def _from_wikipedia(tags):
    val = tags.get("wikipedia")
    if not val or ":" not in val:
        return None
    lang, title = val.split(":", 1)
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}",
            headers=UA, timeout=15)
        r.raise_for_status()
        src = r.json().get("thumbnail", {}).get("source")
        if src:
            return src, "wikipedia-summary", f"https://{lang}.wikipedia.org/wiki/{quote(title)}"
    except requests.RequestException:
        return None
    return None


def _from_commons_geosearch(lat, lon):
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=15, params={
            "action": "query", "format": "json", "list": "geosearch",
            "gscoord": f"{lat}|{lon}", "gsradius": GEOSEARCH_RADIUS_M,
            "gslimit": 10, "gsnamespace": 6})
        r.raise_for_status()
        hits = r.json().get("query", {}).get("geosearch", [])
        for hit in hits:  # nach Distanz sortiert; erstes Bild-Format gewinnt
            title = hit["title"]
            if title.lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png"):
                return _commons_filepath(title), "commons-geosearch", \
                    f"https://commons.wikimedia.org/wiki/{quote(title)}"
    except requests.RequestException:
        return None
    return None


def _download(url):
    """Laedt eine Bild-URL; gibt (bytes, ext) zurueck oder None (nur jpeg/png)."""
    r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    ext = {"image/jpeg": "jpg", "image/png": "png"}.get(ctype)
    if not ext or len(r.content) < MIN_BYTES:
        return None
    return r.content, ext


def _resolve(tags, lat, lon):
    """Probiert die Quellen der Reihe nach; gibt (url, source, source_url) oder None."""
    for resolver in (lambda: _from_image_tag(tags),
                     lambda: _from_wikidata(tags),
                     lambda: _from_wikipedia(tags),
                     lambda: _from_commons_geosearch(lat, lon)):
        hit = resolver()
        time.sleep(REQUEST_PAUSE)
        if hit:
            return hit
    return None


def update_bridge_images(limit=None):
    """Beschafft fehlende Bruecken-Bilder ueber den Wikimedia-Stack (idempotent, mit Negativ-Cache)."""
    logging.info("[*] Beschaffe Bruecken-Bilder (Wikimedia)...")
    os.makedirs(IMG_DIR, exist_ok=True)
    bridges = load_json_data("bridges.json")
    index = _load_index()
    fetched = 0

    seen = set()
    for poi in bridges:
        tags = poi.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        slug = slugify(name)
        if slug in seen:
            continue  # dieselbe Bruecke (mehrere OSM-Ways) nur einmal behandeln
        seen.add(slug)

        if _existing_image(slug):
            continue  # schon vorhanden (auch manuell abgelegte) -> nicht ueberschreiben
        if _neg_cache_fresh(index.get(slug)):
            continue  # kuerzlich erfolglos geprueft -> APIs schonen

        center = poi.get("center", {})
        lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue

        try:
            hit = _resolve(tags, lat, lon)
            if hit:
                url, source, source_url = hit
                blob = _download(url)
                time.sleep(REQUEST_PAUSE)
                if blob:
                    data, ext = blob
                    with open(os.path.join(IMG_DIR, f"{slug}.{ext}"), "wb") as f:
                        f.write(data)
                    index[slug] = {"name": name, "source": source, "url": source_url,
                                   "license": "frei lizenziert (Attribution: siehe Quelle)",
                                   "fetched_at": _now()}
                    fetched += 1
                    logging.info(f"[+] Bild fuer '{name}' via {source}.")
                    _save_index(index)
                    if limit and fetched >= limit:
                        break
                    continue
            # nichts gefunden -> Negativ-Cache
            index[slug] = {"found": False, "checked_at": _now()}
            _save_index(index)
        except Exception as e:  # eine Bruecke darf den Lauf nicht kippen (NFA7)
            logging.error(f"[-] Bildbeschaffung fuer '{name}' fehlgeschlagen: {e}")

    logging.info(f"[+] Bruecken-Bilder aktualisiert ({fetched} neu).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    update_bridge_images()
