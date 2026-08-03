import json
import os
import re
import threading
import traceback
from collections import OrderedDict

import faiss
import numpy as np
from fastembed import TextEmbedding
from groq import Groq

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

MAX_RESUMES_IN_MEMORY = 50
INDEX_DIR = os.environ.get("RESUME_INDEX_DIR", "resume_indexes")

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
LLM_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

CHUNK_WORDS = 90
CHUNK_OVERLAP = 30
TOP_K = 5
MIN_SCORE = 0.28         

os.makedirs(INDEX_DIR, exist_ok=True)

_lock = threading.RLock()
_embedder = None
_groq = None

_cache = OrderedDict()   


class RagError(Exception):
    """Raised for conditions the caller should surface to the user."""

def get_embedder():
    global _embedder
    with _lock:
        if _embedder is None:
            _embedder = TextEmbedding(model_name=EMBED_MODEL)
    return _embedder


def get_groq_client():
    global _groq
    with _lock:
        if _groq is None:
            key = os.environ.get("GROQ_API_KEY")
            if not key:
                raise RagError("GROQ_API_KEY is not set on the server.")
            _groq = Groq(api_key=key)
    return _groq

def clean_text(text):
    return re.sub(r"[ \t]+", " ", (text or "")).strip()


def chunk_text(text, chunk_size=CHUNK_WORDS, overlap=CHUNK_OVERLAP):

    words = clean_text(text.replace("\n", " \n ")).split()
    if not words:
        return []

    step = max(1, chunk_size - overlap)
    chunks = []

    for start in range(0, len(words), step):
        window = words[start:start + chunk_size]
        if not window:
            break
        chunk = " ".join(w for w in window if w != "\n").strip()
        if len(chunk.split()) >= 8:       
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break

    return chunks

def _safe_id(resume_id):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(resume_id))[:120]


def _paths(resume_id):
    stem = os.path.join(INDEX_DIR, _safe_id(resume_id))
    return f"{stem}.faiss", f"{stem}.json"


def _save_to_disk(resume_id, index, chunks):
    idx_path, meta_path = _paths(resume_id)
    faiss.write_index(index, idx_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"model": EMBED_MODEL, "chunks": chunks}, f)


def _load_from_disk(resume_id):
    idx_path, meta_path = _paths(resume_id)
    if not (os.path.exists(idx_path) and os.path.exists(meta_path)):
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        # An index built by a different embedder has incompatible dimensions.
        if meta.get("model") != EMBED_MODEL:
            return None
        return {"index": faiss.read_index(idx_path), "chunks": meta["chunks"]}
    except Exception:
        traceback.print_exc()
        return None


def _remember(resume_id, entry):
    with _lock:
        _cache.pop(resume_id, None)
        while len(_cache) >= MAX_RESUMES_IN_MEMORY:
            _cache.popitem(last=False)
        _cache[resume_id] = entry


# --------------------------------------------------------------------------
# Indexing
# --------------------------------------------------------------------------

def create_resume_index(resume_id, resume_text):

    chunks = chunk_text(resume_text)
    if not chunks:
        print(f"[rag] no usable text extracted for {resume_id}")
        return False

    vectors = np.array(list(get_embedder().embed(chunks)), dtype=np.float32)
    if vectors.size == 0:
        return False

    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    entry = {"index": index, "chunks": chunks}
    _remember(resume_id, entry)

    try:
        _save_to_disk(resume_id, index, chunks)
    except Exception:
        # Losing persistence is survivable; the in-memory copy still works.
        traceback.print_exc()

    print(f"[rag] indexed {resume_id}: {len(chunks)} chunks, dim {vectors.shape[1]}")
    return True


def get_resume(resume_id):

    with _lock:
        if resume_id in _cache:
            _cache.move_to_end(resume_id)
            return _cache[resume_id]

    entry = _load_from_disk(resume_id)
    if entry:
        _remember(resume_id, entry)
    return entry


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------

def search_resume(resume_id, question, top_k=TOP_K, min_score=MIN_SCORE):
    entry = get_resume(resume_id)
    if not entry:
        raise RagError(
            "This resume is not indexed. Re-run the analysis to rebuild it."
        )

    index, chunks = entry["index"], entry["chunks"]
    if index.ntotal == 0:
        raise RagError("This resume was indexed but contains no text.")

    # query_embed applies the retrieval instruction prefix BGE models expect.
    embedder = get_embedder()
    if hasattr(embedder, "query_embed"):
        q = list(embedder.query_embed([question]))
    else:
        q = list(embedder.embed([question]))

    q = np.array(q, dtype=np.float32)
    faiss.normalize_L2(q)

    k = min(top_k, index.ntotal)
    scores, ids = index.search(q, k)

    hits = []
    for score, idx in zip(scores[0], ids[0]):
        if idx == -1:
            continue
        if float(score) < min_score:
            continue
        hits.append({"text": chunks[int(idx)], "score": float(score)})

    # The opening chunk holds the name, title, and summary, which many
    # questions need but which rarely scores highly on its own.
    if chunks and all(h["text"] != chunks[0] for h in hits):
        hits.append({"text": chunks[0], "score": 0.0, "header": True})

    return hits


# --------------------------------------------------------------------------
# Answering
# --------------------------------------------------------------------------

PROMPT = """You are reading one candidate's resume on behalf of a recruiter.

Answer the question using only the resume excerpts below.

Rules:
- Use only what the excerpts state. Never infer or invent employers, dates,
  or skills that are not written there.
- For skills questions, answer with a comma-separated list.
- For experience questions, give the years and the roles they belong to.
- If the excerpts do not contain the answer, reply exactly: Not stated in this resume
- Answer in at most four sentences, or a short list. No preamble.

RESUME EXCERPTS:
{context}

QUESTION:
{question}

ANSWER:"""


def llm_generate(prompt, model=None, max_tokens=400):
    client = get_groq_client()
    response = client.chat.completions.create(
        model=model or LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def answer_question(resume_id, question):

    question = clean_text(question)
    if not question:
        return {"answer": "Ask a question about this resume.",
                "sources": [], "status": "no_match"}

    try:
        hits = search_resume(resume_id, question)
    except RagError as e:
        return {"answer": str(e), "sources": [], "status": "not_indexed"}

    if not hits:
        return {
            "answer": "Nothing in this resume relates to that question.",
            "sources": [],
            "status": "no_match",
        }

    context = "\n---\n".join(h["text"] for h in hits)

    try:
        answer = llm_generate(PROMPT.format(context=context, question=question))
    except RagError as e:
        return {"answer": str(e), "sources": [], "status": "llm_error"}
    except Exception:
        traceback.print_exc()
        return {
            "answer": "The language model did not respond. Check the server logs.",
            "sources": [],
            "status": "llm_error",
        }

    if not answer:
        answer = "Not stated in this resume"

    return {
        "answer": answer,
        "sources": [h["text"] for h in hits],
        "status": "ok",
    }