import os
import chromadb
import openai
import json
from google import genai
import re

# Configuration paths
CONFIG_FILE = "data/config.json"

chat_history = []

# Load configurations
with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

PROMPT_IMPROVEMENT = config["prompt_improvement"]
LLM_PROMPT_TEMPLATE = config["llm_prompt_template"]

# CHROMA_DB_FOLDER = "chromadb_store_en"
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MAX_CALLS = 100000
MAX_TOKENS = 16000
call_count = 0

MAX_CHAT_HISTORY =  config["max_chat_history"]
if MAX_CHAT_HISTORY is None:
    MAX_CHAT_HISTORY = 6

if not OPENAI_API_KEY or not GEMINI_API_KEY:
    raise ValueError("Missing API keys. Check your environment variables.")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

collection = chroma_client.get_or_create_collection(name="memory")

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# Load dictionary.json
with open('data/dictionary.json', 'r', encoding='utf-8') as f:
    dictionary = json.load(f)


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

def call_openai(prompt: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def extract_idx_from_id(sentence_id):
    # Extrae el índice numérico de algo como 'ruta/sentence23_part0'
    match = re.search(r'_sentence(\d+)_part\d+', sentence_id)
    return int(match.group(1)) if match else None

def get_embedding_results_info(query_embedding, results, join_x_sentences):

    results = collection.query(query_embeddings=query_embedding, n_results=results)

    all_ids = []

    info =""
    for current_id in results['ids'][0]:
        current_neighbors=[]
        idx = extract_idx_from_id(current_id)
        if idx is None:
            continue
        # Genera los IDs de la frase actual y las +/-2 vecinas
        base_path = current_id.split("_sentence")[0]
        for offset in range(-join_x_sentences, join_x_sentences + 1):
            neighbor_idx = idx + offset
            if neighbor_idx < 0:
                continue
            neighbor_id = f"{base_path}_sentence{neighbor_idx}_part0"
            current_neighbors.append(neighbor_id)
            #all_ids.append(neighbor_id)

        # Elimina duplicados preservando el orden
        unique_ids = list(OrderedDict.fromkeys(current_neighbors))
        if len(unique_ids) == 0:
            continue
        neighbors = collection.get(ids=unique_ids)
        info += "".join([f"- {meta['sentence']}\n" for meta in neighbors["metadatas"]]) + "\n\n\n\n\n"

    if info == "":
        return None

    return info

def improve_user_prompt(user_prompt, chat_history_local):
    # Asegurarse de que solo se usan los últimos 5 mensajes
    last_turns = chat_history_local[-8:]
    formatted_history = ""
    for turn in last_turns:
        formatted_history += f"{turn['role'].capitalize()}: {turn['content']}\n"

    # Extraer términos útiles del diccionario
    palabras = re.split(r'[,\s.!?¿¡;:\(\)\[\]\{\}]+', user_prompt)
    contexto_items = []
    for palabra in palabras:
        if palabra in dictionary:
            entry = dictionary[palabra]
            details = [f"**{palabra}**"]
            if 'es' in entry:
                details.append(f"es: {entry['es']}")
            if 'en' in entry:
                details.append(f"en: {entry['en']}")
            if 'description' in entry:
                details.append(f"desc: {entry['description']}")
            if 'type' in entry:
                details.append(f"type: {entry['type']}")
            contexto_items.append(" | ".join(details))

    contexto = "\n".join(contexto_items)

    # Obtener embeddings para esta consulta
    query_embedding = get_openai_embedding(user_prompt)

    info = get_embedding_results_info(query_embedding, 14, 1)

    if info is None:
        return None
    # Construir el nuevo prompt con historial
    full_prompt = PROMPT_IMPROVEMENT.format(
        user_query=user_prompt,
        chat_history=formatted_history,
        dictionary=contexto,
        current_embeddings=info
    )

    improved_prompt = call_openai(full_prompt)
    return improved_prompt

def extract_response(full_response, prompt_marker):
    return full_response.split(prompt_marker)[-1].strip() if prompt_marker in full_response else full_response.strip()

def handle_query(query: str, chat_history: list):

    # Mejorar la consulta con historial
    improved_query = improve_user_prompt(query, chat_history)

    if improved_query is None :
        print("No relevant info found.")
        return "No relevant information found."

    # Guardar prompt mejorado en historial antes de la respuesta
    query_embedding = get_openai_embedding(improved_query)
    if not query_embedding:
        return "Error generating embedding for query."

    info = get_embedding_results_info(query_embedding, 15,1)

    if info is None:
        print("No relevant info found.")
        return "No relevant information found."

    final_prompt = LLM_PROMPT_TEMPLATE.format(user_query=query, improved_query=improved_query, info=info)
    response = call_openai(final_prompt)

    # Añadir consulta al historial
    chat_history.append({"role": "user", "content": improved_query})

    # Guardar respuesta también en el historial
    chat_history.append({"role": "assistant", "content": response})

    while(len(chat_history) > MAX_CHAT_HISTORY):
        chat_history.pop(0)

    print("\nAnswer from LLM:\n")
    print(response)
    return response