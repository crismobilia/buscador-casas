import streamlit as st
import pandas as pd
from src.ui.casas import mostrar_pantalla_casas, mostrar_pantalla_agregar
from src.ui.mapa import mostrar_pantalla_mapa

st.set_page_config(page_title="Buscador de Casas", page_icon="🏠", layout="wide")

# Login
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
        
    # Auto-login con token en la URL
    if not st.session_state["password_correct"]:
        token = st.query_params.get("token", "")
        if token == st.secrets["CONTRASEÑA_APP"]:
            st.session_state["password_correct"] = True
            
    if st.session_state["password_correct"]:
        return True

    st.title("🏠 Acceso al Buscador de Casas")
    st.write("Ingresá la contraseña para ver las casas.")
    pwd = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar", type="primary"):
        # Leemos la contraseña del archivo secrets.toml
        if pwd == st.secrets["CONTRASEÑA_APP"]:
            st.session_state["password_correct"] = True
            # Agregar el token a la URL para que quede guardado si guardan en favoritos
            st.query_params["token"] = pwd
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    return False

if not check_password():
    st.stop()

# Selección de usuario
if "usuario" not in st.session_state:
    st.title("¿Quién está usando la app?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👦 Cris", use_container_width=True):
            st.session_state["usuario"] = "Cris"
            st.rerun()
    with col2:
        if st.button("👩 Gise", use_container_width=True):
            st.session_state["usuario"] = "Gise"
            st.rerun()
    st.stop()

# Inicializar GSheets si es la primera vez
from src.gsheets import init_sheets
try:
    init_sheets()
except Exception as e:
    st.error(f"Error conectando a Google Sheets: {e}")
    st.stop()

# Menú lateral
st.sidebar.title(f"Hola, {st.session_state['usuario']}")
if st.sidebar.button("Cambiar usuario"):
    del st.session_state["usuario"]
    st.rerun()

st.sidebar.write("---")
pantalla = st.sidebar.radio("Navegación", ["🏠 Ver Casas", "🗺️ Mapa", "💕 Las de los dos", "🤖 Asistente IA", "➕ Agregar aviso", "⚙️ Configurar Zona"])

if pantalla == "🏠 Ver Casas":
    mostrar_pantalla_casas()
elif pantalla == "🗺️ Mapa":
    mostrar_pantalla_mapa()
elif pantalla == "💕 Las de los dos":
    from src.ui.favoritos import mostrar_pantalla_favoritos
    mostrar_pantalla_favoritos()
elif pantalla == "🤖 Asistente IA":
    from src.ui.chat import mostrar_pantalla_chat
    mostrar_pantalla_chat()
elif pantalla == "➕ Agregar aviso":
    mostrar_pantalla_agregar()
elif pantalla == "⚙️ Configurar Zona":
    from src.ui.zona import mostrar_pantalla_zona
    mostrar_pantalla_zona()
