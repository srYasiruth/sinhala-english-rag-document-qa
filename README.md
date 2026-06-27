# Sinhala + English Local RAG Document QA System

A local-first Retrieval-Augmented Generation (RAG) web application for asking Sinhala or English questions over uploaded PDF, DOCX, and TXT documents. The system extracts document text, normalizes Sinhala/English content, chunks it, indexes it in a local vector database, retrieves relevant passages, and generates grounded answers with source citations.

The project is designed to be completely free to run locally: no paid APIs, no hosted vector database, and no external LLM service.

## Project Overview

This application helps users explore Sinhala, English, and mixed-language documents through natural-language questions. It supports cross-language retrieval and answer generation, so the document language and question language do not need to match.

The answer language follows the user's question language by default. If the user explicitly asks for English or Sinhala output, that requested language is used:

- Sinhala document + Sinhala question -> Sinhala answer
- English document + English question -> English answer
- Sinhala document + English question -> English answer
- English document + Sinhala question -> Sinhala answer

Retrieved context and citations still come from the uploaded documents, and answers are generated only from that context.

## Features

- Upload and index PDF, DOCX, and TXT documents.
- Extract text with PyMuPDF and `python-docx`.
- Normalize Unicode text while preserving Sinhala characters.
- Chunk document text with Sinhala-safe paragraph-aware chunking.
- Generate multilingual embeddings with `intfloat/multilingual-e5-base`.
- Store semantic vectors locally in ChromaDB.
- Ask Sinhala or English questions across one or many documents.
- Retrieve with original and translated local query variants, then merge and deduplicate results.
- Apply lightweight keyword boosting for exact Sinhala/English terms, numbers, names, and section labels.
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
Paragraph-aware chunks, 700 tokens + 120 overlap
        |
        v
Embedding Model
intfloat/multilingual-e5-base
        |
        v
Vector Database
ChromaDB persisted locally

User Question
Sinhala or English
        |
        v
Question Language Detection
Stored for chat metadata/history
        |
        v
Question Embedding
E5 query embedding
        |
        v
Cross-Lingual Query Expansion
Original query + local Ollama translation when needed
        |
        v
Multi-Query Retrieval
Vector search + lightweight keyword boost
        |
        v
Merge + Deduplicate + Rank
Candidate K = 15, final Top K = 5
        |
        v
Retrieved Source Chunks
        |
        v
Answer Language Selection
Majority language among top retrieved chunks
        |
        v
Local LLM
Ollama + Qwen3 4B
        |
        v
Grounded Answer + Citations
Answer language follows question or explicit user request
```

## Technologies Used

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, Vite, TypeScript, Lucide React, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Document Processing | PyMuPDF, python-docx |
| Embeddings | SentenceTransformers, `intfloat/multilingual-e5-base`; MiniLM can be used as a lightweight fallback |
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

### One-Click Windows Startup

For the easiest local startup on Windows, use the launcher in the project root:

```powershell
.\start_app.bat
```

You can also run the PowerShell launcher directly:

```powershell
.\start_app.ps1
```

The launcher will:

- Check that Ollama, Python, and npm are available.
- Start the Ollama server if it is not already running.
- Check whether the `qwen3:4b` model is available and pull it if missing.
- Create `backend/.env` from `backend/.env.example` if needed.
- Create the backend virtual environment if needed.
- Install backend dependencies if the virtual environment is missing.
- Install frontend dependencies if `node_modules/` is missing.
- Start the FastAPI backend in a visible log window.
- Start the Vite frontend in a visible log window.
- Open the app automatically at `http://localhost:5173`.
- Write runtime logs to the local `logs/` folder.

Keep the Ollama, backend, and frontend windows open while using the app. Close those windows when you want to stop the system.

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

### Beginner Startup

1. Double-click `start_app.bat` or run `.\start_app.bat` from PowerShell.
2. Wait for the launcher to open the browser at `http://localhost:5173`.
3. Upload a Sinhala, English, or mixed-language PDF, DOCX, or TXT file.
4. Select one or more documents from the document panel.
5. Ask a question in Sinhala or English.
6. Review the generated answer, confidence score, and cited source passages.
7. Use the admin panel to inspect document counts, indexed chunks, chat history, and retrieval activity.

### Manual Startup

Use these steps if you prefer to run each service yourself:

1. Start Ollama and make sure the Qwen model is available.
2. Start the FastAPI backend on port `8000`.
3. Start the React frontend on port `5173`.
4. Open `http://localhost:5173` in your browser.

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
|-- README.md
|-- start_app.bat                # Windows double-click launcher
`-- start_app.ps1                # Windows PowerShell startup script
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

The current test suite covers text normalization, paragraph-aware chunking, E5 query/passage prefixes, cross-lingual query expansion, retrieved-context answer-language routing, LLM fallback language behavior, API schema contracts, and the required document/question language-direction cases.

## Troubleshooting

### Large documents or Sinhala questions time out

Large retrieved passages and Sinhala generation can take longer on local CPU/GPU resources. The backend keeps the existing answer style but limits only the context sent to Ollama and uses a longer timeout:

```text
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_KEEP_ALIVE="10m"
MAX_CONTEXT_CHARS=12000
MAX_SOURCE_CHARS=3000
```

If you already have `backend/.env`, add these values manually or recreate it from `backend/.env.example`. If answers still time out, increase `OLLAMA_TIMEOUT_SECONDS`.

### Reindex after embedding model changes

The default embedding model is `intfloat/multilingual-e5-base`. The first upload can take a long time because the model is downloaded and cached locally from Hugging Face. After the download finishes, later indexing runs are faster.

You can pre-cache the model before starting the app:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"
```

The vector database uses a separate Chroma collection for each embedding model, because E5 vectors have 768 dimensions while MiniLM vectors have 384 dimensions. If you previously indexed documents with MiniLM, delete and re-upload those documents so SQLite metadata and Chroma vectors stay aligned.

If you need the older lightweight model for faster indexing, set:

```text
EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

Then restart the backend and re-upload documents again after changing the model.

### Debug retrieval

The chat API accepts `debug: true` in `POST /api/chat/query`. Debug responses include detected question language, target document languages, query variants, translated queries, candidate chunks, final chunks, and final answer language. The current UI ignores this field, but it is useful when checking whether a failure comes from translation, embedding retrieval, keyword matching, chunking, or the final LLM answer.

### Backend fails after changing `.env`

If the backend does not start after editing `.env`, compare it with `backend/.env.example` and remove unsupported keys. The current backend ignores unknown keys, but keeping `.env` aligned with `.env.example` makes troubleshooting easier.

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

**LDCSR Yasiruth**
Email: `sahanryasiruth01@gmail.com`

## License

This project is licensed under the MIT License.
