import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from src.gsheets import get_todas_las_casas, guardar_casa, get_votos, guardar_voto
from src.gemini import extraer_datos_aviso
from src.geocoding import obtener_coordenadas

def mostrar_pantalla_agregar():
    st.title("➕ Agregar aviso")
    
    tab1, tab2, tab3 = st.tabs(["Link Individual", "Varios Links", "Desde web Inmobiliaria"])
    
    with tab1:
        st.write("Pegá el link de una casa para extraer sus datos automáticamente.")
        
        url = st.text_input("URL del aviso (ej: argenprop.com/...)")
        
        if st.button("Procesar casa", type="primary"):
            if url:
                procesar_un_link(url)
            else:
                st.error("Por favor ingresá una URL.")
                
    with tab2:
        st.write("Pegá varios links (uno por línea). Ideal si tenés una lista que armaste a mano.")
        links_texto = st.text_area("Links de las casas", height=200)
        
        if st.button("Procesar todos", type="primary"):
            links = [l.strip() for l in links_texto.split("\n") if l.strip().startswith("http")]
            if links:
                procesar_lista_links(links)
            else:
                st.error("No se encontraron links válidos (deben empezar con http).")
                
    with tab3:
        st.write("Pegá el link de la lista de resultados de la web de una **inmobiliaria local** (No Zonaprop/Argenprop). El robot va a buscar todos los links de casas en esa página y los va a cargar.")
        url_lista = st.text_input("URL de la página de resultados")
        
        if st.button("Buscar y procesar", type="primary"):
            if url_lista:
                with st.spinner("🕵️ Buscando propiedades en la página..."):
                    from src.gemini import extraer_links_de_lista
                    resultado = extraer_links_de_lista(url_lista)
                    
                if isinstance(resultado, dict) and resultado.get("status") == "error":
                    st.error(f"Hubo un error al leer la página: {resultado.get('message')}")
                    st.info("💡 Consejo: A veces los sitios bloquean el acceso automático de los robots. Intentá usar la pestaña 'Varios Links' copiándolos a mano.")
                else:
                    # Compatibility if it returns dict or list directly
                    links_encontrados = resultado.get("links", []) if isinstance(resultado, dict) else resultado
                    
                    if links_encontrados:
                        st.success(f"¡Se encontraron {len(links_encontrados)} casas! Procesando...")
                        procesar_lista_links(links_encontrados)
                    else:
                        st.warning("El robot logró leer la página, pero no encontró ningún link hacia las propiedades.")
                        st.info("🤔 ¿Por qué pasa esto? Muchas inmobiliarias (como Feray) programan mal sus páginas web usando botones invisibles en lugar de links reales (etiquetas <a>). Esto hace que el robot no pueda ver a dónde lleva el clic. En estos casos, te conviene entrar a la web y copiar los links de las casas a mano en la pestaña 'Varios Links'.")
            else:
                st.error("Por favor ingresá una URL.")

def procesar_un_link(url, mostrar_mensajes=True):
    from src.gemini import extraer_datos_aviso
    from src.geocoding import obtener_coordenadas
    from src.gsheets import guardar_casa
    import uuid
    from datetime import datetime
    
    if mostrar_mensajes:
        progreso = st.spinner("🤖 Leyendo el aviso con IA...")
    else:
        # Dummy context manager if we don't want to show spinners per house
        import contextlib
        progreso = contextlib.nullcontext()
        
    with progreso:
        datos = extraer_datos_aviso(url)
        
        if "error" in datos:
            if mostrar_mensajes: st.error(datos["error"])
            return False
            
        if mostrar_mensajes: st.success("¡Datos extraídos con éxito!")
        
        from src.osm import calcular_puntaje_zona
        
        # Buscar coordenadas
        lat, lon, exacta = obtener_coordenadas(datos.get("dirección", ""), datos.get("barrio", "Quilmes"))
        
        # Calcular puntaje de zona si tenemos coordenadas
        puntajes = calcular_puntaje_zona(lat, lon)
        
        # Armar la fila para guardar
        nuevo_id = str(uuid.uuid4())[:8]
        registro = {
            "id": nuevo_id,
            "url_aviso": url,
            "fuente": "Carga Manual",
            "fecha_alta": datetime.now().strftime("%Y-%m-%d"),
            "título": datos.get("título", ""),
            "precio": datos.get("precio", ""),
            "moneda": datos.get("moneda", ""),
            "expensas": datos.get("expensas", ""),
            "m2_cubiertos": datos.get("m2_cubiertos", ""),
            "m2_terreno": datos.get("m2_terreno", ""),
            "ambientes": datos.get("ambientes", ""),
            "dormitorios": datos.get("dormitorios", ""),
            "baños": datos.get("baños", ""),
            "cochera": datos.get("cochera", ""),
            "antigüedad": datos.get("antigüedad", ""),
            "dirección": datos.get("dirección", ""),
            "barrio": datos.get("barrio", ""),
            "lat": lat,
            "lon": lon,
            "ubicacion_exacta": exacta,
            "foto_url": datos.get("foto_url", ""),
            "resumen_corto": datos.get("resumen_corto", ""),
            "estado_aviso": "Activo",
            "puntaje_zona": puntajes["puntaje_zona"],
            "mejor_rasgo": puntajes["mejor_rasgo"],
            "peor_rasgo": puntajes["peor_rasgo"],
            "subpuntajes": puntajes["subpuntajes"]
        }
        
        # Guardamos en Google Sheets
        guardar_casa(registro)
        if mostrar_mensajes: st.success("🏠 ¡Casa guardada en la base de datos!")
        return True

def procesar_lista_links(links):
    from src.gsheets import get_todas_las_casas
    
    def normalizar_url(u):
        u = str(u).strip()
        # Sacarle el query string si es que tiene, para que url.com?x=1 sea igual a url.com
        if "?" in u:
            u = u.split("?")[0]
        # Sacarle la barra final
        if u.endswith("/"):
            u = u[:-1]
        return u.lower()
        
    # Evitar duplicados
    df_actual = get_todas_las_casas()
    links_guardados = [normalizar_url(u) for u in df_actual['url_aviso'].tolist()] if not df_actual.empty else []
    
    links_a_procesar = []
    for l in links:
        if normalizar_url(l) not in links_guardados:
            links_a_procesar.append(l)
            # Add to guardados to prevent adding the same link twice in the same batch
            links_guardados.append(normalizar_url(l))
            
    omitidos = len(links) - len(links_a_procesar)
    
    if omitidos > 0:
        st.info(f"Se omitieron {omitidos} links que ya estaban guardados en la planilla.")
        
    if not links_a_procesar:
        st.warning("No hay links nuevos para procesar.")
        return
        
    barra = st.progress(0)
    estado = st.empty()
    
    exitos = 0
    for i, url in enumerate(links_a_procesar):
        estado.write(f"Procesando {i+1} de {len(links_a_procesar)}: {url}")
        if procesar_un_link(url, mostrar_mensajes=False):
            exitos += 1
        barra.progress((i + 1) / len(links_a_procesar))
        
    estado.write("¡Proceso terminado!")
    st.success(f"Se guardaron {exitos} casas nuevas de un total de {len(links_a_procesar)} intentadas.")

def mostrar_pantalla_casas():
    st.title("🏠 Casas Guardadas")
    
    df_casas = get_todas_las_casas()
    if df_casas.empty:
        st.info("Todavía no hay casas guardadas. Usá el menú de la izquierda para agregar una.")
        return
        
    import urllib.parse
    
    # Extraer lista de dominios únicos para el filtro
    dominios_unicos = set()
    for index, row in df_casas.iterrows():
        try:
            dom = urllib.parse.urlparse(str(row.get('url_aviso', ''))).netloc.replace("www.", "")
            if dom: dominios_unicos.add(dom)
        except:
            pass
    dominios_unicos = sorted(list(dominios_unicos))
    
    df_votos = get_votos()
    
    # Filtros simples (escondidos por defecto para no molestar en el celular)
    with st.expander("🔍 Filtros y Acciones", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        precio_max = col1.number_input("Precio máximo", value=0, step=10000)
        ambientes_min = col2.number_input("Ambientes (mínimo)", value=0, step=1)
        ordenar_por = col3.selectbox("Ordenar por", ["Más recientes", "Precio (Menor a Mayor)", "Precio (Mayor a Menor)", "Ambientes (Mayor a Menor)", "M² (Mayor a Menor)"])
        ocultar_descartadas = col4.checkbox("Ocultar las que descarté", value=True)
        
        c_zona, c_inmo = st.columns([2, 2])
        from src.geofence import esta_en_zona
        ocultar_lejanas = c_zona.checkbox("Ocultar casas fuera de la Zona configurada", value=True)
        inmobiliarias_sel = c_inmo.multiselect("Filtrar por Inmobiliaria", options=dominios_unicos, default=[])
        
        # --- APLICAR FILTROS EN MEMORIA ---
        df_filtrado = df_casas.copy()
        
        if precio_max > 0:
            df_filtrado['precio_num'] = pd.to_numeric(df_filtrado['precio'], errors='coerce').fillna(0)
            df_filtrado = df_filtrado[(df_filtrado['precio_num'] <= precio_max) | (df_filtrado['precio_num'] == 0)]
            
        if ambientes_min > 0:
            df_filtrado['amb_num'] = pd.to_numeric(df_filtrado['ambientes'], errors='coerce').fillna(0)
            df_filtrado = df_filtrado[df_filtrado['amb_num'] >= ambientes_min]
            
        if inmobiliarias_sel:
            def match_inmo(url):
                try: return urllib.parse.urlparse(str(url)).netloc.replace("www.", "") in inmobiliarias_sel
                except: return False
            df_filtrado = df_filtrado[df_filtrado['url_aviso'].apply(match_inmo)]
            
        if ocultar_lejanas:
            en_zona = []
            for index, row in df_filtrado.iterrows():
                en_zona.append(esta_en_zona(row.get('lat'), row.get('lon')))
            df_filtrado = df_filtrado[en_zona]
            
        # Pre-calcular qué casas quedan (considerando descartadas)
        casas_a_mostrar = []
        for index, casa in df_filtrado.iterrows():
            voto_actual = "Ninguno"
            if not df_votos.empty:
                mis_votos = df_votos[(df_votos["casa_id"] == str(casa["id"])) & (df_votos["usuario"] == st.session_state["usuario"])]
                if not mis_votos.empty: voto_actual = mis_votos.iloc[-1]["voto"]
                    
            if ocultar_descartadas and voto_actual == "❌ Descartar": continue
                
            casa_dict = casa.to_dict()
            casa_dict["voto_actual"] = voto_actual
            casas_a_mostrar.append(casa_dict)
            
        # --- BOTONES DE ACCIÓN ---
        st.write("---")
        cantidad = len(casas_a_mostrar)
        pendientes = [c for c in casas_a_mostrar if "Error" in str(c.get("mejor_rasgo", ""))]
        
        c_acc1, c_acc2 = st.columns(2)
        
        if c_acc1.button(f"🔄 Recalcular {len(pendientes)} zonas pendientes", disabled=(len(pendientes)==0), use_container_width=True):
            from src.osm import calcular_puntaje_zona
            from src.gsheets import get_sheet
            import time
            import src.gsheets
            
            sheet = get_sheet("Casas")
            cols_headers = sheet.row_values(1)
            
            progreso = st.progress(0)
            texto_prog = st.empty()
            
            for idx, c in enumerate(pendientes):
                texto_prog.write(f"Recalculando {idx+1} de {len(pendientes)}... (Esperando 6s para no saturar el servidor de mapas)")
                
                # Respetar rate limits de OSM API (esperar 6 segundos)
                if idx > 0:
                    time.sleep(6)
                    
                lat, lon = c.get("lat"), c.get("lon")
                if lat and lon:
                    nuevos = calcular_puntaje_zona(lat, lon)
                    # Convertimos el ID explícitamente a string porque gspread.find tira error si no lo es
                    cell = sheet.find(str(c["id"]))
                    if cell:
                        sheet.update_cell(cell.row, cols_headers.index("puntaje_zona")+1, nuevos["puntaje_zona"])
                        sheet.update_cell(cell.row, cols_headers.index("mejor_rasgo")+1, nuevos["mejor_rasgo"])
                        sheet.update_cell(cell.row, cols_headers.index("peor_rasgo")+1, nuevos["peor_rasgo"])
                        sheet.update_cell(cell.row, cols_headers.index("subpuntajes")+1, nuevos["subpuntajes"])
                
                progreso.progress((idx + 1) / len(pendientes))
                
            texto_prog.write("¡Recálculo completado!")
            src.gsheets.get_todas_las_casas.clear()
            st.rerun()
            
        if c_acc2.button(f"🗑️ Borrar las {cantidad} casas mostradas", type="secondary", use_container_width=True):
            if cantidad > 0:
                ids_a_borrar = [str(c["id"]) for c in casas_a_mostrar]
                # Quedarnos solo con las casas que NO queremos borrar
                df_restantes = df_casas[~df_casas['id'].astype(str).isin(ids_a_borrar)]
                
                from src.gsheets import get_sheet
                import src.gsheets
                sheet_casas = get_sheet("Casas")
                sheet_casas.clear()
                from src.gsheets import CASAS_COLS
                
                # Armar tabla para resubir
                datos_nuevos = [CASAS_COLS]
                # Asegurar que las columnas coincidan en orden
                for _, row in df_restantes.iterrows():
                    fila = [str(row.get(col, "")) for col in CASAS_COLS]
                    datos_nuevos.append(fila)
                    
                sheet_casas.update(datos_nuevos)
                
                src.gsheets.get_todas_las_casas.clear()
                st.rerun()
        
    # Ordenar
    if ordenar_por != "Más recientes":
        # Extraer a pandas dataframe para ordenar fácil
        df_orden = pd.DataFrame(casas_a_mostrar)
        if not df_orden.empty:
            if ordenar_por == "Precio (Menor a Mayor)":
                df_orden['precio_num'] = pd.to_numeric(df_orden['precio'], errors='coerce').fillna(float('inf'))
                df_orden = df_orden.sort_values(by='precio_num', ascending=True)
            elif ordenar_por == "Precio (Mayor a Menor)":
                df_orden['precio_num'] = pd.to_numeric(df_orden['precio'], errors='coerce').fillna(0)
                df_orden = df_orden.sort_values(by='precio_num', ascending=False)
            elif ordenar_por == "Ambientes (Mayor a Menor)":
                df_orden['amb_num'] = pd.to_numeric(df_orden['ambientes'], errors='coerce').fillna(0)
                df_orden = df_orden.sort_values(by='amb_num', ascending=False)
            elif ordenar_por == "M² (Mayor a Menor)":
                df_orden['m2_num'] = pd.to_numeric(df_orden['m2_cubiertos'], errors='coerce').fillna(0)
                df_orden = df_orden.sort_values(by='m2_num', ascending=False)
            casas_a_mostrar = df_orden.to_dict('records')
        
    st.write(f"Mostrando {len(casas_a_mostrar)} casas.")
    
    import urllib.parse
    
    # Mostrar casas en grilla de 3 columnas (creando filas reales para que queden alineadas)
    for i in range(0, len(casas_a_mostrar), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(casas_a_mostrar):
                casa = casas_a_mostrar[i + j]
                col = cols[j]
                voto_actual = casa["voto_actual"]
                
                with col:
                    with st.container(border=True):
                        foto = str(casa.get("foto_url", ""))
                        if foto.startswith("http"):
                            st.image(foto, width='stretch')
                        else:
                            st.write("📷 *(Sin foto)*")
                        
                        moneda = casa.get('moneda', 'USD')
                        precio = casa.get('precio', 'Consulte')
                        
                        direccion = str(casa.get('dirección', '')).strip()
                        barrio = str(casa.get('barrio', '')).strip()
                        ubicacion_texto = f"{direccion}, {barrio}".strip(", ")
                        if str(casa.get('ubicacion_exacta', '')).lower() == 'no':
                            ubicacion_texto = f"Aprox: {ubicacion_texto}"
                            
                        st.markdown(f"""
                        <div style='line-height:1.2; margin-bottom: 10px'>
                            <h4 style='margin-bottom:2px'>{moneda} {precio}</h4>
                            <span style='font-size:0.85em; color:gray'>{ubicacion_texto}</span><br>
                            <span style='font-size:0.85em'>📐 {casa.get('ambientes', '?')} amb | {casa.get('m2_cubiertos', '?')} m² | 🛏️ {casa.get('dormitorios', '?')} dorm</span><br>
                            <span style='font-size:0.85em'>💡 {casa.get('resumen_corto', '')}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Mostrar puntaje si existe
                        puntaje = str(casa.get("puntaje_zona", "")).strip()
                        mejor_rasgo = str(casa.get("mejor_rasgo", ""))
                        if puntaje:
                            if "Error" in mejor_rasgo:
                                c_err, c_btn = st.columns([3, 1])
                                c_err.markdown(f"<span style='font-size:0.8em; color:orange'>⚠️ Error de zona</span>", unsafe_allow_html=True)
                                if c_btn.button("🔄", key=f"recalc_{casa['id']}", use_container_width=True):
                                    from src.osm import calcular_puntaje_zona
                                    from src.gsheets import get_sheet
                                    lat, lon = casa.get("lat"), casa.get("lon")
                                    if lat and lon:
                                        nuevos = calcular_puntaje_zona(lat, lon)
                                        # Update the specific row
                                        sheet = get_sheet("Casas")
                                        # Encontrar la fila (siempre con str)
                                        cell = sheet.find(str(casa["id"]))
                                        if cell:
                                            # Columnas de zona: puntaje(24), mejor(25), peor(26), sub(27)
                                            cols_headers = sheet.row_values(1)
                                            sheet.update_cell(cell.row, cols_headers.index("puntaje_zona")+1, nuevos["puntaje_zona"])
                                            sheet.update_cell(cell.row, cols_headers.index("mejor_rasgo")+1, nuevos["mejor_rasgo"])
                                            sheet.update_cell(cell.row, cols_headers.index("peor_rasgo")+1, nuevos["peor_rasgo"])
                                            sheet.update_cell(cell.row, cols_headers.index("subpuntajes")+1, nuevos["subpuntajes"])
                                            import src.gsheets
                                            src.gsheets.get_todas_las_casas.clear()
                                            st.rerun()
                            else:
                                st.markdown(f"<span style='font-size:0.8em'>⭐ Zona: {puntaje}/10 | 👍 {mejor_rasgo}</span>", unsafe_allow_html=True)
                        
                        # Extraer dominio de la inmobiliaria
                        url_aviso = str(casa["url_aviso"])
                        dominio = "la Inmobiliaria"
                        try:
                            dominio_p = urllib.parse.urlparse(url_aviso).netloc
                            dominio_p = dominio_p.replace("www.", "")
                            if dominio_p:
                                dominio = dominio_p
                        except:
                            pass
                            
                        # Si ya votó, lo mostramos chiquito
                        if voto_actual != "Ninguno":
                            st.markdown(f"<div style='text-align:center; font-size:0.7em; color:gray; margin-bottom:2px'>Votaste: {voto_actual}</div>", unsafe_allow_html=True)
                            
                        # Botones en una sola fila para ahorrar espacio vertical!
                        c_link, c_like, c_desc = st.columns([5, 2, 2])
                        c_link.link_button(f"🌐 {dominio}", url_aviso, use_container_width=True)
                        
                        if c_like.button("❤️", key=f"like_{casa['id']}", use_container_width=True):
                            guardar_voto(str(casa["id"]), st.session_state["usuario"], "❤️ Me gusta", "")
                            st.rerun()
                        if c_desc.button("❌", key=f"desc_{casa['id']}", use_container_width=True):
                            guardar_voto(str(casa["id"]), st.session_state["usuario"], "❌ Descartar", "")
                            st.rerun()
