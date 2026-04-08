import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from groq import Groq
from dotenv import load_dotenv
import os

# Load API key from .env file
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============ STAGE 1 - Extract Text ============
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# ============ STAGE 2 - Chunk + Store in FAISS ============
def create_vector_store(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_text(text)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vector_store = FAISS.from_texts(chunks, embeddings)
    return vector_store

# ============ STAGE 3 - Answer with Groq ============
def answer_question(vector_store, question):
    relevant_chunks = vector_store.similarity_search(question, k=3)
    context = "\n\n".join([doc.page_content for doc in relevant_chunks])

    prompt = f"""You are a helpful study assistant.
Answer the question based ONLY on the context below.
If the answer is not in the context, say "I could not find this in the uploaded document."

Context:
{context}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ============ TEST ============
print("Loading PDF...")
text = extract_text_from_pdf("SONAKSHI_ARORA.pdf")

print("Creating vector store...")
vector_store = create_vector_store(text)

print("Ready! Testing questions...\n")

questions = [
    "What projects has Sonakshi built?",
    "What programming languages does Sonakshi know?",
    "What is Sonakshi's education?"
]

for q in questions:
    print(f"Question: {q}")
    answer = answer_question(vector_store, q)
    print(f"Answer: {answer}")
    print("-" * 50)