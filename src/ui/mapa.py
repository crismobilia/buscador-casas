import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from src.gsheets import get_todas_las_casas

def mostrar_pantalla_mapa():
    st.title("🗺️ Mapa de Casas")
    
    from src.gsheets import get_todas_las_casas, get_votos
    df_casas = get_todas_las_casas()
    if df_casas.empty:
        st.info("No hay casas para mostrar.")
        return
        
    df_votos = get_votos()
        
    # Filtrar solo las que pudimos ubicar en el mapa
    df_mapa = df_casas[df_casas['lat'].astype(str).str.strip() != ""]
    df_mapa = df_mapa[df_mapa['lat'].notna()]
    
    if df_mapa.empty:
        st.warning("Hay casas guardadas, pero ninguna tiene coordenadas válidas todavía.")
        return
    
    import urllib.parse
    
    # Extraer lista de dominios únicos para el filtro
    dominios_unicos = set()
    for index, row in df_mapa.iterrows():
        try:
            dom = urllib.parse.urlparse(str(row.get('url_aviso', ''))).netloc.replace("www.", "")
            if dom: dominios_unicos.add(dom)
        except:
            pass
    dominios_unicos = sorted(list(dominios_unicos))
    
    # ----------------------------------------------------
    # FILTROS
    # ----------------------------------------------------
    with st.expander("🔍 Filtros y Configuración del Mapa", expanded=False):
        c1, c2, c3 = st.columns(3)
        precio_max = c1.number_input("Precio máximo", value=0, step=10000)
        ambientes_min = c2.number_input("Ambientes (mínimo)", value=0, step=1)
        ocultar_descartadas = c3.checkbox("Ocultar las que descarté", value=True)
        
        c_zona, c_inmo = st.columns(2)
        from src.geofence import esta_en_zona
        ocultar_lejanas = c_zona.checkbox("Ocultar casas fuera de la Zona configurada", value=True)
        inmobiliarias_sel = c_inmo.multiselect("Filtrar por Inmobiliaria", options=dominios_unicos, default=[])
        
        st.write("---")
        st.write("🎨 **Personalizar colores de los pines:**")
        c_col1, c_col2 = st.columns(2)
        precio_alerta = c_col1.number_input("Límite de precio (USD) para pin ROJO:", value=80000, step=5000)
        c_col2.info("Las casas más caras que ese monto saldrán rojas, las más baratas saldrán verdes.")
    
    # Aplicar filtros
    if precio_max > 0:
        df_mapa['precio_num'] = pd.to_numeric(df_mapa['precio'], errors='coerce').fillna(0)
        df_mapa = df_mapa[(df_mapa['precio_num'] <= precio_max) | (df_mapa['precio_num'] == 0)]
        
    if ambientes_min > 0:
        df_mapa['amb_num'] = pd.to_numeric(df_mapa['ambientes'], errors='coerce').fillna(0)
        df_mapa = df_mapa[df_mapa['amb_num'] >= ambientes_min]
        
    if inmobiliarias_sel:
        def match_inmo(url):
            try:
                return urllib.parse.urlparse(str(url)).netloc.replace("www.", "") in inmobiliarias_sel
            except: return False
        df_mapa = df_mapa[df_mapa['url_aviso'].apply(match_inmo)]
        
    if ocultar_lejanas:
        en_zona = []
        for index, row in df_mapa.iterrows():
            en_zona.append(esta_en_zona(row.get('lat'), row.get('lon')))
        df_mapa = df_mapa[en_zona]
        
    casas_a_mostrar = []
    for index, casa in df_mapa.iterrows():
        voto_actual = "Ninguno"
        if not df_votos.empty:
            mis_votos = df_votos[(df_votos["casa_id"] == str(casa["id"])) & (df_votos["usuario"] == st.session_state["usuario"])]
            if not mis_votos.empty:
                voto_actual = mis_votos.iloc[-1]["voto"]
                
        if ocultar_descartadas and voto_actual == "❌ Descartar":
            continue
            
        casas_a_mostrar.append(casa)
        
    if not casas_a_mostrar:
        st.warning("No hay casas para mostrar con los filtros actuales.")
        return
        
    # Calculamos el centro para enfocar la cámara
    lats = [float(c["lat"]) for c in casas_a_mostrar]
    lons = [float(c["lon"]) for c in casas_a_mostrar]
    centro_lat = sum(lats) / len(lats)
    centro_lon = sum(lons) / len(lons)
    
    # Creamos el mapa
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14)
    
    # Dibujar la zona si está configurada
    from src.geofence import get_config_zona
    config = get_config_zona()
    modo = config.get("modo", "Ninguno")
    if modo == "Radio":
        try:
            clat = float(config.get("centro_lat", 0))
            clon = float(config.get("centro_lon", 0))
            rad = float(config.get("radio_km", 0))
            if rad > 0:
                folium.Circle(
                    location=[clat, clon],
                    radius=rad * 1000, # metros
                    color='green',
                    fill=True,
                    fill_opacity=0.1
                ).add_to(m)
        except:
            pass
    elif modo == "Polígono":
        import json
        poly = config.get("poligono", "")
        if poly:
            try:
                geo = json.loads(poly)
                folium.GeoJson(geo, style_function=lambda x: {'color': 'green', 'fillOpacity': 0.1}).add_to(m)
            except:
                pass
                
    # Ponemos un pin por cada casa
    for casa in casas_a_mostrar:
        try:
            lat = float(casa["lat"])
            lon = float(casa["lon"])
            
            moneda = casa.get('moneda', 'USD')
            precio_str = casa.get('precio', '0')
            try:
                precio_num = float(precio_str)
            except:
                precio_num = 0
                
            precio_texto = f"{moneda} {precio_str}"
            
            # Determinar color
            color_fondo = "green"
            if precio_num > precio_alerta:
                color_fondo = "red"
                
            # Si es ubicación aproximada, lo mostramos distinto
            if str(casa.get("ubicacion_exacta", "")).lower() == "no":
                color_fondo = "orange"
                
            # Preparar imagen
            foto_url = str(casa.get('foto_url', ''))
            if foto_url.startswith("http"):
                img_tag = f"<img src='{foto_url}' style='width: 110px; height: 85px; object-fit: cover; border-radius: 4px;'/>"
            else:
                img_tag = f"<div style='width: 110px; height: 85px; background:#f0f0f0; border-radius: 4px; display:flex; align-items:center; justify-content:center; color:gray; font-size:10px;'>Sin foto</div>"
                
            # HTML para el globito que sale al tocar el pin (Flexbox para foto + texto)
            popup_html = f"""
            <div style='width: 280px; font-family: sans-serif; display: flex; gap: 12px; align-items: center;'>
                <div style='flex-shrink: 0;'>
                    {img_tag}
                </div>
                <div style='font-size: 11px; line-height: 1.3;'>
                    <b style='font-size: 13px;'>{precio_texto}</b><br>
                    <span style='color: gray;'>{casa.get('dirección', '')}</span><br>
                    {casa.get('ambientes', '?')} amb | {casa.get('m2_cubiertos', '?')} m²<br>
                    <a href='{casa.get('url_aviso', '#')}' target='_blank' style='display: inline-block; margin-top: 6px; text-decoration: none; background: #0078ff; color: white; padding: 3px 8px; border-radius: 4px;'>🌐 Ver aviso</a>
                </div>
            </div>
            """
            
            # HTML para el marcador visible (DivIcon)
            marcador_html = f"""
            <div style="width: 80px; text-align: center;">
                <div style="background-color: {color_fondo}; color: white; border-radius: 4px; padding: 2px 0px; font-size: 11px; font-weight: bold; border: 1px solid white; box-shadow: 1px 1px 3px rgba(0,0,0,0.5);">
                    {precio_texto}
                </div>
                <div style="font-size: 16px; color: {color_fondo}; margin-top: -6px; text-shadow: 1px 1px 1px rgba(0,0,0,0.3);">▼</div>
            </div>
            """
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{casa.get('título', '')}",
                icon=folium.DivIcon(
                    html=marcador_html,
                    icon_size=(80, 30),
                    icon_anchor=(40, 30)
                )
            ).add_to(m)
        except Exception as e:
            print("Error agregando marcador", e)
            
    st.write("Pins naranjas = Ubicación aproximada (solo barrio)")
    st_folium(m, width=1000, height=600, returned_objects=[])
