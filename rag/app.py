# ==============================================================================
# MANUELITA CHATBOT — RAG (Búsqueda Híbrida + Re-ranking) con Gradio
#
# Objetivo:
# - Servir como asistente oficial de Manuelita.
# - Responder SOLO con la información presente en el contexto recuperado (RAG).
# - Evitar alucinaciones con reglas claras de incertidumbre y rechazos útiles.
#
# Notas:
# - Conserva tu stack: LangChain + Chroma + BM25 + Cross-Encoder + Gemini 2.5 Pro.
# - Asegúrate de tener GOOGLE_API_KEY en variables de entorno (Hugging Face Spaces: "Secrets").
# - Los .md deben estar bajo data/raw/ (usa encabezados '#', '##', '###', '####').
# ==============================================================================

import gradio as gr
import os

# --- LangChain / Infra RAG ---
from langchain.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

print("Starting Manuelita Chatbot (RAG)…")
rag_chain = None
initialization_error = None

try:
    # --------------------------------------------------------------------------
    # 1) API Key (Gemini)
    # --------------------------------------------------------------------------
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "CRITICAL: Missing GOOGLE_API_KEY. Set it in your environment/Secrets."
        )

    # --------------------------------------------------------------------------
    # 2) Carga de la base de conocimiento (Markdown bajo data/raw/)
    #    - Cada .md debe usar encabezados para que el splitter funcione bien.
    # --------------------------------------------------------------------------
    print("Loading Markdown documents from 'data/raw/'…")
    loader = DirectoryLoader(
        path="data/raw/",
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()

    if not docs:
        raise ValueError(
            "No .md files found in 'data/raw/'. Put your knowledge base there."
        )

    headers_to_split_on = [
        ("#", "TituloPrincipal"),
        ("##", "Subtitulo1"),
        ("###", "Subtitulo2"),
        ("####", "Subtitulo3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, strip_headers=False
    )

    splits = []
    for doc in docs:
        chunks = markdown_splitter.split_text(doc.page_content)
        splits.extend(chunks)

    print(
        f"DEBUG: Loaded {len(docs)} docs → produced {len(splits)} semantic chunks."
    )
    if not splits:
        raise ValueError(
            "Markdown splitting yielded no chunks. Check headers in your .md files."
        )

    # --------------------------------------------------------------------------
    # 3) Búsqueda Híbrida (Vectorial + BM25)
    # --------------------------------------------------------------------------
    print("Building hybrid retriever (vector + keyword)…")
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_model)

    # - Semántico
    semantic_retriever = vectorstore.as_retriever(search_kwargs={"k": 7})
    # - Palabras clave (BM25)
    keyword_retriever = BM25Retriever.from_documents(splits)
    keyword_retriever.k = 7

    # - Ensemble con mayor peso al semántico
    ensemble_retriever = EnsembleRetriever(
        retrievers=[semantic_retriever, keyword_retriever], weights=[0.75, 0.25]
    )

    # --------------------------------------------------------------------------
    # 4) Re-ranking (Cross-Encoder) para máxima precisión en el top-N
    # --------------------------------------------------------------------------
    print("Configuring Cross-Encoder re-ranker (top_n=4)…")
    reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
    compressor = CrossEncoderReranker(model=reranker_model, top_n=4)

    reranking_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=ensemble_retriever
    )

    # --------------------------------------------------------------------------
    # 5) Modelo LLM + PROMPT ZERO-SHOT (Anti-Alucinación)
    # --------------------------------------------------------------------------
    print("Initializing Gemini 2.5 Pro (temperature=0.05)…")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro", temperature=0.05, google_api_key=api_key
    )

    # ==========================================================================
    # 🔐 PROMPT PRINCIPAL (Zero-shot, anti-alucinación)
    #    - Adaptado para Manuelita (https://www.manuelita.com/)
    #    - Responde SOLO con el contexto recuperado (RAG).
    #    - Si falta info → explica la limitación y sugiere próximos pasos.
    # ==========================================================================
    final_prompt_template = """
You are the official Manuelita Chatbot.

ROLE & SCOPE
- You answer ONLY using the factual information contained in the provided RAG context.
- You represent Manuelita’s voice: professional, clear, service-oriented, and consistent with official materials.
- If the user asks for information outside the available context, clearly say you don’t have enough information and avoid guessing.

STRICT ANTI-HALLUCINATION RULES
1) Do NOT invent facts, figures, dates, certifications, products, or policies.
2) If the context does not contain an answer, say:
   "I have reviewed the available information but I don’t find a direct answer in the current knowledge base."
   Offer a helpful next step (e.g., suggest searching the official site section, or asking a narrower question).
3) If a question requires sensitive or private data not present in the context, refuse politely and explain the privacy constraint.
4) Prefer concise, factual answers. Use bullet points for lists. Keep an approachable tone.

CITATIONS & TRANSPARENCY
- When you state a consequential fact (numbers, product specs, certifications, addresses, contact lines, dates), tie it to the context by briefly naming the section or file if present (e.g., "Fuente: Sostenibilidad.md > Energías renovables").
- If multiple fragments support an answer, synthesize them. Do not repeat the raw chunks.

DISAMBIGUATION
- If the user’s question is ambiguous, briefly ask 1 targeted clarifying question.
- Otherwise, answer directly.

LANGUAGE
- Respond in Spanish for end users.
- Use neutral, professional Spanish (LatAm), plain and accessible.

FORMAT
- Start with a one-sentence answer or summary, then provide details.
- Use short paragraphs (2–4 lines) and bullets for readability.
- Avoid tables for long sentences; only use tables for compact data (palabras clave, cifras, empaques, referencias breves).

NOW USE THE RAG CONTEXT BELOW TO ANSWER.
-----------
[CONTEXT START]
{context}
[CONTEXT END]
-----------
PREGUNTA DEL USUARIO: {input}

ENTREGA:
Responde en español, siguiendo las reglas anteriores. Si falta información en el contexto, dilo explícitamente y no especules.
"""
    final_prompt = PromptTemplate.from_template(final_prompt_template)

    # --------------------------------------------------------------------------
    # 6) Cadena RAG final (Retriever + LLM + Prompt)
    # --------------------------------------------------------------------------
    question_answer_chain = create_stuff_documents_chain(llm, final_prompt)
    rag_chain = create_retrieval_chain(reranking_retriever, question_answer_chain)
    print("Manuelita Chatbot is ready ✅")

except Exception as e:
    initialization_error = e
    print(f"CRITICAL init error: {e}")

# ------------------------------------------------------------------------------
# 7) Función de respuesta (Gradio)
# ------------------------------------------------------------------------------
def get_response(message, history):
    """
    Recibe el mensaje del usuario y retorna la respuesta generada por la cadena RAG.
    - Si la app no inicializó correctamente, devolvemos el error.
    - Si la cadena no está disponible, lo indicamos.
    - Registramos logs simples en consola para depuración.
    """
    if initialization_error:
        return f"Error de inicialización: {initialization_error}"
    if not rag_chain:
        return "Error: La cadena RAG no está disponible."

    try:
        print(f"[USER] {message}")
        response = rag_chain.invoke({"input": message})
        # LangChain 'create_retrieval_chain' devuelve un dict con la clave "answer"
        return response["answer"]
    except Exception as e:
        print(f"[ERROR] Procesando pregunta: {e}")
        return f"Lo siento, ocurrió un error al procesar tu pregunta. Detalle técnico: {e}"

# ------------------------------------------------------------------------------
# 8) Interfaz Gradio
# ------------------------------------------------------------------------------
demo = gr.ChatInterface(
    fn=get_response,
    title="Manuelita — Asistente Oficial (RAG)",
    description=(
        "Haz tu consulta sobre Manuelita. El asistente usa una base de conocimiento "
        "local (archivos .md en data/raw/) y responde SOLO con información recuperada del contexto."
    ),
    examples=[
        # Ejemplos enfocados a Manuelita. Ajusta según tus .md reales en data/raw/
        ["¿Qué productos de energías renovables ofrece Manuelita y qué beneficios ambientales reportan?"],
        ["¿Cuáles son las presentaciones disponibles para las uvas y en qué temporadas se exportan?"],
        ["¿Cómo funciona la Línea Ética y qué canales oficiales existen para reportar irregularidades?"],
        ["¿Qué subproductos ofrecen derivados de la caña o de la palma y para qué industrias se usan?"],
        ["Dame los datos de contacto corporativo disponibles en la base de conocimiento."],
    ],
    theme="soft",
    chatbot=gr.Chatbot(height=500),
)

# ------------------------------------------------------------------------------
# 9) Lanzamiento
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # share=True no es necesario en Spaces. Úsalo localmente si deseas URL pública.
    demo.launch()
