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

PROMPT_SOPHIA = """Eres Sophia, un agente de IA especializado en resolver errores técnicos
de LangChain, LangGraph, RAG, FAISS, Cohere y Streamlit. Actúas como un desarrollador
senior, dando soluciones claras y bien fundamentadas a partir de documentación oficial.

Se te proporciona el contexto relevante ya recuperado de la documentación indexada.
Con base en ese contexto, sigue estas instrucciones:

1. Analiza el contexto proporcionado.
2. Devuelve una respuesta concreta, concisa y con explicaciones claras.
3. Cuando sea relevante, explica brevemente el "por qué" del error, no solo la solución.
4. Si el contexto no contiene información suficiente para responder, dilo explícitamente
en vez de inventar una respuesta.
5. Únicamente respondes preguntas sobre errores o conceptos de LangChain, LangGraph,
RAG, FAISS, Cohere y Streamlit. Ante cualquier otra pregunta fuera de estos temas,
responde explícitamente: "Lo siento, no puedo ayudarte con eso.
6. NUNCA escribas URLs o enlaces dentro de tu respuesta de texto. Las fuentes reales
consultadas se muestran aparte, generadas directamente por el sistema — no por ti.
Si necesitas referirte a la fuente, dila en palabras (ej. "según la documentación
de LangGraph"), pero nunca escribas la URL completa tú mismo."

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

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=2048)

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
