# 📄 DocChat AI — Chat with Any PDF

> **Upload a PDF. Ask anything. Get answers with page references.**

## 🚀 Live Demo

### 👉 [Open DocChat AI](https://docchatassistant.streamlit.app/)

> **Note:** The app is hosted on Streamlit's free tier, so the first request may take a little longer after a period of inactivity.
>
> To protect free-tier LLM usage, the demo is limited to **one PDF at a time (up to 50 pages / 10 MB)**, **5 questions per visitor**, and **50 questions per day** in total.

<!-- Add a screenshot or GIF of your app here:
![DocChat AI screenshot](screenshot.png)
-->

---

## 📌 Overview

**DocChat AI** is an AI-powered document assistant that lets you upload your own PDF and ask questions about it in plain language.

Instead of scrolling through long documents, you can simply ask:

* 📘 *"What is this document about?"*
* 📝 *"Summarize the main points."*
* ✅ *"What are the key requirements mentioned?"*
* 💳 *"What does the document say about refunds?"*

DocChat AI finds the most relevant parts of your document and answers **only from that content**, with the source pages shown under every answer.

It works with any text-based PDF: handbooks, reports, research papers, manuals, contracts, course material and more.

---

# ✨ Features

### 📤 Upload Your Own PDF

Upload a PDF and the app processes it automatically. A status card confirms when the document is ready to chat.

```text
Upload PDF
    ↓
Document processed ✓
    ↓
Ask questions
```

---

### 🔎 Answers with Page References

Every answer shows where the information came from.

```text
Sources: handbook.pdf — pages 12, 15
```

This makes the answers easy to verify.

---

### 🛡️ Honest Answers (No Made-Up Information)

The assistant is instructed to answer **only** from the retrieved document content. If the answer isn't in the document, it says:

```text
"I couldn't find this information in the uploaded document."
```

---

### 🔄 Fresh Index for Every Document

A brand-new FAISS index is built for each upload, so a new document never uses an old document's data. Removing the file clears the chat and the index.

---

### 🧯 Friendly Error Handling

Clear messages (no raw tracebacks) for:

* Wrong file type or corrupted PDF
* Empty PDF or PDF with no extractable text (e.g. scanned images)
* PDFs that are too large
* Embedding failures
* LLM/API errors and rate limits

---

### 🚦 Built-in Demo Limits

| Limit                        | Value             |
| ---------------------------- | ----------------- |
| Questions per visitor        | 5                 |
| Questions per day (all users)| 50                |
| PDF size                     | 10 MB             |
| PDF length                   | 50 pages          |
| Question length              | 300 characters    |
| Answer length                | 600 tokens        |

An optional access code can also be enabled with a `DEMO_CODE` secret.

---

# 🏗️ System Architecture

```text
              ┌─────────────────────┐
              │     Upload PDF      │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │     PyPDFLoader     │
              │  (text + page no.)  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Text Chunking     │
              │  800 chars / 100    │
              │      overlap        │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │     Embeddings      │
              │   all-MiniLM-L6-v2  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    FAISS Index      │
              └──────────┬──────────┘
                         │
   ┌─────────────────────┴─────────────────────┐
   │             LangGraph workflow            │
   │                                           │
   │   Question → retrieve → generate_answer   │
   │              (top 4)     (Groq LLM)       │
   └─────────────────────┬─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Answer + Sources   │
              └─────────────────────┘
```

---

# 🧠 RAG Design

The whole document is **not** sent to the LLM for every question. Instead:

```text
User Question
      ↓
Similarity Search in FAISS (top 4 chunks)
      ↓
Context (with file name + page numbers) + Question
      ↓
Groq LLM
      ↓
Answer + Source pages
```

This keeps answers focused on the relevant parts of the document and keeps token usage low.

### LangGraph Workflow

```text
START → retrieve → generate_answer → END
```

* **retrieve** — finds the most relevant chunks and their page numbers
* **generate_answer** — answers strictly from that context, or says the information wasn't found

---

# 🛠️ Tech Stack

| Technology           | Purpose                          |
| -------------------- | -------------------------------- |
| **Python**           | Core application                 |
| **Streamlit**        | Web interface & deployment       |
| **LangGraph**        | RAG workflow                     |
| **LangChain**        | RAG components                   |
| **Groq**             | LLM inference                    |
| **FAISS**            | Vector database                  |
| **Hugging Face**     | Sentence embeddings              |
| **all-MiniLM-L6-v2** | Text embeddings                  |
| **PyPDF**            | PDF loading                      |

---

# 🤖 AI Models

### Language Model

```text
openai/gpt-oss-120b
```

Used to generate answers from the retrieved document context.

### Embeddings

```text
sentence-transformers/all-MiniLM-L6-v2
```

Used to convert document chunks into vectors for semantic search.

---

# ⚙️ Run Locally

```bash
# 1. Clone the repo
git clone YOUR_REPO_LINK
cd YOUR_REPO_FOLDER

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create a .env file with your Groq API key
GROQ_API_KEY=your_key_here

# 4. Start the app
streamlit run streamlit_app.py
```

### Project Structure

```text
├── chatbot.py          # PDF processing, FAISS index, LangGraph workflow
├── streamlit_app.py    # Streamlit UI, upload flow, usage limits
├── requirements.txt
├── .env                # GROQ_API_KEY (not committed)
└── .gitignore          # includes .env and usage.json
```

---

# 🚀 Deployment

DocChat AI is deployed on **Streamlit Community Cloud**.

Add your key under **App settings → Secrets**:

```toml
GROQ_API_KEY = "your_key_here"
```

---

# ⚠️ Current Limitations

* Scanned PDFs (images only) are not supported, since there is no OCR.
* Each question is answered independently, so follow-up questions don't use earlier chat history.
* Broad requests like "summarize everything" only see the most relevant chunks, not the full document.
* The demo limits (1 PDF, 5 questions per visitor) exist to protect free-tier usage.

---

# 🔮 Future Improvements

* Conversation memory for follow-up questions
* OCR support for scanned PDFs
* Multiple PDFs in one session
* Full-document summarization

---

# 🎯 Use Cases

* 🎓 University handbooks and course material
* 📚 Research papers and reports
* 📋 Contracts and company documents
* 🔧 User manuals and technical documentation
* 📖 Books and long reading material

---

Upload a document, let DocChat AI index it, and **chat with your PDF**.
