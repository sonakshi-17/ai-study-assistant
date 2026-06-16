import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, EmailStr, Field


load_dotenv()

APP_SECRET = os.getenv("APP_SECRET", "change-this-secret-before-production")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "study_assistant.db"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(7 * 24 * 60 * 60)))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
app = FastAPI(title="AI Study Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
        "http://localhost:5179",
        "http://127.0.0.1:5179",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1200)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                pages INTEGER NOT NULL,
                chunks INTEGER NOT NULL,
                characters INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password, password_hash):
    salt, expected = password_hash.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return hmac.compare_digest(digest.hex(), expected)


def encode_token(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(APP_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def decode_token(token):
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(APP_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Bad signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("exp", 0) < time.time():
            raise ValueError("Expired token")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Please sign in again.") from exc


def create_token(user):
    return encode_token(
        {
            "sub": user["id"],
            "email": user["email"],
            "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        }
    )


def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing sign-in token.")
    payload = decode_token(authorization.removeprefix("Bearer ").strip())

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (payload["sub"],),
        ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="User account was not found.")
    return dict(user)


def public_user(user, token=None):
    response = {"user": {"id": user["id"], "name": user["name"], "email": user["email"]}}
    if token:
        response["token"] = token
    return response


def extract_pages_from_pdf(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": index, "text": text})
    return pages


def split_page_text(text, chunk_size=900, overlap=140):
    clean_text = re.sub(r"\s+", " ", text).strip()
    if not clean_text:
        return []

    chunks = []
    start = 0
    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        chunks.append(clean_text[start:end])
        if end == len(clean_text):
            break
        start = max(0, end - overlap)
    return chunks


def tokenize(text):
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def find_relevant_chunks(question, rows, limit=4):
    question_terms = tokenize(question)
    scored = []
    for row in rows:
        chunk_terms = tokenize(row["content"])
        score = len(question_terms & chunk_terms)
        scored.append((score, -row["chunk_index"], dict(row)))

    scored.sort(reverse=True)
    best = [row for score, _, row in scored if score > 0][:limit]
    return best or [dict(row) for row in rows[:limit]]


def answer_from_context(question, chunks):
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is missing. Add it to .env and restart the backend.",
        )

    context = "\n\n".join(
        f"[Page {chunk['page_number']}] {chunk['content']}" for chunk in chunks
    )
    prompt = f"""You are a helpful study assistant.
Answer the question based ONLY on the context below.
If the answer is not in the context, say "I could not find this in the uploaded document."
Keep the answer clear, student-friendly, and easy to revise from.
When useful, mention page numbers from the context.

Context:
{context}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def require_document(conn, document_id, user_id):
    document = conn.execute(
        """
        SELECT id, filename, pages, chunks, characters, created_at
        FROM documents
        WHERE id = ? AND user_id = ?
        """,
        (document_id, user_id),
    ).fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="Document was not found.")
    return document


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {"ok": True, "database": str(DATABASE_PATH), "max_upload_mb": MAX_UPLOAD_BYTES // 1024 // 1024}


@app.post("/api/auth/register")
def register(request: AuthRequest):
    name = (request.name or request.email.split("@")[0]).strip()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, request.email.lower(), hash_password(request.password), utc_now()),
            )
            user = conn.execute(
                "SELECT id, name, email, created_at FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc

    return public_user(dict(user), create_token(user))


@app.post("/api/auth/login")
def login(request: LoginRequest):
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
            (request.email.lower(),),
        ).fetchone()

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return public_user(dict(user), create_token(user))


@app.get("/api/me")
def me(user=Depends(current_user)):
    return public_user(user)


@app.get("/api/documents")
def list_documents(user=Depends(current_user)):
    with get_db() as conn:
        documents = conn.execute(
            """
            SELECT id, filename, pages, chunks, characters, created_at
            FROM documents
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            """,
            (user["id"],),
        ).fetchall()
    return {"documents": [dict(document) for document in documents]}


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...), user=Depends(current_user)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF is larger than the upload limit.")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        temp_file.write(data)

    try:
        pages = extract_pages_from_pdf(temp_path)
        chunk_records = []
        total_characters = 0
        for page in pages:
            total_characters += len(page["text"])
            for content in split_page_text(page["text"]):
                chunk_records.append((page["page"], len(chunk_records), content))

        if not chunk_records:
            raise HTTPException(status_code=422, detail="No readable text was found in this PDF.")

        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documents (user_id, filename, pages, chunks, characters, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user["id"], file.filename, len(pages), len(chunk_records), total_characters, utc_now()),
            )
            document_id = cursor.lastrowid
            conn.executemany(
                """
                INSERT INTO document_chunks (document_id, page_number, chunk_index, content)
                VALUES (?, ?, ?, ?)
                """,
                [(document_id, page, index, content) for page, index, content in chunk_records],
            )
            document = conn.execute(
                """
                SELECT id, filename, pages, chunks, characters, created_at
                FROM documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()

        return {"message": "Document ready", "document": dict(document)}
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@app.get("/api/documents/{document_id}/chats")
def list_chats(document_id: int, user=Depends(current_user)):
    with get_db() as conn:
        require_document(conn, document_id, user["id"])
        chats = conn.execute(
            """
            SELECT id, question, answer, citations, created_at
            FROM chats
            WHERE document_id = ? AND user_id = ?
            ORDER BY datetime(created_at) ASC
            """,
            (document_id, user["id"]),
        ).fetchall()

    return {
        "chats": [
            {**dict(chat), "citations": json.loads(chat["citations"])} for chat in chats
        ]
    }


@app.post("/api/documents/{document_id}/ask")
def ask_document(document_id: int, request: QuestionRequest, user=Depends(current_user)):
    question = request.question.strip()
    with get_db() as conn:
        require_document(conn, document_id, user["id"])
        chunks = conn.execute(
            """
            SELECT id, page_number, chunk_index, content
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY chunk_index ASC
            """,
            (document_id,),
        ).fetchall()

        relevant = find_relevant_chunks(question, chunks)
        answer = answer_from_context(question, relevant)
        citations = sorted({chunk["page_number"] for chunk in relevant})
        cursor = conn.execute(
            """
            INSERT INTO chats (document_id, user_id, question, answer, citations, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, user["id"], question, answer, json.dumps(citations), utc_now()),
        )

    return {
        "chat": {
            "id": cursor.lastrowid,
            "question": question,
            "answer": answer,
            "citations": citations,
            "created_at": utc_now(),
        }
    }
