import os
import chromadb
import openai
import json
from google import genai
import re

# Configuration paths
CONFIG_FILE = "data/config.json"

print(os.getcwd())

# Load configurations
with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

PROMPT_IMPROVEMENT = config["prompt_improvement"]
LLM_PROMPT_TEMPLATE = config["llm_prompt_template"]

CHROMA_DB_FOLDER = "chromadb_store_en"
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MAX_CALLS = 100000
MAX_TOKENS = 16000
call_count = 0

if not OPENAI_API_KEY or not GEMINI_API_KEY:
    raise ValueError("Missing API keys. Check your environment variables.")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

collection = chroma_client.get_or_create_collection(name="memory")

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# Cargar el diccionario desde el JSON
with open('data/acronims.json', 'r', encoding='utf-8') as f:
    acronimos_fib = json.load(f)


def split_large_text(text, max_tokens=MAX_TOKENS):
    if len(text) <= max_tokens:
        return [text]
    mid = len(text) // 2
    return split_large_text(text[:mid], max_tokens) + split_large_text(text[mid:], max_tokens)

def get_openai_embedding(text):
    global call_count
    if call_count >= MAX_CALLS:
        raise RuntimeError("OpenAI call limit reached.")

    chunks = split_large_text(text)
    embeddings = []

    for chunk in chunks:
        response = openai_client.embeddings.create(input=[chunk], model=OPENAI_MODEL)
        call_count += 1
        embeddings.append(response.data[0].embedding)

    return embeddings[0]

def improve_user_prompt(user_prompt):
    # Obtener contexto relevante
    # Split robusto usando expresiones regulares
    palabras = re.split(r'[,\s.!?¿¡;:\(\)\[\]\{\}]+', user_prompt)

    # Obtener contexto relevante
    contexto = ", ".join(f"{k}={acronimos_fib[k]}" for k in palabras if k in acronimos_fib)

    query_embedding = get_openai_embedding(user_prompt)

    results = collection.query(query_embeddings=query_embedding, n_results=6)

    info = "".join([f"- {meta['sentence']}\n" for meta in results["metadatas"][0]])

    prompt = PROMPT_IMPROVEMENT.format(user_query=user_prompt, dictionary= contexto, current_embeddings=info)

    response = genai_client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    return response.text

def extract_response(full_response, prompt_marker):
    return full_response.split(prompt_marker)[-1].strip() if prompt_marker in full_response else full_response.strip()

# Interactive search
def handle_query(query:str):

    # Improve user query using LLM
    improved_query = improve_user_prompt(query)

    # Generate query embedding
    query_embedding = get_openai_embedding(improved_query)
    if not query_embedding:
        print("Error generating embedding for query.")
        return

    # Query ChromaDB
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=6
    )

    if not results["ids"] or not results["ids"][0]:
        print("No relevant info found.")
        return

    # Build context information
    info = ""
    for idx, metadata in enumerate(results["metadatas"][0]):
        sentence = results["metadatas"][0][idx]['sentence']
        info += f"- {sentence}\n"

    # Build LLM prompt
    prompt = LLM_PROMPT_TEMPLATE.format(user_query=improved_query, info=info)
    prompt_marker = "Short answer in English:"

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )

    clean_response = extract_response(response.text, prompt_marker)
    print("\nAnswer from LLM:\n")
    print(response.text)
    return response.text