import h3

H3_RESOLUTION = 7

# Diskrete Suchradius-Stufen: Stufenwert -> Anzahl der k-Ringe um die Zentrumszelle.
_RING_LEVELS = {1: 1, 2: 3, 3: 6}


def get_search_area(lat, lon, level):
    """
    Ermittelt die H3-Zellen fuer einen diskreten Suchradius (k-Ring) um die
    Nutzerposition. Rueckgabe ist ein set, damit die nachgelagerte
    Mitgliedschaftspruefung in O(1) erfolgt.
    """
    # Defensives Casting: args kommen als Strings aus cmd_string.split().
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = 1
    rings = _RING_LEVELS.get(level, 6 if level >= 3 else 1)

    try:
        # h3-py v4 API
        center_hex = h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
        return set(h3.grid_disk(center_hex, rings))
    except AttributeError:
        # Fallback fuer h3-py v3
        center_hex = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
        return set(h3.k_ring(center_hex, rings))