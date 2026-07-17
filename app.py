"""
Interfaz de Sophia en Streamlit.

Ejecutar con: streamlit run app.py
Requiere haber corrido antes: python ingest.py (para tener el índice FAISS listo)
"""

import os
import streamlit as st

from rag_chain import cargar_cadena, preguntar
from logger import registrar_interaccion, Cronometro

from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONO_PATH = os.path.join(BASE_DIR, "assets", "sophia.png")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "sophia-lockup.png")

st.set_page_config(
    page_title="Sophia AI Agent",
    page_icon=Image.open(ICONO_PATH),
)

col_izq, col_centro, col_der = st.columns([1, 2, 1])
with col_centro:
    st.image(LOGO_PATH, width=400)

st.markdown(
    "<p style='text-align: center; color: gray;'>"
    "AI Agent para resolución de errores técnicos de LangChain, "
    "LangGraph, RAG, FAISS, Cohere y Streamlit."
    "</p>",
    unsafe_allow_html=True,
)

st.info(
    "⚠️ SophIA: es un AI Agent, puede cometer errores. "
    "Las respuestas se basan únicamente en los documentos indexados.",
    icon="🤖",
)

INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faiss_index_sophia")

if not os.path.exists(INDEX_PATH):
    st.error(
        "No se encontró el índice de documentos. "
        "Corre primero `python ingest.py` para construirlo."
    )
    st.stop()


@st.cache_resource
def obtener_cadena():
    """Carga la cadena una sola vez por sesión (no en cada pregunta)"""
    return cargar_cadena(k=3)


cadena, retriever = obtener_cadena()

if "historial" not in st.session_state:
    st.session_state.historial = []

# Muestra el historial de la conversación
for turno in st.session_state.historial:
    with st.chat_message(turno["rol"]):
        st.markdown(turno["contenido"])
        if turno.get("fuentes"):
            with st.expander("📄 Fuentes consultadas"):
                for url in turno["fuentes"]:
                    st.markdown(f"- {url}")

pregunta = st.chat_input("Dime que error necesitass resolver...")

if pregunta:
    st.session_state.historial.append({"rol": "user", "contenido": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            with Cronometro() as cronometro:
                respuesta, fuentes = preguntar(cadena, retriever, pregunta)

            st.markdown(respuesta)
            with st.expander("📄 Fuentes consultadas"):
                for url in fuentes:
                    st.markdown(f"- {url}")

            # Botón de feedback (requisito del desafío)
            col1, col2 = st.columns(2)
            col1.button("👍 Útil", key=f"up_{len(st.session_state.historial)}")
            col2.button("👎 No útil", key=f"down_{len(st.session_state.historial)}")

    registrar_interaccion(pregunta, respuesta, fuentes, cronometro.duracion)

    st.session_state.historial.append(
        {"rol": "assistant", "contenido": respuesta, "fuentes": fuentes}
    )
