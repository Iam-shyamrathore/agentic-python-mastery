# 📚 Topic 09: RAG, Embeddings & Vector DBs for AI Engineers

> **Master Retrieval-Augmented Generation (RAG), text chunking, dense vector representations, ChromaDB indexing, and grounded context synthesis.**

---

## 🎯 Why RAG is the Dominant Pattern in Production AI

LLMs possess general world knowledge, but they:
1. Suffer from hallucinations when unsure
2. Lack access to private corporate manuals, user records, and real-time updates
3. Cannot ingest gigabytes of data all at once without blowing up token budgets and latency

**RAG (Retrieval-Augmented Generation)** retrieves only the top 3-5 most mathematically relevant snippets and passes them to the LLM at inference time.

---

## 📖 Complete Zero-to-100 Theory & Reference

### 1. The RAG Pipeline Architecture

```
[Document Corpus]
       │
       ▼
[Chunking: 500 chars, 50 overlap]
       │
       ▼
[Embedding Model: text ─► vector]
       │
       ▼
[ChromaDB Vector Store]
       │
       ▲ (Cosine Similarity Search)
       │
[User Query: "How does refund work?"]
       │
       ▼
[Retrieved Context Chunks] ──► [LLM System Prompt] ──► [Grounded Answer + Citations]
```

---

### 2. Text Chunking with Overlap

If you split text strictly on paragraph boundaries, sentences bridging two chunks lose meaning. Overlap ensures context continuity:

$$\text{Chunk } i: [t_0 \dots t_{500}]$$
$$\text{Chunk } i+1: [t_{450} \dots t_{950}]$$

---

### 3. ChromaDB Vector Store Operations

```python
import chromadb

# Ephemeral client for testing or persistent on disk
client = chromadb.Client()
collection = client.get_or_create_collection(name="ai_docs")

# Adding documents (Chroma handles default all-MiniLM embeddings automatically!)
collection.add(
    documents=["RAG combines retrieval with generative LLMs.", "LangGraph enables cyclic agent workflows."],
    metadatas=[{"source": "rag_intro.md"}, {"source": "agents.md"}],
    ids=["doc1", "doc2"]
)

# Semantic similarity search
results = collection.query(
    query_texts=["What framework should I use for cyclic agent state?"],
    n_results=1
)
print(results["documents"][0])
```

---

## 🛠️ The Hands-on Project: Document Q&A Application

In this module, you will build `starter/rag_app.py`:
- Recursive text chunker with configurable overlap
- ChromaDB collection ingestion with metadata
- Top-$K$ semantic similarity retrieval
- Grounded answer synthesis referencing retrieved document IDs
- Automated test coverage

### Running the Tests
```bash
pytest 09-rag-embeddings-vector-dbs/tests/test_rag.py -v
```
