import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """Berechnet die Distanz zwischen zwei Koordinaten in Metern (Haversine)."""
    R = 6371000 # Erdradius in Metern
    
    # In Bogenmaß umrechnen
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    # Haversine-Formel anwenden
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Berechnet den Winkel (Azimut) zwischen zwei Punkten in Grad."""
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1) # Umrechnung Bogenmaß
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    d_lon = lon2_rad - lon1_rad
    y = math.sin(d_lon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon)
    
    # Winkel berechnen und normalisieren
    return (math.degrees(math.atan2(y, x)) + 360) % 360