import streamlit as st
from src.gsheets import get_todas_las_casas, get_votos

def mostrar_pantalla_favoritos():
    st.title("💖 Las de los dos")
    st.write("Acá aparecen las casas a las que ambos le dieron 'Me gusta'.")
    
    df_casas = get_todas_las_casas()
    df_votos = get_votos()
    
    if df_casas.empty or df_votos.empty:
        st.info("Todavía no hay votos registrados.")
        return
        
    # Agrupar votos por casa_id y usuario
    # Nos quedamos con el último voto de cada uno para cada casa
    votos_unicos = df_votos.drop_duplicates(subset=["casa_id", "usuario"], keep="last")
    
    # Filtrar solo los "Me gusta"
    me_gusta = votos_unicos[votos_unicos["voto"] == "❤️ Me gusta"]
    
    # Contar cuántos "Me gusta" tiene cada casa
    conteo = me_gusta.groupby("casa_id").size()
    
    # Las que tienen 2 "Me gusta" (asumiendo que solo hay 2 usuarios: Cristian y Esposa)
    casas_match = conteo[conteo >= 2].index.tolist()
    
    if not casas_match:
        st.info("Por ahora no hay ninguna casa que les guste a los dos al mismo tiempo. ¡A seguir buscando!")
        return
        
    df_match = df_casas[df_casas["id"].astype(str).isin(casas_match)]
    
    st.success(f"¡Tienen {len(df_match)} casas en común!")
    
    # Mostrar lado a lado (máximo 3 columnas para que no se rompa el celu)
    cols = st.columns(min(3, len(df_match)))
    
    for i, (index, casa) in enumerate(df_match.iterrows()):
        col = cols[i % len(cols)]
        
        with col:
            with st.container(border=True):
                foto = str(casa.get("foto_url", ""))
                if foto.startswith("http"):
                    st.image(foto, width='stretch')
                
                moneda = casa.get('moneda', 'USD')
                precio = casa.get('precio', 'Consulte')
                st.subheader(f"{moneda} {precio}")
                st.write(f"**{casa.get('barrio', '')}**")
                
                st.write(f"📏 {casa.get('ambientes', '?')} amb | {casa.get('m2_cubiertos', '?')} m²")
                
                if str(casa.get("puntaje_zona", "")).strip():
                    st.caption(f"⭐ Zona: {casa.get('puntaje_zona')}/10")
                    
                st.link_button("Ver aviso", str(casa["url_aviso"]), type='primary')
