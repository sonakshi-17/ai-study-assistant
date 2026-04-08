# AI Study Assistant — Context-Aware Doubt Solver

A RAG-based (Retrieval-Augmented Generation) desktop application where students upload study material (PDFs) and ask questions — getting answers grounded strictly in their own documents.

## Problem Statement
Students struggle to find specific answers from lengthy PDFs, textbooks, and notes. Manual searching is time-consuming and inefficient. This tool eliminates that by letting AI answer questions directly from uploaded material.

## Features
- Upload any PDF (notes, textbook, assignment)
- Ask questions in natural language
- Get AI-generated answers based ONLY on your document
- Semantic search — finds answers by meaning, not just keywords

## Tech Stack
- Python
- pdfplumber — PDF text extraction
- LangChain — RAG pipeline orchestration
- FAISS — Vector database for semantic search
- HuggingFace MiniLM — Text embedding model
- Groq API (LLaMA 3) — LLM for answer generation
- Tkinter — Desktop UI

## How It Works
1. User uploads a PDF
2. Text is extracted and split into overlapping chunks
3. Chunks are converted to embeddings and stored in FAISS
4. User asks a question
5. FAISS finds the most relevant chunks semantically
6. LLaMA 3 generates an answer using only those chunks

## Setup Instructions

### 1. Clone the repository
git clone https://github.com/sonakshi-17/ai-study-assistant.git
cd ai-study-assistant

### 2. Install dependencies
pip install pdfplumber langchain langchain-text-splitters langchain-huggingface
pip install langchain-community faiss-cpu sentence-transformers groq python-dotenv

### 3. Add your API key
Create a .env file in the project folder:
GROQ_API_KEY=your_groq_api_key_here

Get your free key at: https://console.groq.com

### 4. Run the app
python app.py

## What This Project Demonstrates
- RAG (Retrieval-Augmented Generation) architecture
- Vector search using FAISS
- LLM integration with context grounding
- Practical AI application with real-world use case
- Clean desktop UI with Tkinter

## Author
Sonakshi Arora
GitHub: https://github.com/sonakshi-17
Email: sonakshiarora1709@gmail.com
