"""
Lógica central de Sophia: recuperación de contexto + generación de respuesta.

Centralizado aquí a propósito (en vez de disperso en app.py) para que,
cuando quieras ajustar el prompt o la lógica de recuperación más adelante,
tengas un solo lugar donde iterar.
"""

import os
from dotenv import load_dotenv
from langchain_cohere import CohereEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "faiss_index_sophia")

PROMPT_SOPHIA = """Eres Sophia, un AI Agent que recibe un error, razona sobre el, consultando documentación de LangChain, LangGraph, RAG, FAISS, Cohere, Streamlit y GitHub oficial. Detecta, diagnostica y resuelve errores técnicos, combinando búsqueda semántica y razonamiento agéntico. Recupera y devuelve una solución explicada. Actúa como un desarrollador Senior y especializado en dar soluciones a errores técnicos que se presentan con estos frameworks.
Utiliza las fuentes oficiales proporcionadas para responder a las preguntas del usuario.

Herramientas disponibles:
- fuentes_urls: realiza búsquedas en las fuentes y devuelve la solución al errores que te preguntan, con explicación de la solución y enlaces a las fuentes oficiales.

Siempre que el usuario pregunte sobre un error específico:
1. Usa la herramienta fuentes_urls.
2. Analiza los resultados.
3. Devuelve una respuesta concreta, concisa y con explicaciones claras.
4. Incluye los enlaces de las fuentes utilizadas.
5. Cuando sea relevante, explica brevemente el "por qué del error", no solo la "solución".
6. Si el contexto no contiene información suficiente para responder, dilo explícitamente en vez de inventar una respuesta.
7. Unicamente estás disponible para responder a preguntas sobre errores de LangChain, LangGraph, RAG, FAISS, Cohere, Streamlit y GitHub oficial. A cualquiier otro pregunta fuera de estos temas, sé explicita en decir: "Lo siento, no puedo ayudarte con eso."

Contexto:
{context}

Pregunta: {question}

Respuesta:"""


def _formatear_contexto(documentos):
    """Concatena los fragmentos recuperados en un solo bloque de texto"""
    return "\n\n---\n\n".join(doc.page_content for doc in documentos)


def cargar_cadena(k=3):
    """
    Carga el índice FAISS ya construido y arma la cadena completa
    (retriever -> prompt -> Claude -> respuesta en texto).

    k: cuántos fragmentos recupera el retriever por consulta (menos = más rápido)
    """
    embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")

    vector_store = FAISS.load_local(
        INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": k})

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=512)

    prompt = ChatPromptTemplate.from_template(PROMPT_SOPHIA)

    cadena = (
        {
            "context": retriever | _formatear_contexto,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return cadena, retriever


def preguntar(cadena, retriever, pregunta):
    """
    Ejecuta la pregunta contra la cadena y devuelve tanto la respuesta
    como las fuentes recuperadas (para mostrar en la UI y en los logs).
    """
    respuesta = cadena.invoke(pregunta)
    fuentes = retriever.invoke(pregunta)
    fuentes_urls = list({doc.metadata.get("source", "desconocida") for doc in fuentes})

    return respuesta, fuentes_urls
