import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  FileText,
  History,
  Loader2,
  MessageSquare,
  Search,
  Send,
  Trash2,
  Upload
} from "lucide-react";
import "./styles.css";

type DocumentItem = {
  id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  language_mix: string;
  chunk_count: number;
  created_at: string;
};

type Source = {
  chunk_id: string;
  document_id: number | null;
  filename: string;
  page_number: number | null;
  text: string;
  score: number;
  highlights: string[];
};

type QueryResponse = {
  question: string;
  question_language: string;
  answer: string;
  confidence: number;
  sources: Source[];
};

type Conversation = {
  id: number;
  question: string;
  answer: string;
  question_language: string;
  confidence: number;
  created_at: string;
};

type Stats = {
  documents: number;
  chunks: number;
  conversations: number;
  retrieval_logs: number;
};

const API = "";

async function jsonFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<Conversation[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const selectedCount = selectedIds.length || documents.length;

  async function refresh() {
    const [docs, chatHistory, adminStats] = await Promise.all([
      jsonFetch<DocumentItem[]>(`${API}/api/documents`),
      jsonFetch<Conversation[]>(`${API}/api/chat/history`),
      jsonFetch<Stats>(`${API}/api/admin/stats`)
    ]);
    setDocuments(docs);
    setHistory(chatHistory);
    setStats(adminStats);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  const languageLabel = useMemo(() => {
    if (!answer) return "Waiting";
    return answer.question_language === "si" ? "Sinhala" : "English";
  }, [answer]);

  async function uploadFile(file: File) {
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      await jsonFetch<DocumentItem>(`${API}/api/documents/upload`, {
        method: "POST",
        body: formData
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function deleteDocument(id: number) {
    setError("");
    await jsonFetch(`${API}/api/documents/${id}`, { method: "DELETE" });
    setSelectedIds((current) => current.filter((item) => item !== id));
    await refresh();
  }

  async function askQuestion() {
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    try {
      const response = await jsonFetch<QueryResponse>(`${API}/api/chat/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          document_ids: selectedIds.length ? selectedIds : null,
          summarize: false
        })
      });
      setAnswer(response);
      setQuestion("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleDocument(id: number) {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    );
  }

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <h1>Sinhala + English Local RAG</h1>
          <p>{selectedCount} document scope - answers follow the question language</p>
        </div>
        <label className="upload-button" title="Upload PDF, DOCX, or TXT">
          {uploading ? <Loader2 className="spin" size={18} /> : <Upload size={18} />}
          <span>{uploading ? "Indexing" : "Upload"}</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadFile(file);
              event.currentTarget.value = "";
            }}
          />
        </label>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="workspace">
        <aside className="panel document-panel">
          <div className="panel-title">
            <FileText size={18} />
            <h2>Documents</h2>
          </div>
          <div className="document-list">
            {documents.length === 0 && <p className="empty">Upload Sinhala, English, or mixed documents.</p>}
            {documents.map((doc) => (
              <article
                key={doc.id}
                className={`doc-row ${selectedIds.includes(doc.id) ? "selected" : ""}`}
                onClick={() => toggleDocument(doc.id)}
              >
                <div>
                  <strong>{doc.original_filename}</strong>
                  <span>
                    {doc.file_type.toUpperCase()} - {doc.language_mix} - {doc.chunk_count} chunks
                  </span>
                </div>
                <button
                  title="Delete document"
                  onClick={(event) => {
                    event.stopPropagation();
                    deleteDocument(doc.id).catch((err) => setError(err.message));
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </article>
            ))}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="question-box">
            <MessageSquare size={20} />
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={"\u0dc3\u0dd2\u0d82\u0dc4\u0dbd\u0dd9\u0db1\u0dca \u0dc4\u0ddd English \u0dc0\u0dbd\u0dd2\u0db1\u0dca \u0db4\u0dca\u200d\u0dbb\u0dc1\u0dca\u0db1\u0dba\u0d9a\u0dca \u0d85\u0dc3\u0db1\u0dca\u0db1..."}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) askQuestion();
              }}
            />
            <button onClick={askQuestion} disabled={busy || !question.trim()} title="Ask question">
              {busy ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            </button>
          </div>

          <div className="answer-grid">
            <article className="answer-panel">
              <div className="panel-title">
                <Search size={18} />
                <h2>Answer</h2>
                <span className="pill">{languageLabel}</span>
              </div>
              {answer ? (
                <>
                  <p className="answer-text">{answer.answer}</p>
                  <div className="confidence">
                    <span>Confidence</span>
                    <meter min="0" max="1" value={answer.confidence} />
                    <strong>{Math.round(answer.confidence * 100)}%</strong>
                  </div>
                </>
              ) : (
                <p className="empty">Ask a question to retrieve source passages and generate an answer.</p>
              )}
            </article>

            <article className="sources-panel">
              <div className="panel-title">
                <FileText size={18} />
                <h2>Sources</h2>
              </div>
              <div className="sources-list">
                {answer?.sources.map((source, index) => (
                  <details key={source.chunk_id} open={index === 0}>
                    <summary>
                      <span>{source.filename}</span>
                      <b>{Math.round(source.score * 100)}%</b>
                    </summary>
                    <p>{source.text}</p>
                    <small>
                      Page {source.page_number || "N/A"} - Highlights:{" "}
                      {source.highlights.length ? source.highlights.join(", ") : "semantic match"}
                    </small>
                  </details>
                ))}
                {!answer?.sources.length && <p className="empty">Source citations will appear here.</p>}
              </div>
            </article>
          </div>
        </section>

        <aside className="panel side-panel">
          <div className="panel-title">
            <BarChart3 size={18} />
            <h2>Admin</h2>
          </div>
          <div className="stat-grid">
            <span>Documents <strong>{stats?.documents ?? 0}</strong></span>
            <span>Chunks <strong>{stats?.chunks ?? 0}</strong></span>
            <span>Chats <strong>{stats?.conversations ?? 0}</strong></span>
            <span>Retrievals <strong>{stats?.retrieval_logs ?? 0}</strong></span>
          </div>

          <div className="panel-title history-title">
            <History size={18} />
            <h2>History</h2>
          </div>
          <div className="history-list">
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() =>
                  setAnswer({
                    question: item.question,
                    answer: item.answer,
                    question_language: item.question_language,
                    confidence: item.confidence,
                    sources: []
                  })
                }
              >
                <strong>{item.question}</strong>
                <span>{new Date(item.created_at).toLocaleString()}</span>
              </button>
            ))}
            {!history.length && <p className="empty">No conversations yet.</p>}
          </div>
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
