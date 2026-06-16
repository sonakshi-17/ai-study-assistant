import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  FileText,
  FileUp,
  Loader2,
  LogOut,
  MessageSquareText,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010/api";

function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ title, text }) {
  return (
    <div className="empty-state">
      <BrainCircuit size={28} />
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("study_token") || "");
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "" });
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [chats, setChats] = useState([]);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [authState, setAuthState] = useState("idle");
  const [uploadState, setUploadState] = useState("idle");
  const [askState, setAskState] = useState("idle");
  const fileInputRef = useRef(null);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId) || null,
    [documents, selectedDocumentId],
  );

  const authHeaders = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token],
  );

  const totalPages = documents.reduce((sum, document) => sum + document.pages, 0);
  const totalChats = chats.length;

  async function api(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...authHeaders,
        ...(options.headers || {}),
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Something went wrong.");
    }
    return payload;
  }

  async function loadDocuments() {
    const payload = await api("/documents");
    setDocuments(payload.documents);
    setSelectedDocumentId((current) => current || payload.documents[0]?.id || null);
  }

  async function loadChats(documentId) {
    if (!documentId) {
      setChats([]);
      return;
    }
    const payload = await api(`/documents/${documentId}/chats`);
    setChats(payload.chats);
  }

  useEffect(() => {
    if (!token) return;

    api("/me")
      .then((payload) => {
        setUser(payload.user);
        return loadDocuments();
      })
      .catch(() => {
        localStorage.removeItem("study_token");
        setToken("");
        setUser(null);
      });
  }, [token]);

  useEffect(() => {
    if (token && selectedDocumentId) {
      loadChats(selectedDocumentId).catch((err) => setError(err.message));
    }
  }, [selectedDocumentId, token]);

  async function handleAuth(event) {
    event.preventDefault();
    setAuthState("loading");
    setError("");

    try {
      const path = authMode === "login" ? "/auth/login" : "/auth/register";
      const body =
        authMode === "login"
          ? { email: authForm.email, password: authForm.password }
          : authForm;
      const payload = await api(path, {
        method: "POST",
        body: JSON.stringify(body),
        headers: {},
      });
      localStorage.setItem("study_token", payload.token);
      setToken(payload.token);
      setUser(payload.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setAuthState("idle");
    }
  }

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadState("loading");
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const payload = await api("/documents", {
        method: "POST",
        body: formData,
      });
      setDocuments((current) => [payload.document, ...current]);
      setSelectedDocumentId(payload.document.id);
      setChats([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadState("idle");
      event.target.value = "";
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    if (!selectedDocument || !question.trim()) return;

    setAskState("loading");
    setError("");

    try {
      const payload = await api(`/documents/${selectedDocument.id}/ask`, {
        method: "POST",
        body: JSON.stringify({ question }),
      });
      setChats((current) => [...current, payload.chat]);
      setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setAskState("idle");
    }
  }

  function logout() {
    localStorage.removeItem("study_token");
    setToken("");
    setUser(null);
    setDocuments([]);
    setSelectedDocumentId(null);
    setChats([]);
  }

  if (!user) {
    return (
      <main className="auth-shell">
        <section className="auth-hero">
          <div className="eyebrow">
            <Sparkles size={18} />
            PDF-powered revision desk
          </div>
          <h1>AI Study Assistant</h1>
          <p>
            Save documents, ask context-aware questions, and keep your study
            answers organized by account.
          </p>
          <div className="trust-row">
            <span>
              <ShieldCheck size={18} />
              Private library
            </span>
            <span>
              <BookOpenCheck size={18} />
              Page citations
            </span>
          </div>
        </section>

        <form className="auth-card" onSubmit={handleAuth}>
          <strong>{authMode === "login" ? "Welcome back" : "Create your workspace"}</strong>
          {authMode === "register" && (
            <input
              type="text"
              placeholder="Name"
              value={authForm.name}
              onChange={(event) => setAuthForm({ ...authForm, name: event.target.value })}
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={authForm.email}
            onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={authForm.password}
            onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
            required
            minLength={8}
          />
          <button className="primary-action" type="submit" disabled={authState === "loading"}>
            {authState === "loading" ? <Loader2 className="spin" size={18} /> : <CheckCircle2 size={18} />}
            {authMode === "login" ? "Sign in" : "Create account"}
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
          >
            {authMode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
          </button>
          {error && <div className="error-banner">{error}</div>}
        </form>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow dark">
            <Sparkles size={17} />
            Study workspace
          </span>
          <h1>AI Study Assistant</h1>
        </div>
        <button className="icon-text-button" type="button" onClick={logout}>
          <LogOut size={18} />
          Sign out
        </button>
      </header>

      <section className="summary-band">
        <StatCard label="Documents" value={documents.length} />
        <StatCard label="Pages saved" value={totalPages} />
        <StatCard label="Current Q&A" value={totalChats} />
      </section>

      <section className="product-grid">
        <aside className="library-panel">
          <div className="panel-header">
            <div>
              <span>Signed in as</span>
              <strong>{user.name}</strong>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={handleUpload}
            />
            <button
              className="primary-action compact"
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadState === "loading"}
            >
              {uploadState === "loading" ? <Loader2 className="spin" size={18} /> : <FileUp size={18} />}
              Upload
            </button>
          </div>

          <div className="document-list">
            {documents.length === 0 ? (
              <EmptyState title="No PDFs yet" text="Upload your first study document." />
            ) : (
              documents.map((document) => (
                <button
                  className={`document-item ${document.id === selectedDocumentId ? "active" : ""}`}
                  type="button"
                  key={document.id}
                  onClick={() => setSelectedDocumentId(document.id)}
                >
                  <FileText size={22} />
                  <span>
                    <strong>{document.filename}</strong>
                    <small>
                      {document.pages} pages · {document.chunks} chunks
                    </small>
                  </span>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="ask-panel">
          {selectedDocument ? (
            <>
              <div className="active-document">
                <div>
                  <span>Active document</span>
                  <strong>{selectedDocument.filename}</strong>
                </div>
                <div className="pill-row">
                  <span>{selectedDocument.pages} pages</span>
                  <span>{selectedDocument.characters.toLocaleString("en-IN")} chars</span>
                </div>
              </div>

              <div className="chat-list">
                {chats.length === 0 ? (
                  <EmptyState
                    title="Ask your first question"
                    text="Answers are saved here with the pages used as context."
                  />
                ) : (
                  chats.map((chat) => (
                    <article className="chat-card" key={chat.id}>
                      <h3>{chat.question}</h3>
                      <p>{chat.answer}</p>
                      <div className="citation-row">
                        {(chat.citations || []).map((page) => (
                          <span key={page}>Page {page}</span>
                        ))}
                      </div>
                    </article>
                  ))
                )}
              </div>

              <form className="question-row" onSubmit={handleAsk}>
                <input
                  type="text"
                  placeholder="Ask a question from this PDF"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />
                <button type="submit" disabled={askState === "loading" || !question.trim()}>
                  {askState === "loading" ? <Loader2 className="spin" size={19} /> : <Send size={19} />}
                </button>
              </form>
            </>
          ) : (
            <EmptyState title="Choose or upload a PDF" text="Your document Q&A workspace will appear here." />
          )}

          {error && <div className="error-banner">{error}</div>}
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
