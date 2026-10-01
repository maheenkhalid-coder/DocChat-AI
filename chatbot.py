import os
import tempfile
from typing import TypedDict

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from langgraph.graph import StateGraph, START, END


# Load environment variables (.env locally). On Streamlit Cloud the key
# comes from st.secrets, which streamlit_app.py copies into os.environ.
load_dotenv()


# --------------------------------------------------
# 1. Models (loaded once)
# --------------------------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2,  # lower than before: we want facts from the document, not creativity
    max_tokens=300
)

NOT_FOUND_MESSAGE = "I couldn't find this information in the uploaded document."
MAX_PAGES = 200  # per PDF, keeps processing reasonable on free hosting


class DocumentError(Exception):
    """Problems with the uploaded file(s). The message is safe to show to users."""


# --------------------------------------------------
# 2. Build a vector store from uploaded PDFs
# --------------------------------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)


def build_vectorstore(files):
    """
    files: list of (filename, pdf_bytes)
    Returns (FAISS vectorstore, number_of_chunks).
    A NEW store is built every time, so an old document is never reused.
    """
    all_chunks = []

    for name, data in files:

        if not name.lower().endswith(".pdf") or not data.startswith(b"%PDF"):
            raise DocumentError(f"'{name}' is not a valid PDF file.")

        # PyPDFLoader needs a file path, so write the upload to a temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            path = tmp.name

        try:
            pages = PyPDFLoader(path).load()
        except Exception:
            raise DocumentError(f"Couldn't read '{name}'. The file may be corrupted or password-protected.")
        finally:
            os.remove(path)

        if len(pages) > MAX_PAGES:
            raise DocumentError(
                f"'{name}' has {len(pages)} pages. The limit is {MAX_PAGES} pages per PDF."
            )

        # Drop pages with no text (e.g. scanned images)
        pages = [p for p in pages if p.page_content.strip()]

        if not pages:
            raise DocumentError(
                f"'{name}' has no extractable text. It may be a scanned PDF (images only)."
            )

        # Remember the file name and page number for every chunk (used for sources)
        for p in pages:
            p.metadata["source"] = name
            p.metadata["page"] = int(p.metadata.get("page", 0)) + 1  # pages start at 1

        all_chunks.extend(splitter.split_documents(pages))

    try:
        vectorstore = FAISS.from_documents(all_chunks, embeddings)
    except Exception:
        raise DocumentError("Couldn't create embeddings for this document. Please try again.")

    return vectorstore, len(all_chunks)


# --------------------------------------------------
# 3. State
# --------------------------------------------------

class State(TypedDict):
    question: str
    context: str
    sources: list   # [[file_name, page], ...]
    answer: str


# --------------------------------------------------
# 4. LangGraph workflow: retrieve -> generate_answer
# --------------------------------------------------

def build_graph(vectorstore):
    """Creates a graph that searches ONLY the given document's vector store."""

    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    def retrieve(state: State):
        docs = retriever.invoke(state["question"])

        context = "\n\n".join(
            f"[{d.metadata['source']}, page {d.metadata['page']}]\n{d.page_content}"
            for d in docs
        )

        sources = sorted(
            {(d.metadata["source"], d.metadata["page"]) for d in docs}
        )

        return {"context": context, "sources": [list(s) for s in sources]}

    def generate_answer(state: State):
        prompt = f"""
You are a helpful document assistant.

Answer the question using ONLY the document context below.

Rules:
- If the answer is not in the context, reply exactly: "{NOT_FOUND_MESSAGE}"
- Never guess or use outside knowledge.
- When useful, mention the page number, like (page 12).
- Be clear and concise.

Document context:
{state["context"]}

Question:
{state["question"]}
"""
        answer = llm.invoke(prompt).content.strip()

        # No point showing sources when nothing was found
        if "couldn't find this information" in answer.lower():
            return {"answer": answer, "sources": []}

        return {"answer": answer}

    graph = StateGraph(State)

    graph.add_node("retrieve", retrieve)
    graph.add_node("generate_answer", generate_answer)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()
