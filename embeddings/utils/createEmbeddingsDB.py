import os
import chromadb
import markdown
import re
import openai
from bs4 import BeautifulSoup
# from docling.document_converter import DocumentConverter

# Configuración
DATA_FOLDER = "../markdowns"
CHROMA_DB_FOLDER = "chromadb_store_en"
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_CALLS = 1000000
MAX_TOKENS = 16000  # Límite seguro para evitar el error de 8192 tokens
call_count = 0
BASE_URL = ""

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Set the OPENAI_API_KEY environment variable.")

# Inicializar ChromaDB
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

collection = chroma_client.get_or_create_collection(name="memory")

# Configurar cliente OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def remove_empty_dirs(path):
    """Elimina recursivamente las carpetas vacías."""
    for root, dirs, _ in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):  # si está vacía
                try:
                    os.rmdir(dir_path)
                    print(f"🗑️ Removed empty folder: {dir_path}")
                except Exception as e:
                    print(f"❌ Error deleting folder {dir_path}: {e}")

# Función para limpiar HTML
def clean_html(text):
    return BeautifulSoup(text, "html.parser").get_text()


# Función para contar tokens con OpenAI tokenizer
def count_tokens(text):
    return len(client.tokenize(model=OPENAI_MODEL, input=[text]).data[0].tokens)


# Función para dividir texto en fragmentos de tamaño seguro
def split_large_text(text, max_tokens=MAX_TOKENS):
    if len(text) <= max_tokens:
        return [text]
    mid = len(text) // 2
    left_part = split_large_text(text[:mid], max_tokens)
    right_part = split_large_text(text[mid:], max_tokens)
    return left_part + right_part


# Función para obtener embeddings de OpenAI con manejo de errores
def get_openai_embedding(text):
    global call_count
    if call_count >= MAX_CALLS:
        raise RuntimeError("Límite de llamadas a OpenAI alcanzado")

    try:
        text_chunks = split_large_text(text)
        embeddings = []

        for chunk in text_chunks:
            response = client.embeddings.create(
                input=[chunk],
                model=OPENAI_MODEL
            )
            call_count += 1
            embeddings.append(response.data[0].embedding)

        return embeddings
    except openai.BadRequestError as e:
        print(f"Error en OpenAI API: {e}")
        return None
    

def get_openai_embedding_pdfs(texts):
    global call_count
    if call_count >= MAX_CALLS:
        raise RuntimeError("Límite de llamadas a OpenAI alcanzado")

    if isinstance(texts, str):
        texts = [texts]

    all_embeddings = []

    try:
        for text in texts:
            text_chunks = split_large_text(text)

            # Para cada chunk del texto largo, obtén embeddings y combínalos (ej. promedio)
            chunk_embeddings = []
            for chunk in text_chunks:
                response = client.embeddings.create(
                    input=[chunk],
                    model=OPENAI_MODEL
                )
                call_count += 1
                chunk_embeddings.append(response.data[0].embedding)

            # Si el texto original se partió en varios chunks, combínalos en uno solo (media)
            if len(chunk_embeddings) > 1:
                import numpy as np
                avg_embedding = list(np.mean(chunk_embeddings, axis=0))
                all_embeddings.append(avg_embedding)
            else:
                all_embeddings.append(chunk_embeddings[0])

        return all_embeddings

    except openai.BadRequestError as e:
        print(f"Error en OpenAI API: {e}")
        return None
    

# Función para dividir el texto en frases
def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
   # sentences = re.split('r'(?<=[.!?])\s+', text)
    #sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [s.strip() for s in sentences if s.strip()]


# Procesar archivos Markdown en todas las subcarpetas
def process_markdown_file(root, filename):
    print("processing file: "+ filename)
    filepath = os.path.join(root, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Convertir Markdown a texto limpio
    text = clean_html(markdown.markdown(content))

    # Dividir el texto en frases
    sentences = split_into_sentences(text)

    # Generar embeddings con OpenAI y guardarlos en ChromaDB
    relative_path = os.path.relpath(filepath, DATA_FOLDER)
    for idx, sentence in enumerate(sentences):
        embeddings = get_openai_embedding(sentence)
        if embeddings:
            for part_idx, embedding in enumerate(embeddings):
                sentence_id = f"{relative_path}_sentence{idx}_part{part_idx}"
                existing = collection.get(ids=[sentence_id])
                if not existing["ids"]:  # si el ID no existe, lo añadimos
                    collection.add(
                        ids=[sentence_id],
                        embeddings=[embedding],
                        metadatas=[{
                            "filename": relative_path,
                            "sentence": sentence,
                            "sentence_index": idx
                        }]
                    )

    # Eliminar el archivo después de procesarlo
    try:
        os.remove(filepath)
        print(f"Deleted file: {filename}")
    except Exception as e:
        print(f"Error deleting file {filename}: {e}")


# def process_pdf_file(root, filename):
#     print("processing PDF file: " + filename)
#     filepath = os.path.join(root, filename)

#     try:
#         # Convertir PDF a Markdown usando Docling
#         converter = DocumentConverter()
#         result = converter.convert(filepath)
#         markdown_text = result.document.export_to_markdown()

#         # Limpiar HTML generado desde el Markdown
#         text = clean_html(markdown.markdown(markdown_text))

#         # Dividir en frases
#         sentences = split_into_sentences(text)

#         # Generar embeddings con OpenAI y guardarlos en ChromaDB
#         relative_path = os.path.relpath(filepath, DATA_FOLDER)

#         embeddings = get_openai_embedding_pdfs(sentences)

#         if embeddings:
#             for idx, (sentence, embedding) in enumerate(zip(sentences, embeddings)):
#                 sentence_id = f"{relative_path}_sentence{idx}_part0"
#                 existing = collection.get(ids=[sentence_id])
#                 if not existing["ids"]:  # si el ID no existe, lo añadimos
#                     collection.add(
#                         ids=[sentence_id],
#                         embeddings=[embedding],
#                         metadatas=[{
#                             "filename": relative_path,
#                             "sentence": sentence,
#                             "sentence_index": idx
#                         }]
#                     )

#         # Eliminar el archivo después de procesarlo
#         os.remove(filepath)
#         print(f"Deleted file: {filename}")

    except Exception as e:
        print(f"Error processing PDF {filename}: {e}")


def process_folder_files(base_folder):
    DATA_FOLDER = base_folder
    for root, _, files in os.walk(DATA_FOLDER):
        for filename in files:
            if(filename.endswith(".pdf")):
                continue
                process_pdf_file(root, filename)
            elif filename.endswith(".md"):
                process_markdown_file(root, filename)
    remove_empty_dirs(DATA_FOLDER)