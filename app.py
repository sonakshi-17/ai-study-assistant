import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from groq import Groq
from dotenv import load_dotenv
import os
import threading

# Load API key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Global vector store
vector_store = None
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ============ CORE FUNCTIONS ============
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def create_vector_store(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_text(text)
    vs = FAISS.from_texts(chunks, embeddings)
    return vs

def answer_question(question):
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

# ============ UI FUNCTIONS ============
def upload_pdf():
    global vector_store
    file_path = filedialog.askopenfilename(
        filetypes=[("PDF files", "*.pdf")]
    )
    if not file_path:
        return

    status_label.config(text="Processing PDF... please wait", fg="orange")
    ask_button.config(state="disabled")
    root.update()

    def process():
        global vector_store
        try:
            text = extract_text_from_pdf(file_path)
            vector_store = create_vector_store(text)
            filename = os.path.basename(file_path)
            status_label.config(
                text=f"✓ Loaded: {filename}", fg="green"
            )
            ask_button.config(state="normal")
        except Exception as e:
            status_label.config(text=f"Error: {str(e)}", fg="red")

    threading.Thread(target=process).start()

def ask_question():
    if vector_store is None:
        messagebox.showwarning("No PDF", "Please upload a PDF first!")
        return

    question = question_entry.get().strip()
    if not question:
        messagebox.showwarning("Empty", "Please enter a question!")
        return

    answer_box.config(state="normal")
    answer_box.delete(1.0, tk.END)
    answer_box.insert(tk.END, "Thinking...")
    answer_box.config(state="disabled")
    ask_button.config(state="disabled")
    root.update()

    def get_answer():
        try:
            answer = answer_question(question)
            answer_box.config(state="normal")
            answer_box.delete(1.0, tk.END)
            answer_box.insert(tk.END, answer)
            answer_box.config(state="disabled")
        except Exception as e:
            answer_box.config(state="normal")
            answer_box.delete(1.0, tk.END)
            answer_box.insert(tk.END, f"Error: {str(e)}")
            answer_box.config(state="disabled")
        ask_button.config(state="normal")

    threading.Thread(target=get_answer).start()

# ============ UI LAYOUT ============
root = tk.Tk()
root.title("AI Study Assistant")
root.geometry("700x550")
root.configure(bg="#1e1e2e")

# Title
tk.Label(
    root, text="AI Study Assistant",
    font=("Helvetica", 20, "bold"),
    bg="#1e1e2e", fg="#cdd6f4"
).pack(pady=20)

# Upload button
tk.Button(
    root, text="Upload PDF",
    command=upload_pdf,
    bg="#89b4fa", fg="#1e1e2e",
    font=("Helvetica", 12, "bold"),
    padx=20, pady=8, cursor="hand2"
).pack(pady=5)

# Status label
status_label = tk.Label(
    root, text="No PDF uploaded yet",
    bg="#1e1e2e", fg="#6c7086",
    font=("Helvetica", 10)
)
status_label.pack(pady=5)

# Question entry
tk.Label(
    root, text="Ask a question:",
    bg="#1e1e2e", fg="#cdd6f4",
    font=("Helvetica", 12)
).pack(pady=(15, 5))

question_entry = tk.Entry(
    root, width=60,
    font=("Helvetica", 11),
    bg="#313244", fg="#cdd6f4",
    insertbackground="white"
)
question_entry.pack(pady=5, ipady=8)

# Ask button
ask_button = tk.Button(
    root, text="Ask",
    command=ask_question,
    bg="#a6e3a1", fg="#1e1e2e",
    font=("Helvetica", 12, "bold"),
    padx=20, pady=8,
    cursor="hand2", state="disabled"
)
ask_button.pack(pady=10)

# Answer box
tk.Label(
    root, text="Answer:",
    bg="#1e1e2e", fg="#cdd6f4",
    font=("Helvetica", 12)
).pack(pady=(10, 5))

answer_box = scrolledtext.ScrolledText(
    root, width=75, height=10,
    font=("Helvetica", 11),
    bg="#313244", fg="#cdd6f4",
    state="disabled", wrap=tk.WORD
)
answer_box.pack(pady=5)

root.mainloop()