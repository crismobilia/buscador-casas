import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

def extraer_datos_aviso(url):
    # 1. Descargar la página web con Jina AI
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        'X-Return-Format': 'markdown',
        'User-Agent': 'BuscadorCasasQuilmes/1.0'
    }
    
    try:
        response = requests.get(jina_url, headers=headers, timeout=25)
        texto_pagina = response.text
    except Exception as e:
        return {"error": f"No se pudo descargar la página. Error: {e}"}

    # 2. Pedirle a Gemini que extraiga los datos
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Sos un asistente experto en bienes raíces buscando casas en Quilmes, Argentina.
    Analizá el siguiente texto (Markdown) extraído de un aviso inmobiliario web y extraé los datos.
    Si un dato no está en el texto, dejalo vacío (null o ""). NO inventes información.
    
    Quiero que respondas ÚNICAMENTE en formato JSON, usando exactamente estas claves:
    - título (texto)
    - precio (número, sin puntos ni comas, ej: 150000)
    - moneda (texto: "USD" o "ARS")
    - expensas (número, sin puntos)
    - m2_cubiertos (número)
    - m2_terreno (número)
    - ambientes (número)
    - dormitorios (número)
    - baños (número)
    - cochera (número, 0 si no dice)
    - antigüedad (número, cantidad de años)
    - dirección (texto, intentá armar la calle y altura exacta, o la intersección si la dice)
    - barrio (texto, ej: "Quilmes", "Quilmes Oeste", "Bernal")
    - resumen_corto (texto, máximo 2 renglones resumiendo lo más destacable del aviso en lenguaje simple)
    - foto_url (buscá en el Markdown el link de la primera imagen o la foto principal de la propiedad. Suele estar con formato ![texto](link))
    
    Texto del aviso:
    ---
    {texto_pagina[:25000]}
    ---
    """
    
    try:
        # Usamos el modelo gemini-3.7-flash y la API Interactions recomendada
        interaction = client.interactions.create(
            model='gemini-3.7-flash',
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json"
            }
        )
        
        datos = json.loads(interaction.output_text)
        return datos
    except Exception as e:
        return {"error": f"Error al procesar con Gemini: {e}"}

def extraer_links_de_lista(url):
    """
    Descarga una página usando Jina AI (para ejecutar JavaScript de Tokko/inmobiliarias locales)
    y le pide a Gemini que encuentre todos los links a las propiedades individuales.
    """
    try:
        # Usamos r.jina.ai para saltear el problema de que el HTML venga vacío por JavaScript
        jina_url = f"https://r.jina.ai/{url}"
        
        headers = {
            'X-Return-Format': 'markdown',
            'User-Agent': 'BuscadorCasasQuilmes/1.0'
        }
        
        response = requests.get(jina_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        markdown_text = response.text
        
        # Limitar tamaño para no pasarnos
        markdown_text = markdown_text[:100000]
        
        prompt = f"""
        Tengo este texto (en formato Markdown) extraído de una página web de una inmobiliaria ({url}):
        
        {markdown_text}
        
        Tu tarea es leer el texto e identificar ÚNICAMENTE los links que apuntan a la página de detalle de una propiedad (casa, departamento, etc.). 
        En el markdown vas a ver los links entre paréntesis () después de los corchetes [].
        Asegurate de que las URLs estén completas (que empiecen con http o https). Si son rutas relativas (como /propiedad/123), armalas usando como base {url}.
        Ignorá links de contacto, 'sobre nosotros', páginas de búsqueda general o redes sociales.
        
        Devolvé ÚNICAMENTE un JSON con una lista de los links válidos y completos, con este formato exacto:
        {{
            "links": ["url1", "url2", ...]
        }}
        """
        
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        interaction = client.interactions.create(
            model='gemini-3.7-flash',
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json"
            }
        )
        
        resultado = json.loads(interaction.output_text)
        return {"status": "ok", "links": resultado.get("links", [])}
        
    except Exception as e:
        print("Error en extraer_links_de_lista:", e)
        return {"status": "error", "message": str(e), "links": []}
