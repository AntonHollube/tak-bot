def execute(lat, lon, args):
    """
    Gibt eine strukturierte Übersicht der verfügbaren Bot-Kommandos zurück.
    Dient als direkte Hilfe-Schnittstelle innerhalb des ATAK-Chat-Clients.
    """
    help_text = (
        "Befehle (Optional mit Radius Stufe 1-3):\n"
        " !b [1-3]   -> Bruecken\n"
        " !t [1-3]   -> Tunnel & Unterfuehrungen\n"
        " !hosp [1-3]-> Kliniken\n"
        " !p [1-3]   -> Aktuelle Flusspegel \n"
        " !w [1-3]   -> Wetter- & Wind-Lagebild \n"
        " !wifi [1-3]-> Notfall-WLAN-Hotspots \n"
        " !a         -> Live-Flugzeug-Tracking umschalten\n"
        "Beispiel: '!t 2' sucht Tunnel im mittleren Umkreis."
    )
    return help_text, []