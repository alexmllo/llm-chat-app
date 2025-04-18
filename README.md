# 🧠 LLM Chat Web App with Embeddings & ChromaDB

This project is a microservices-based web app that allows you to scrape websites, convert content to markdown, generate embeddings using OpenAI, store them in ChromaDB, and query them via an LLM API—all connected to a React frontend for easy interaction.

---

## 📦 Services Overview

| Service              | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `scraper-embeddings` | Scrapes website content into markdown, generates embeddings with OpenAI     |
| `chroma-db`          | Vector store using ChromaDB with persistent volume                          |
| `llm`                | Backend API to handle queries via OpenAI or Gemini using ChromaDB data      |
| `frontend`           | React frontend to interact with the LLM-based chatbot interface             |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-user/llm-chat.git
cd llm-chat-app
```

### 2. Setup Environment Variables
Create a .env file at the root of the project with the following content:

```env
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
ANONYMIZED_TELEMETRY=FALSE
```

### 3. Run the App
Make sure Docker is running, then launch everything:

```bash
docker compose up --build
```

This will spin up:
- ChromaDB on `http://localhost:8000`
- Scraper/Embedding API on `http://localhost:8080`
- LLM API on `http://localhost:5050`
- Frontend on `http://localhost:3000`

--

## 📂 Folder Structure

```bash
.
├── LICENSE
├── README.md
├── compose.yml                  # Docker Compose setup for all services
├── embeddings/                 # Scraper and embedding generator service
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── utils/
│       ├── createEmbeddingsDB.py
│       ├── extractWebInfo.py
│       └── scraper.py
├── frontend/                   # Frontend UI to interact with the LLM
│   ├── Dockerfile
│   ├── app.js
│   ├── index.html
│   └── style.css
└── llm/                        # Backend service to query the embeddings with LLMs
    ├── Dockerfile
    ├── app.py
    ├── data/
    │   ├── acronims.json
    │   └── config.json
    ├── requirements.txt
    └── utils/
        └── llm.py
```

## Services
- **Frontend**: A simple UI for entering queries and displaying results.
- **Scraper & Embeddings**: Scrapes web content and converts it into markdown files and OpenAI embeddings stored in a ChromaDB database.
- **LLM Backend**: Handles user queries and retrieves relevant information using OpenAI and Gemini APIs.
- **ChromaDB**: A persistent vector database that stores and serves embeddings.