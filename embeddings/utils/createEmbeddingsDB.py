from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import threading
import nltk
import tiktoken
import chromadb
import markdown
import re
import openai
from bs4 import BeautifulSoup
from docling.document_converter import DocumentConverter

from nltk.tokenize import sent_tokenize

lock = threading.Lock()

# Configuración
DATA_FOLDER = "markdown"
# CHROMA_DB_FOLDER = "chromadb_store_en"
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_CHARS = 16000
call_count = 0
BASE_URL = ""

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Set the OPENAI_API_KEY environment variable.")

# Inicializar ChromaDB
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

collection = chroma_client.get_or_create_collection(name="memory")

nltk.download('punkt_tab')
encoding = tiktoken.encoding_for_model("text-embedding-ada-002")

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
def split_large_text(text, max_tokens=MAX_CHARS):
    if len(text) <= max_tokens:
        return [text]
    mid = len(text) // 2
    left_part = split_large_text(text[:mid], max_tokens)
    right_part = split_large_text(text[mid:], max_tokens)
    return left_part + right_part


# Función para obtener embeddings de OpenAI con manejo de errores
def get_openai_embedding(text):
    global call_count
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
    max_tokens = 1000
    # Patrón para detectar títulos con cierto formato
    sections = re.split(r'\n{4,}', text)  # separa por líneas vacías dobles
    chunks = []

    for section in sections:
        sentences = sent_tokenize(section)
        current_chunk = []

        current_length = 0

        for sentence in sentences:
            sentence_tokens = len(encoding.encode(sentence))
            # Si pasaría el límite, cierra el chunk actual y empieza uno nuevo
            if current_length + sentence_tokens > max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_length += sentence_tokens

        # Añade el último chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

    return chunks


#def split_into_sentences(text):
#    sentences = re.split(r'(?<=[.!?])\s+', text)
#    return [s.strip() for s in sentences if s.strip()]


# Procesar archivos Markdown en todas las subcarpetas
def process_markdown_file(root, filename, url):
    print("processing file: "+ filename)
    filepath = os.path.join(root, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Convertir Markdown a texto limpio
        text = clean_html(markdown.markdown(content))

        # Dividir el texto en frases
        sentences = split_into_sentences(text)

        # Generar embeddings con OpenAI y guardarlos en ChromaDB
        relative_path = os.path.relpath(filepath, DATA_FOLDER)

        file_url = get_url(filepath, root, url)
        for idx, sentence in enumerate(sentences):
            embeddings = get_openai_embedding(sentence)
            if embeddings:
                for part_idx, embedding in enumerate(embeddings):
                    sentence_id = f"{relative_path}_sentence{idx}_part{part_idx}"
                    with lock:
                        existing = collection.get(ids=[sentence_id])
                        if not existing["ids"]:  # si el ID no existe, lo añadimos
                            collection.add(
                                ids=[sentence_id],
                                embeddings=[embedding],
                                metadatas=[{
                                    "filename": file_url,
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

    except Exception as e:
        print(f"Error processing file {filename}: {e}")


def get_url(filepath, root, url):
    url = filepath.replace(root, url).replace("\\","/").replace("//","/").replace(":/","://").replace("_index.md","")
    if(url.endswith(".md")):
        url = url[:-3]
    return url


def process_pdf_file(root, filename, url):
    print("processing PDF file: " + filename)
    filepath = os.path.join(root, filename)
    file_url = get_url(filepath, root, url)

    try:
        # Convertir PDF a Markdown usando Docling
        converter = DocumentConverter()
        result = converter.convert(filepath)
        markdown_text = result.document.export_to_markdown()

        # Limpiar HTML generado desde el Markdown
        text = clean_html(markdown.markdown(markdown_text))

        # Dividir en frases
        sentences = split_into_sentences(text)

        # Generar embeddings con OpenAI y guardarlos en ChromaDB
        relative_path = os.path.relpath(filepath, DATA_FOLDER)

        embeddings = get_openai_embedding_pdfs(sentences)

        if embeddings:
            for idx, (sentence, embedding) in enumerate(zip(sentences, embeddings)):
                sentence_id = f"{relative_path}_sentence{idx}_part0"
                with lock:
                    existing = collection.get(ids=[sentence_id])
                    if not existing["ids"]:  # si el ID no existe, lo añadimos
                        collection.add(
                            ids=[sentence_id],
                            embeddings=[embedding],
                            metadatas=[{
                                "filename": file_url,
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

    except Exception as e:
        print(f"Error processing PDF {filename}: {e}")


def process_file(root, filename, url, task_id, progress_dict):
    this_task = f"Creating embeddings for {filename}..."
    with lock:
        progress_dict[task_id]['text'] += "\n" + this_task

    if filename.endswith(".pdf"):
        process_pdf_file(root, filename, url)
    elif filename.endswith(".md"):
        process_markdown_file(root, filename, url)

    with lock:
        progress_dict[task_id]['text'] = progress_dict[task_id]['text'].replace(
            this_task,
            f"✅ Created embeddings for {filename}"
        )


def process_folder_files(url, base_folder, task_id, progress_dict):
    DATA_FOLDER = base_folder
    futures = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        for root, _, files in os.walk(DATA_FOLDER):
            for filename in files:
                if filename.endswith(".pdf") or filename.endswith(".md"):
                    futures.append(
                        executor.submit(process_file, root, filename, url, task_id, progress_dict)
                    )

        for future in as_completed(futures):
            future.result()  # raise any exceptions

    remove_empty_dirs(DATA_FOLDER)