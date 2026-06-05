import os

def save_kml_file(filename, document_name, styles_xml, placemarks_xml):
    """
    Kapselt XML-Placemarks in eine valide KML-Dokumentstruktur 
    und persistiert diese im lokalen Dateisystem.
    """
    # KML-Header aufbauen
    kml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{document_name}</name>
{styles_xml}
"""
    # KML-Footer definieren
    kml_footer = """  </Document>
</kml>"""

    full_kml = kml_header + placemarks_xml + kml_footer
    
    try:
        # Datei schreiben
        with open(filename, "w", encoding="utf-8") as f:
            f.write(full_kml)
        print(f"[+] KML gespeichert: {os.path.abspath(filename)}")
        return True
    except Exception as e:
        print(f"[-] I/O-Fehler bei KML-Speicherung: {e}")
        return False