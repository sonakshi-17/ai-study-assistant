# AI Study Assistant

A React + FastAPI study assistant that lets users create accounts, upload PDFs,
save a document library, and ask questions answered from document context with
page citations.

## Run the frontend

```powershell
npm install
npm run dev -- --host 127.0.0.1 --port 5178
```

Open `http://127.0.0.1:5178`.

## Run the backend

Create a Python environment, install the API dependencies, and start FastAPI:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8010
```

Add your Groq key to `.env`:

```env
GROQ_API_KEY=your_key_here
APP_SECRET=replace_with_a_long_random_secret
DATABASE_PATH=study_assistant.db
MAX_UPLOAD_BYTES=15728640
```

## Product features

- Account registration and sign in
- Per-user PDF library
- Persistent document chunks in SQLite
- Saved Q&A history per document
- Page citations for retrieved context
- Upload size limit and PDF-only validation
