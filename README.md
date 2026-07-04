# AI Study Assistant

🌐 **Live demo:** [ai-study-assistant-psi-silk.vercel.app](https://ai-study-assistant-psi-silk.vercel.app)

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

## Deploy on Vercel

This repository is configured to deploy the Vite frontend and FastAPI API as one
Vercel project. The browser calls the API through the same `/api` domain.

1. Push the repository to GitHub and import it at `vercel.com/new`.
2. In the Vercel project, open **Storage**, create a Neon Postgres integration,
   and connect it to this project. Ensure it provides `POSTGRES_URL` (or add the
   provided connection string under that name).
3. In **Settings → Environment Variables**, add:
   - `GROQ_API_KEY`: your Groq API key
   - `APP_SECRET`: a long random value used to sign login tokens
4. Redeploy the project.

Vercel Functions accept request bodies up to 4.5 MB, so hosted PDF uploads are
limited to 4 MB by default. Local development keeps the 15 MB limit and SQLite.
Without Postgres, Vercel falls back to temporary SQLite storage and data may be
lost whenever the function restarts; use Postgres for a showcase deployment.

## Product features

- Account registration and sign in
- Per-user PDF library
- Persistent document chunks in SQLite
- Saved Q&A history per document
- Page citations for retrieved context
- Upload size limit and PDF-only validation
