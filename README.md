# Sinhala + English Local RAG Document QA System

A local-first Retrieval-Augmented Generation (RAG) web application for asking Sinhala or English questions over uploaded PDF, DOCX, and TXT documents. The system extracts document text, normalizes Sinhala/English content, chunks it, indexes it in a local vector database, retrieves relevant passages, and generates grounded answers with source citations.

The project is designed to be completely free to run locally: no paid APIs, no hosted vector database, and no external LLM service.

## Project Overview

This application helps users explore Sinhala, English, and mixed-language documents through natural-language questions. It supports cross-language retrieval and answer generation, so the document language and question language do not need to match.

The answer language follows the user's question language:

- Sinhala document + Sinhala question -> Sinhala answer
- English document + English question -> English answer
- Sinhala document + English question -> English answer
- English document + Sinhala question -> Sinhala answer
- Mixed Sinhala/English document + Sinhala question -> Sinhala answer
- Mixed Sinhala/English document + English question -> English answer

## Features

- Upload and index PDF, DOCX, and TXT documents.
- Extract text with PyMuPDF and `python-docx`.
- Normalize Unicode text while preserving Sinhala characters.
- Chunk document text into 500-token windows with 50-token overlap.
- Generate multilingual embeddings with `paraphrase-multilingual-MiniLM-L12-v2`.
- Store semantic vectors locally in ChromaDB.
- Ask Sinhala or English questions across one or many documents.
- Retrieve the top 5 most relevant chunks for each question.
- Generate grounded answers using a local Ollama-compatible Qwen model.
- Fall back gracefully when the local LLM is unavailable.
- Display source citations, similarity confidence, page metadata, and keyword highlights.
- Track conversation history and retrieval logs.
- Provide an admin dashboard with document, chunk, chat, and retrieval counts.
- Run fully on a local machine using open-source tooling.

## System Architecture

```text
Document Upload
PDF / DOCX / TXT
        |
        v
Text Extraction
PyMuPDF / python-docx / TXT reader
        |
        v
Text Cleaning
Unicode normalization + whitespace cleanup
        |
        v
Chunking
500 tokens + 50 token overlap
        |
        v
Embedding Model
paraphrase-multilingual-MiniLM-L12-v2
        |
        v
Vector Database
ChromaDB persisted locally

User Question
Sinhala or English
        |
        v
Question Language Detection
Sinhala if Sinhala script is present, otherwise English
        |
        v
Question Embedding
MiniLM embedding model
        |
        v
Similarity Search
Top K = 5
        |
        v
Retrieved Source Chunks
        |
        v
Local LLM
Ollama + Qwen3 4B
        |
        v
Grounded Answer + Citations
Answer language follows question language
```

## Technologies Used

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, Vite, TypeScript, Lucide React, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Document Processing | PyMuPDF, python-docx |
| Embeddings | SentenceTransformers, `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector Store | ChromaDB persistent local collection |
| LLM Runtime | Ollama with Qwen3 4B |
| Database | SQLite |
| Testing | pytest, pytest-asyncio |

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama installed locally
- Git

Pull the recommended local model:

```powershell
ollama pull qwen3:4b
```

### Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

The backend API runs at:

```text
http://localhost:8000
```

### Frontend Setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The web app runs at:

```text
http://localhost:5173
```

## Usage

1. Start Ollama and make sure the Qwen model is available.
2. Start the FastAPI backend on port `8000`.
3. Start the React frontend on port `5173`.
4. Upload a Sinhala, English, or mixed-language PDF, DOCX, or TXT file.
5. Select one or more documents from the document panel.
6. Ask a question in Sinhala or English.
7. Review the generated answer, confidence score, and cited source passages.
8. Use the admin panel to inspect document counts, indexed chunks, chat history, and retrieval activity.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/documents/upload` | Upload and index a document |
| `GET` | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{document_id}` | Delete a document and its vectors |
| `POST` | `/api/chat/query` | Ask a question over indexed documents |
| `GET` | `/api/chat/history` | Fetch recent conversations |
| `GET` | `/api/admin/stats` | Fetch dashboard statistics |
| `GET` | `/api/admin/retrieval-logs` | Fetch retrieval logs |

## Project Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- main.py              # FastAPI app and API routes
|   |   |-- rag.py               # Upload, retrieval, answering, deletion flow
|   |   |-- extraction.py        # PDF, DOCX, and TXT extraction
|   |   |-- text_processing.py   # Normalization, language detection, chunking
|   |   |-- embeddings.py        # SentenceTransformer embedding service
|   |   |-- vector_store.py      # ChromaDB persistence and search
|   |   |-- llm.py               # Ollama/Qwen prompt and fallback handling
|   |   |-- models.py            # SQLAlchemy database models
|   |   |-- schemas.py           # Pydantic request/response schemas
|   |   `-- database.py          # SQLite session and initialization
|   |-- tests/
|   |   |-- fixtures/            # Sinhala, English, and mixed sample texts
|   |   `-- test_*.py            # Unit and acceptance tests
|   |-- .env.example
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- main.tsx             # React application
|   |   `-- styles.css           # Responsive app styling
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- tsconfig.json
|   `-- vite.config.ts
|-- data/
|   `-- .gitkeep                 # Runtime storage directory placeholder
|-- docs/
|   `-- screenshots/
|       `-- .gitkeep             # Screenshot placeholder directory
|-- .gitignore
|-- LICENSE
`-- README.md
```

## Example Screenshots

Add screenshots to `docs/screenshots/` after running the app locally.

| Upload and Document Management | Chat and Citations | Admin Dashboard |
| --- | --- | --- |
| `docs/screenshots/upload.png` | `docs/screenshots/chat.png` | `docs/screenshots/admin.png` |

## Testing

Run backend tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Useful checks:

```powershell
python -m compileall app
```

The current test suite covers text normalization, Sinhala/English question-language routing, chunk overlap behavior, LLM fallback language behavior, API schema contracts, and the six required language-direction cases.

## Future Improvements

- Add authentication and role-based access control.
- Add streaming LLM responses.
- Add OCR support for scanned Sinhala PDFs.
- Add reranking for higher retrieval precision.
- Add document-level access permissions.
- Add exportable chat reports with citations.
- Add automated frontend tests with Playwright.
- Add Docker Compose for one-command local startup.
- Add configurable model selection for smaller or larger local LLMs.

## Author

**013th**  
Email: `total13@gmail.com`

## License

This project is licensed under the MIT License.
