import gspread
import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

CASAS_COLS = ["id", "url_aviso", "fuente", "fecha_alta", "título", "precio", "moneda", "expensas", "m2_cubiertos", "m2_terreno", "ambientes", "dormitorios", "baños", "cochera", "antigüedad", "dirección", "barrio", "lat", "lon", "ubicacion_exacta", "foto_url", "resumen_corto", "estado_aviso", "fecha_ultima_verificacion", "puntaje_zona", "mejor_rasgo", "peor_rasgo", "subpuntajes"]
VOTOS_COLS = ["casa_id", "usuario", "voto", "nota", "fecha"]

@st.cache_resource
def get_gspread_client():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(
        credentials_dict, scopes=SCOPES
    )
    return gspread.authorize(credentials)

@st.cache_resource
def get_gspread_doc():
    client = get_gspread_client()
    return client.open_by_key(st.secrets["SHEET_ID"])

@st.cache_resource
def get_sheet(tab_name):
    doc = get_gspread_doc()
    try:
        return doc.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        return doc.add_worksheet(title=tab_name, rows=100, cols=30)

@st.cache_data(ttl=3600)
def check_headers_exist():
    # Cacheamos esto por una hora para no revisar los headers cada vez que arranca la app
    doc = get_gspread_doc()
    return True

def init_sheets():
    # Evitamos llamar a la API si ya lo revisamos recientemente
    try:
        if check_headers_exist():
            return
    except:
        pass

    casas_sheet = get_sheet("Casas")
    if not casas_sheet.row_values(1):
        casas_sheet.append_row(CASAS_COLS)
        
    votos_sheet = get_sheet("Votos")
    if not votos_sheet.row_values(1):
        votos_sheet.append_row(VOTOS_COLS)
        
    fuentes_sheet = get_sheet("Fuentes")
    if not fuentes_sheet.row_values(1):
        fuentes_sheet.append_row(["nombre", "url", "tipo", "activa", "ultima_corrida", "notas"])
        
    zona_sheet = get_sheet("Zona")
    if not zona_sheet.row_values(1):
        zona_sheet.append_row(["parametro", "valor"])

@st.cache_data(ttl=10)
def get_todas_las_casas():
    sheet = get_sheet("Casas")
    # get_all_records() gasta 1 cuota de lectura
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def guardar_casa(datos_dict):
    sheet = get_sheet("Casas")
    # Ya no llamamos a sheet.row_values(1) porque sabemos cuáles son las columnas
    row = [datos_dict.get(c, "") for c in CASAS_COLS]
    sheet.append_row(row)
    get_todas_las_casas.clear() # Limpiar cache para que se vea reflejado al instante

@st.cache_data(ttl=10)
def get_votos():
    sheet = get_sheet("Votos")
    data = sheet.get_all_values()
    if not data or len(data) == 1:
        return pd.DataFrame(columns=VOTOS_COLS)
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Mapeo de nombres viejos a nombres nuevos para no perder votos históricos
    df['usuario'] = df['usuario'].replace({"Cristian": "Cris", "Esposa": "Gise"})
    
    return df

def guardar_voto(casa_id, usuario, voto, nota):
    sheet = get_sheet("Votos")
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([casa_id, usuario, voto, nota, fecha])
    get_votos.clear() # Limpiar cache para que se vea reflejado al instante
