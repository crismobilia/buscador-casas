import requests
import json
import time

def calcular_puntaje_zona(lat, lon):
    if not lat or not lon:
        return {
            "puntaje_zona": 0,
            "mejor_rasgo": "Sin datos de ubicación exacta",
            "peor_rasgo": "Sin datos de ubicación exacta",
            "subpuntajes": "{}"
        }
        
    lat = float(lat)
    lon = float(lon)
    
    # Consulta a Overpass API (OpenStreetMap)
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json];
    (
      node["highway"="bus_stop"](around:500, {lat}, {lon});
      node["railway"="station"](around:1500, {lat}, {lon});
      node["shop"](around:500, {lat}, {lon});
      node["amenity"="pharmacy"](around:500, {lat}, {lon});
      way["leisure"~"park|pitch|playground"](around:800, {lat}, {lon});
      node["leisure"~"park|pitch|playground"](around:800, {lat}, {lon});
      node["amenity"~"school|kindergarten"](around:800, {lat}, {lon});
      way["amenity"~"school|kindergarten"](around:800, {lat}, {lon});
      node["amenity"~"police|hospital|clinic"](around:1500, {lat}, {lon});
      way["amenity"~"police|hospital|clinic"](around:1500, {lat}, {lon});
    );
    out center;
    """
    
    try:
        headers = {'User-Agent': 'BuscadorCasasQuilmes/1.0'}
        response = requests.post(overpass_url, data={'data': query}, headers=headers, timeout=25)
        if response.status_code != 200:
            print(f"OSM Error: {response.status_code} - {response.text[:200]}")
            raise Exception("Overpass API error")
        data = response.json()
        
        paradas_colectivo = 0
        estaciones_tren = 0
        comercios = 0
        parques = 0
        escuelas = 0
        salud_seg = 0
        
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            if tags.get('highway') == 'bus_stop':
                paradas_colectivo += 1
            elif tags.get('railway') == 'station':
                estaciones_tren += 1
            elif 'shop' in tags or tags.get('amenity') == 'pharmacy':
                comercios += 1
            elif tags.get('leisure') in ['park', 'pitch', 'playground']:
                parques += 1
            elif tags.get('amenity') in ['school', 'kindergarten']:
                escuelas += 1
            elif tags.get('amenity') in ['hospital', 'clinic', 'police']:
                salud_seg += 1
                
        # Normalizar de 0 a 10
        score_transporte = min(10, (estaciones_tren * 4) + paradas_colectivo)
        score_verde = min(10, parques * 3)
        score_escuelas = min(10, escuelas * 2)
        score_servicios = min(10, salud_seg * 3)
        score_comercios = min(10, comercios // 2) # necesita 20 comercios para un 10
        
        subpuntajes = {
            "Transporte": score_transporte,
            "Espacios Verdes": score_verde,
            "Escuelas": score_escuelas,
            "Seguridad/Salud": score_servicios,
            "Comercios": score_comercios
        }
        
        # Calcular promedio pesado: Transporte 30%, Servicios 25%, Verde 20%, Escuelas 15%, Comercios 10%
        puntaje_final = (score_transporte*0.30 + score_servicios*0.25 + score_verde*0.20 + score_escuelas*0.15 + score_comercios*0.10)
        
        # Para destacar, priorizamos lo que más le interese a la familia, y descartamos comercios si es el único alto
        mejor = max(subpuntajes, key=subpuntajes.get)
        # Si comercios es el mejor, pero hay algo con puntaje similar, preferimos el otro
        for k, v in subpuntajes.items():
            if k != "Comercios" and v >= subpuntajes[mejor] - 1:
                mejor = k
                break
                
        peor = min(subpuntajes, key=subpuntajes.get)
        
        textos_mejor = {
            "Transporte": "Buen transporte público",
            "Espacios Verdes": "Plazas o parques cerca",
            "Escuelas": "Escuelas en la zona",
            "Seguridad/Salud": "Cerca de hospital o comisaría",
            "Comercios": "Zona comercial"
        }
        textos_peor = {
            "Transporte": "Poco transporte cerca",
            "Espacios Verdes": "Poco verde en la zona",
            "Escuelas": "Lejos de escuelas",
            "Seguridad/Salud": "Lejos de comisarías/hospitales",
            "Comercios": "Zona muy residencial (pocos negocios)"
        }
        
        if subpuntajes[peor] >= 6:
            peor_rasgo = "Zonificación muy completa"
        else:
            peor_rasgo = textos_peor[peor]
            
        mejor_rasgo = textos_mejor[mejor]
        if puntaje_final <= 2:
            mejor_rasgo = "Zona muy aislada"
            
        return {
            "puntaje_zona": round(puntaje_final, 1),
            "mejor_rasgo": mejor_rasgo,
            "peor_rasgo": peor_rasgo,
            "subpuntajes": json.dumps(subpuntajes)
        }
        
    except Exception as e:
        print("ERROR OSM:", e)
        return {
            "puntaje_zona": 0,
            "mejor_rasgo": "Error al calcular",
            "peor_rasgo": "Error al calcular",
            "subpuntajes": "{}"
        }
