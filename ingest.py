"""
Ingesta de documentos para Sophia.

Este script se ejecuta UNA sola vez (o cada vez que cambies la lista de URLs):
1. Descarga y extrae el texto de cada URL en urls.py
2. Divide el texto en fragmentos manejables
3. Genera embeddings con Cohere
4. Guarda el índice FAISS en disco, para no repetir este proceso en cada consulta

Uso:
    python ingest.py
"""

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_cohere import CohereEmbeddings
from langchain_community.vectorstores import FAISS

from urls import URLS

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "faiss_index_sophia")


def cargar_documentos():
    """Descarga y extrae el texto de cada URL definida en urls.py"""
    print(f"Cargando {len(URLS)} URLs...")
    loader = WebBaseLoader(URLS)
    documentos = loader.load()
    print(f"✅ {len(documentos)} documentos cargados")
    return documentos


def dividir_en_fragmentos(documentos):
    """Divide los documentos en fragmentos manejables para el embedding"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    fragmentos = splitter.split_documents(documentos)
    print(f"✅ {len(fragmentos)} fragmentos generados")
    return fragmentos


import time

def construir_indice(fragmentos, tamano_lote=80, pausa_segundos=65):
    """
    Genera embeddings con Cohere y construye el índice FAISS,
    procesando en lotes para respetar los límites de la cuenta trial
    (40 llamadas/min y 100,000 tokens/min).
    """
    embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")

    total_lotes = (len(fragmentos) + tamano_lote - 1) // tamano_lote
    vector_store = None

    for i in range(0, len(fragmentos), tamano_lote):
        lote = fragmentos[i : i + tamano_lote]
        numero_lote = i // tamano_lote + 1
        print(f"Procesando lote {numero_lote}/{total_lotes} ({len(lote)} fragmentos)...")

        if vector_store is None:
            vector_store = FAISS.from_documents(documents=lote, embedding=embeddings)
        else:
            vector_store.add_documents(lote)

        es_ultimo_lote = (i + tamano_lote) >= len(fragmentos)
        if not es_ultimo_lote:
            print(f"  Pausando {pausa_segundos}s para respetar el límite de la cuenta trial...")
            time.sleep(pausa_segundos)

    vector_store.save_local(INDEX_PATH)
    print(f"✅ Índice guardado en: {INDEX_PATH}")

if __name__ == "__main__":
    documentos = cargar_documentos()
    fragmentos = dividir_en_fragmentos(documentos)
    construir_indice(fragmentos)
    print("\n🎉 Ingesta completa. Ya puedes correr la app con: streamlit run app.py")
