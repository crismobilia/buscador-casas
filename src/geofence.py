import json
import math
from shapely.geometry import shape, Point
from src.gsheets import get_sheet

import streamlit as st

@st.cache_data(ttl=60) # Cachear por un minuto para no gastar cuota de API
def get_config_zona():
    sheet = get_sheet("Zona")
    data = sheet.get_all_records()
    config = {}
    for row in data:
        if "parametro" in row and "valor" in row:
            config[row["parametro"]] = row["valor"]
    return config

def calcular_distancia(lat1, lon1, lat2, lon2):
    # Formula de Haversine para sacar distancia en km
    R = 6371 # Radio de la tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return d

def esta_en_zona(lat, lon):
    if not lat or not lon:
        return True # Si no sabemos dónde es, la mostramos igual por las dudas
        
    config = get_config_zona()
    modo = config.get("modo", "Ninguno")
    
    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return True
        
    if modo == "Radio":
        try:
            centro_lat = float(config.get("centro_lat", 0))
            centro_lon = float(config.get("centro_lon", 0))
            radio_km = float(config.get("radio_km", 0))
            dist = calcular_distancia(centro_lat, centro_lon, lat, lon)
            return dist <= radio_km
        except:
            return True
            
    elif modo == "Polígono":
        poligono_str = config.get("poligono", "")
        if poligono_str:
            try:
                geom = json.loads(poligono_str)
                # shapely usa (lon, lat)
                punto = Point(lon, lat)
                poligono = shape(geom['geometry'])
                return poligono.contains(punto)
            except Exception as e:
                print("Error evaluando polígono:", e)
                return True
                
    return True
