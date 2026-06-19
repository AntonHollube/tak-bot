"""Hilfe-Feature: Uebersicht der verfuegbaren Bot-Befehle fuer den ATAK-Chat."""

def execute(lat, lon, args):
    """Gibt die Liste der verfuegbaren Bot-Befehle als Chat-Text zurueck."""
    help_text = (
        "Befehle (Optional mit Radius Stufe 1-3):\n"
        " !b [1-3]    -> Bruecken\n"
        " !t [1-3]    -> Tunnel & Unterfuehrungen\n"
        " !hosp [1-3] -> Kliniken\n"
        " !p [1-3]    -> Aktuelle Flusspegel\n"
        " !w [1-3]    -> Wetter- & Wind-Lagebild\n"
        " !wifi [1-3] -> Notfall-WLAN-Hotspots\n"
        " !h          -> Diese Hilfe\n"
        "Beispiel: '!t 2' sucht Tunnel im mittleren Umkreis."
    )
    return help_text, []