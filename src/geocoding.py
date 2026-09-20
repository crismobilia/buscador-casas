from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def obtener_coordenadas(direccion, barrio, provincia="Buenos Aires"):
    if not direccion or direccion.lower() in ["consultar", "sin dirección", "a consultar"]:
        return "", "", "no"
        
    geolocator = Nominatim(user_agent="buscador_casas_quilmes_privado")
    
    # 1. Intentar con dirección y barrio
    query = f"{direccion}, {barrio}, {provincia}, Argentina"
    try:
        location = geolocator.geocode(query, timeout=5)
        if location:
            es_exacta = "no" if "entre" in direccion.lower() or "y" in direccion.lower() else "sí"
            return location.latitude, location.longitude, es_exacta
            
        # 2. Si falla, intentar solo con el barrio para tener un punto aproximado
        loc_barrio = geolocator.geocode(f"{barrio}, {provincia}, Argentina", timeout=5)
        if loc_barrio:
            return loc_barrio.latitude, loc_barrio.longitude, "no"
            
        return "", "", "no"
    except GeocoderTimedOut:
        return "", "", "no"
