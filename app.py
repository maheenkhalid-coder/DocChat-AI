import os
import json
import html
import threading
from datetime import date
from pathlib import Path

import streamlit as st


# --------------------------------------------------
# Page setup
# --------------------------------------------------

st.set_page_config(
    page_title="DocChat AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# API key
# --------------------------------------------------

# On Streamlit Cloud the key lives in st.secrets;
# locally it can come from .env / environment variables.
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass


# --------------------------------------------------
# Backend
# --------------------------------------------------

from chatbot import build_vectorstore, build_graph, DocumentError


# --------------------------------------------------
# Limits
# --------------------------------------------------

# Maximum questions across ALL visitors per day
DAILY_LIMIT = 50

# Maximum length of one user question
MAX_QUESTION_LENGTH = 300

# Maximum PDF size (page limit is MAX_PAGES in chatbot.py)
MAX_FILE_MB = 10

# File used to persist the daily counter
USAGE_FILE = Path(__file__).parent / "usage.json"


STARTERS = [
    "What is this document about?",
    "Summarize the main points.",
    "What are the key requirements mentioned?",
    "List any important dates, numbers or deadlines.",
]


# --------------------------------------------------
# Global daily counter
# Shared by every visitor and saved in usage.json
# --------------------------------------------------

@st.cache_resource
def _usage_lock():
    return threading.Lock()


def _read_usage():
    today = date.today().isoformat()

    try:
        data = json.loads(USAGE_FILE.read_text())

        if data.get("date") == today:
            return {
                "date": today,
                "count": int(data.get("count", 0)),
            }

    except (FileNotFoundError, ValueError, TypeError):
        pass

    # New day or missing/invalid file
    return {
        "date": today,
        "count": 0,
    }


def daily_used() -> int:
    """Return how many questions have been used today."""
    with _usage_lock():
        return _read_usage()["count"]


def reserve_daily_slot() -> bool:
    """
    Reserve one question slot.

    Returns:
        True  -> question is allowed
        False -> daily limit reached
    """
    with _usage_lock():
        usage = _read_usage()

        if usage["count"] >= DAILY_LIMIT:
            return False

        usage["count"] += 1

        USAGE_FILE.write_text(
            json.dumps(usage, indent=2),
            encoding="utf-8",
        )

        return True


# --------------------------------------------------
# Styling
# --------------------------------------------------

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700;800&family=Source+Sans+3:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stChatInput textarea {
    font-family: 'Source Sans 3', sans-serif;
}

h1, h2, h3, h4, .cd-title, .cd-side-title {
    font-family: 'Bricolage Grotesque', sans-serif !important;
    letter-spacing: -0.02em;
}

#MainMenu,
footer,
header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0;
}

.block-container {
    padding-top: 1.6rem;
    max-width: 900px;
}


/* Hero banner */

.cd-hero {
    background: linear-gradient(
        120deg,
        #1E1B4B 0%,
        #312E81 55%,
        #0F766E 130%
    );
    border-radius: 22px;
    padding: 30px 34px;
    color: #fff;
    position: relative;
    overflow: hidden;
    margin-bottom: 1.2rem;
}

.cd-hero::after {
    content: "📄";
    position: absolute;
    right: 26px;
    top: 8px;
    font-size: 110px;
    opacity: 0.13;
    transform: rotate(-12deg);
}

.cd-title {
    font-size: 2.3rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.1;
    color: #fff;
}

.cd-sub {
    margin: 8px 0 14px 0;
    font-size: 1.05rem;
    color: #C7D2FE;
    max-width: 580px;
}

.cd-chip {
    display: inline-block;
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.25);
    color: #fff;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.9rem;
    font-weight: 500;
}


/* Document status card */

.cd-doc {
    border: 1px solid rgba(13,148,136,0.45);
    background: rgba(13,148,136,0.08);
    border-radius: 16px;
    padding: 14px 18px;
    margin: 6px 0 14px 0;
}

.cd-doc-row {
    font-weight: 600;
    margin: 2px 0;
}

.cd-doc-status {
    color: #0D9488;
    font-weight: 600;
    margin-top: 8px;
}

.cd-doc-meta {
    color: #6B7280;
    font-size: 0.88rem;
}


/* Sources */

.cd-sources {
    display: inline-block;
    margin-top: 8px;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #4F46E5;
    background: rgba(79,70,229,0.10);
}


/* Chat bubbles */

[data-testid="stChatMessage"] {
    border-radius: 18px;
    padding: 14px 18px;
    margin-bottom: 10px;
    border: 1px solid rgba(128,128,128,0.18);
    background: rgba(99,102,241,0.045);
}


/* Buttons */

div[data-testid="stButton"] > button {
    border-radius: 14px;
    border: 1px solid rgba(99,102,241,0.35);
    text-align: left;
    padding: 12px 14px;
    height: 100%;
    transition: border-color .15s, background .15s;
}

div[data-testid="stButton"] > button:hover {
    border-color: #4F46E5;
    background: rgba(99,102,241,0.09);
}


/* Sidebar */

[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.2);
}

.cd-side-title {
    font-size: 1.35rem;
    font-weight: 800;
    margin-bottom: 0;
}

.cd-side-sub {
    color: #6B7280;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}

.cd-stat {
    background: rgba(99,102,241,0.08);
    border-radius: 14px;
    padding: 12px 16px;
    margin-top: 6px;
}

.cd-stat b {
    font-size: 1.6rem;
    font-family: 'Bricolage Grotesque', sans-serif;
}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Session state
# --------------------------------------------------

defaults = {
    "messages": [],
    "pending": None,
    "graph": None,
    "doc_key": None,
    "doc_names": [],
    "n_chunks": 0,
    "failed_key": None,
    "upload_error": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# --------------------------------------------------
# Daily limit
# --------------------------------------------------

daily_left = max(
    DAILY_LIMIT - daily_used(),
    0,
)

daily_limit_reached = daily_left == 0


# --------------------------------------------------
# Reset document
# --------------------------------------------------

def reset_document():
    st.session_state.graph = None
    st.session_state.doc_key = None
    st.session_state.doc_names = []
    st.session_state.n_chunks = 0
    st.session_state.failed_key = None
    st.session_state.upload_error = None
    st.session_state.messages = []
    st.session_state.pending = None


# --------------------------------------------------
# Format source pages
# --------------------------------------------------

def format_sources(sources) -> str:
    """
    Example:

    [
        ['a.pdf', 12],
        ['a.pdf', 15]
    ]

    becomes:

    a.pdf — pages 12, 15
    """

    by_file = {}

    for name, page in sources:
        by_file.setdefault(name, []).append(page)

    parts = []

    for name, pages in by_file.items():
        pages = sorted(set(pages))

        label = "page" if len(pages) == 1 else "pages"

        parts.append(
            f"{name} — {label} {', '.join(str(p) for p in pages)}"
        )

    return " · ".join(parts)


# NOTE ABOUT HTML BELOW:
# Every st.markdown(... unsafe_allow_html=True) block is written as ONE
# line of joined strings, with no indentation and no blank lines.
# Markdown turns lines indented by 4+ spaces into a code block, which
# would show the raw HTML text instead of rendering it.


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.markdown(
        '<p class="cd-side-title">DocChat AI</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="cd-side-sub">'
        'Upload a PDF. Ask anything. Get answers with page references.'
        '</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cd-stat">Questions remaining today<br>'
        f'<b>{daily_left}</b> / {DAILY_LIMIT}</div>',
        unsafe_allow_html=True,
    )

    st.progress(
        daily_left / DAILY_LIMIT
    )

    st.caption(
        "Daily demo limit is shared across all visitors."
    )

    st.caption(
        f"Questions are limited to {MAX_QUESTION_LENGTH} characters."
    )

    st.write("")

    if st.button(
        "🧹 Clear chat",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.pending = None
        st.rerun()

    st.divider()

    st.caption(
        "Your PDF is split into chunks, converted to embeddings and "
        "stored in a FAISS index. For each question, DocChat AI "
        "retrieves the most relevant passages and a LangGraph workflow "
        "asks the LLM to answer using only those passages."
    )


# --------------------------------------------------
# Header
# --------------------------------------------------

chip = (
    "📄 " + html.escape(", ".join(st.session_state.doc_names))
    if st.session_state.graph is not None
    else "No document uploaded yet"
)

st.markdown(
    '<div class="cd-hero">'
    '<p class="cd-title">DocChat AI</p>'
    '<p class="cd-sub">AI-powered PDF assistant. Upload any document '
    'and get answers with page references in seconds.</p>'
    f'<span class="cd-chip">{chip}</span>'
    '</div>',
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Upload + document processing
# --------------------------------------------------

st.markdown("#### Upload your PDF")

uploaded = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"],
    accept_multiple_files=False,   # demo: one PDF at a time
    label_visibility="collapsed",
    help=f"Text-based PDF only, up to 50 pages and {MAX_FILE_MB} MB.",
)

files = [uploaded] if uploaded else []

key = (
    tuple((f.name, f.size) for f in files)
    if files
    else None
)


# --------------------------------------------------
# Process uploaded documents
# --------------------------------------------------

if key is None:

    # Nothing uploaded
    if (
        st.session_state.doc_key is not None
        or st.session_state.failed_key is not None
    ):
        reset_document()


elif (
    key != st.session_state.doc_key
    and key != st.session_state.failed_key
):

    # New or changed upload
    reset_document()

    try:

        with st.spinner(
            "Reading your PDF and building the search index. "
            "Large files can take a minute..."
        ):

            for f in files:
                if f.size > MAX_FILE_MB * 1024 * 1024:
                    raise DocumentError(
                        f"'{f.name}' is larger than {MAX_FILE_MB} MB. "
                        "Please upload a smaller PDF."
                    )

            payload = [
                (f.name, f.getvalue())
                for f in files
            ]

            vectorstore, n_chunks = build_vectorstore(
                payload
            )

            st.session_state.graph = build_graph(
                vectorstore
            )

        st.session_state.doc_key = key

        st.session_state.doc_names = [
            f.name for f in files
        ]

        st.session_state.n_chunks = n_chunks

    except DocumentError as e:

        st.session_state.failed_key = key
        st.session_state.upload_error = str(e)

    except Exception:

        st.session_state.failed_key = key

        st.session_state.upload_error = (
            "Something went wrong while processing your PDF. "
            "Please try again or use a different file."
        )


# --------------------------------------------------
# Document status
# --------------------------------------------------

doc_ready = (
    st.session_state.graph is not None
    and key == st.session_state.doc_key
)


if (
    key is not None
    and key == st.session_state.failed_key
):

    st.error(
        st.session_state.upload_error
    )


if doc_ready:

    rows = "".join(
        f'<div class="cd-doc-row">📄 {html.escape(n)}</div>'
        for n in st.session_state.doc_names
    )

    st.markdown(
        '<div class="cd-doc">'
        f'{rows}'
        '<div class="cd-doc-status">'
        '✓ Document processed successfully. Ready to chat.'
        '</div>'
        '<div class="cd-doc-meta">'
        f'{st.session_state.n_chunks} searchable sections indexed'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

elif key is None:

    st.info(
        "Upload a PDF above to get started. "
        "You can ask questions as soon as it's processed."
    )


# --------------------------------------------------
# Daily limit warning
# --------------------------------------------------

if doc_ready and daily_limit_reached:

    st.warning(
        "The demo has reached its daily limit of "
        f"{DAILY_LIMIT} questions. "
        "Please try again tomorrow."
    )


# --------------------------------------------------
# Starter questions
# --------------------------------------------------

if (
    doc_ready
    and not st.session_state.messages
):

    st.markdown("#### Try asking")

    cols = st.columns(2)

    for i, text in enumerate(STARTERS):

        if cols[i % 2].button(
            f"💬  {text}",
            key=f"starter_{i}",
            use_container_width=True,
            disabled=daily_limit_reached,
        ):

            st.session_state.pending = text
            st.rerun()


# --------------------------------------------------
# Chat history
# --------------------------------------------------

if doc_ready:

    st.markdown(
        "#### Ask questions about your document"
    )


for msg in st.session_state.messages:

    avatar = (
        "🧑‍🎓"
        if msg["role"] == "user"
        else "🎓"
    )

    with st.chat_message(
        msg["role"],
        avatar=avatar,
    ):

        st.markdown(
            msg["content"]
        )

        if (
            msg["role"] == "assistant"
            and msg.get("sources")
        ):

            st.markdown(
                '<span class="cd-sources">Sources: '
                f'{html.escape(format_sources(msg["sources"]))}'
                '</span>',
                unsafe_allow_html=True,
            )


# --------------------------------------------------
# Chat input
# --------------------------------------------------

if not doc_ready:

    placeholder = "Upload a PDF first"

elif daily_limit_reached:

    placeholder = "Daily question limit reached"

else:

    placeholder = (
        "Ask a question about your document "
        f"(max {MAX_QUESTION_LENGTH} characters)..."
    )


typed = st.chat_input(
    placeholder,
    disabled=(
        not doc_ready
        or daily_limit_reached
    ),
    max_chars=MAX_QUESTION_LENGTH,
)


# Starter button question OR typed question
question = (
    st.session_state.pending
    or typed
)

st.session_state.pending = None


# --------------------------------------------------
# Handle new question
# --------------------------------------------------

if (
    question
    and doc_ready
    and not daily_limit_reached
):

    # ----------------------------------------------
    # Check question length BEFORE using the LLM
    # (backup check; the chat box also enforces it)
    # ----------------------------------------------

    if len(question) > MAX_QUESTION_LENGTH:

        st.warning(
            f"Please keep your question under "
            f"{MAX_QUESTION_LENGTH} characters. "
            f"Your question has {len(question)} characters."
        )

        st.stop()


    # ----------------------------------------------
    # Re-check daily limit immediately before
    # using the LLM.
    #
    # This protects against two visitors using
    # the final available slot at the same time.
    # ----------------------------------------------

    if not reserve_daily_slot():

        st.warning(
            "The demo has just reached its daily limit of "
            f"{DAILY_LIMIT} questions. "
            "Please try again tomorrow."
        )

        st.stop()


    # ----------------------------------------------
    # Add user message
    # ----------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )


    with st.chat_message(
        "user",
        avatar="🧑‍🎓",
    ):

        st.markdown(question)


    # ----------------------------------------------
    # Generate answer
    # ----------------------------------------------

    with st.chat_message(
        "assistant",
        avatar="🎓",
    ):

        try:

            with st.spinner(
                "Searching your document..."
            ):

                result = (
                    st.session_state.graph.invoke(
                        {
                            "question": question,
                            "context": "",
                            "sources": [],
                            "answer": "",
                        }
                    )
                )


            reply = {
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get(
                    "sources",
                    [],
                ),
            }


            st.session_state.messages.append(
                reply
            )


            # Refresh UI so the daily counter updates
            st.rerun()


        except Exception:

            st.error(
                "I couldn't get an answer right now. "
                "This is usually a temporary API issue "
                "or a rate limit. Please wait a moment "
                "and try again."
            )