import streamlit as st
import json

def mostrar_pantalla_chat():
    st.title("🤖 Asistente Virtual Inmobiliario")
    st.write("Preguntale a la Inteligencia Artificial cualquier cosa sobre tu base de datos de casas.")
    
    # Inicializar el historial del chat
    if "mensajes_chat" not in st.session_state:
        st.session_state.mensajes_chat = [
            {"role": "assistant", "content": "¡Hola! Analicé todas tus casas guardadas. ¿Qué querés buscar hoy? (Ej: 'Mostrame casas con jardín a menos de 70 mil USD')"}
        ]

    # Mostrar el historial del chat
    for mensaje in st.session_state.mensajes_chat:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # Capturar nueva pregunta
    pregunta = st.chat_input("Escribí tu pregunta acá...")
    if pregunta:
        # Mostrar la pregunta del usuario
        with st.chat_message("user"):
            st.markdown(pregunta)
        st.session_state.mensajes_chat.append({"role": "user", "content": pregunta})

        # Preparar la base de datos para la IA
        with st.spinner("🤖 Pensando..."):
            from src.gsheets import get_todas_las_casas, get_votos
            df_casas = get_todas_las_casas()
            df_votos = get_votos()
            
            # Filtramos un poco los datos para no mandarle columnas inútiles y que le cueste entender
            if not df_casas.empty:
                # Nos quedamos con las columnas clave
                columnas = ["id", "url_aviso", "barrio", "dirección", "precio", "moneda", "ambientes", "m2_cubiertos", "m2_terreno", "dormitorios", "resumen_corto", "puntaje_zona", "mejor_rasgo"]
                casas_limpias = []
                for _, row in df_casas.iterrows():
                    casa_dict = {col: str(row.get(col, "")) for col in columnas}
                    # Agregar qué votamos
                    voto_cris = "Ninguno"
                    voto_esposa = "Ninguno"
                    if not df_votos.empty:
                        vc = df_votos[(df_votos["casa_id"] == str(row["id"])) & (df_votos["usuario"] == "Cristian")]
                        ve = df_votos[(df_votos["casa_id"] == str(row["id"])) & (df_votos["usuario"] == "Esposa")]
                        if not vc.empty: voto_cris = vc.iloc[-1]["voto"]
                        if not ve.empty: voto_esposa = ve.iloc[-1]["voto"]
                    
                    casa_dict["voto_cristian"] = voto_cris
                    casa_dict["voto_esposa"] = voto_esposa
                    casas_limpias.append(casa_dict)
                    
                contexto_json = json.dumps(casas_limpias, indent=2, ensure_ascii=False)
            else:
                contexto_json = "La base de datos está vacía."

            prompt = f"""
            Sos el Asistente Virtual personal de una pareja (Cristian y su esposa) que está buscando comprar una casa.
            Ellos armaron una base de datos de casas que les interesan, y quieren que los ayudes a filtrarla, buscar patrones o encontrar la casa ideal según sus preguntas.
            
            Acá está la base de datos actual de TODAS sus casas guardadas en formato JSON:
            {contexto_json}
            
            INSTRUCCIONES:
            - Respondé de forma amable, clara y directa.
            - Si te preguntan por una casa específica, pasales siempre el "url_aviso" para que puedan entrar a verla, y armá un link usando Markdown: [Ver Casa](url)
            - Si te piden casas que necesitan "menos trabajo de remodelación" o "con jardín", leé el "resumen_corto" y deducilo desde ahí (ya que la IA extrajo esos datos de los avisos originales).
            - Tené en cuenta que si el "voto_cristian" o "voto_esposa" dice "❌ Descartar", significa que ya no les interesa esa casa.
            
            Pregunta de la pareja: {pregunta}
            """

            from google import genai
            import os
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                client = genai.Client(api_key=api_key)
                
                interaction = client.interactions.create(
                    model='gemini-3.7-flash',
                    input=prompt
                )
                respuesta_ia = interaction.output_text
            except Exception as e:
                respuesta_ia = f"Perdón, tuve un problema al procesar la información: {e}"

        # Mostrar respuesta
        with st.chat_message("assistant"):
            st.markdown(respuesta_ia)
        st.session_state.mensajes_chat.append({"role": "assistant", "content": respuesta_ia})
