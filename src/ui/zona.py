import streamlit as st
import json
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from src.gsheets import get_sheet

def guardar_config(diccionario):
    sheet = get_sheet("Zona")
    # Borrar todo
    sheet.clear()
    sheet.append_row(["parametro", "valor"])
    for k, v in diccionario.items():
        sheet.append_row([k, str(v)])
        
    from src.geofence import get_config_zona
    get_config_zona.clear()

def mostrar_pantalla_zona():
    st.title("⚙️ Configurar Zona de Búsqueda")
    st.write("Acá podés limitar las casas que te muestra la app. Las que estén afuera de la zona se ocultan.")
    
    from src.geofence import get_config_zona
    config = get_config_zona()
    modo_actual = config.get("modo", "Ninguno")
    
    opciones = ["Ninguno (Mostrar todo)", "Radio (Kilómetros desde un punto)", "Polígono (Dibujar en el mapa)"]
    
    if modo_actual == "Ninguno":
        idx = 0
    elif modo_actual == "Radio":
        idx = 1
    elif modo_actual == "Polígono":
        idx = 2
    else:
        idx = 0
        
    modo = st.radio("Modo de restricción", opciones, index=idx)
    
    if modo == "Ninguno (Mostrar todo)":
        if st.button("Guardar cambios", type="primary"):
            guardar_config({"modo": "Ninguno"})
            st.success("Guardado. Ahora se muestran todas las casas.")
            st.rerun()
            
    elif modo == "Radio (Kilómetros desde un punto)":
        st.write("Elegí un punto central y un radio máximo.")
        
        col1, col2, col3 = st.columns(3)
        lat = col1.number_input("Latitud", value=float(config.get("centro_lat", -34.72338)), format="%f")
        lon = col2.number_input("Longitud", value=float(config.get("centro_lon", -58.26191)), format="%f")
        radio = col3.number_input("Radio en KM", value=float(config.get("radio_km", 3.0)), step=0.5)
        
        st.write("*(Por defecto es el centro de Quilmes)*")
        
        if st.button("Guardar cambios", type="primary"):
            guardar_config({
                "modo": "Radio",
                "centro_lat": lat,
                "centro_lon": lon,
                "radio_km": radio
            })
            st.success("Guardado. Se ocultarán las casas a más de esa distancia.")
            st.rerun()
            
    elif modo == "Polígono (Dibujar en el mapa)":
        st.write("Usa el botón del polígono ⬟ a la izquierda del mapa para dibujar la zona exacta que querés.")
        
        m = folium.Map(location=[-34.72338, -58.26191], zoom_start=13)
        
        # Cargar polígono guardado si hay
        if config.get("poligono"):
            try:
                geo = json.loads(config["poligono"])
                folium.GeoJson(geo).add_to(m)
            except:
                pass
                
        # Herramienta de dibujo (solo permitimos polígonos)
        draw = Draw(
            export=False,
            position='topleft',
            draw_options={
                'polyline': False,
                'rectangle': False,
                'circle': False,
                'marker': False,
                'circlemarker': False
            }
        )
        draw.add_to(m)
        
        # Mostrar el mapa y capturar cuando dibujan
        output = st_folium(m, width=800, height=500)
        
        if st.button("Guardar Dibujo Actual", type="primary"):
            dibujos = output.get("all_drawings")
            if dibujos and len(dibujos) > 0:
                # Nos quedamos con el último dibujo que hizo el usuario
                ultimo_dibujo = dibujos[-1]
                guardar_config({
                    "modo": "Polígono",
                    "poligono": json.dumps(ultimo_dibujo)
                })
                st.success("Polígono guardado. Las casas fuera de esta figura ya no aparecerán.")
                st.rerun()
            else:
                st.error("No dibujaste nada en el mapa todavía.")
