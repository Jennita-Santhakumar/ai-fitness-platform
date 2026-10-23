"""
ChromaDB memory store service (Day 22).

Provides a persistent vector store for user workout history, plans, and session notes.
Each user gets a separate collection (namespaced by user_id) enabling:
- Semantic similarity search across training history
- Memory-augmented LLM prompts for personalised plan generation
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_fitness.memory")

# Lazy-initialized ChromaDB client
_chroma_client = None
_COLLECTION_PREFIX = "user_memory_"


def _get_chroma_client():
    """Lazily initialise the ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        from app.core.config import settings

        persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_data")
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"ChromaDB client initialised at {persist_dir}")
    return _chroma_client


def reset_chroma_client():
    """Reset the lazy client (used in tests)."""
    global _chroma_client
    _chroma_client = None


def _collection_name(user_id: int) -> str:
    """Return the ChromaDB collection name for a given user."""
    return f"{_COLLECTION_PREFIX}{user_id}"


def get_or_create_user_collection(user_id: int):
    """
    Returns (or creates) the ChromaDB collection for the given user.
    Collections are namespaced per-user to enable isolation.
    """
    client = _get_chroma_client()
    return client.get_or_create_collection(name=_collection_name(user_id))


def add_memory(
    user_id: int,
    doc_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Upserts a single text document into the user's memory collection.

    Args:
        user_id: Owner user ID.
        doc_id:  Unique identifier for the document (e.g. "session_42", "plan_7").
        text:    Text content to embed and store.
        metadata: Optional dict of filterable metadata (e.g. {"type": "session", "date": "2026-10-20"}).
    """
    collection = get_or_create_user_collection(user_id)
    meta = metadata if metadata else {"_source": "ai_fitness"}
    collection.upsert(
        ids=[doc_id],
        documents=[text],
        metadatas=[meta],
    )
    logger.debug(f"Upserted memory doc_id={doc_id} for user_id={user_id}")


def add_memories_batch(
    user_id: int,
    doc_ids: List[str],
    texts: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Batch upsert multiple documents into the user's memory collection.
    """
    collection = get_or_create_user_collection(user_id)
    metas = metadatas or [{"_source": "ai_fitness"}] * len(doc_ids)
    # Ensure no empty dicts (ChromaDB requires non-empty metadata)
    metas = [m if m else {"_source": "ai_fitness"} for m in metas]
    collection.upsert(
        ids=doc_ids,
        documents=texts,
        metadatas=metas,
    )
    logger.debug(f"Batch upserted {len(doc_ids)} memory docs for user_id={user_id}")


def query_memory(
    user_id: int,
    query_text: str,
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Performs a semantic similarity search over the user's memory collection.

    Args:
        user_id:    Owner user ID.
        query_text: Query string to embed and search against.
        n_results:  Maximum number of results to return.
        where:      Optional ChromaDB metadata filter (e.g. {"type": "session"}).

    Returns:
        List of dicts, each with keys: "id", "document", "metadata", "distance".
    """
    collection = get_or_create_user_collection(user_id)

    # Ensure we don't query for more results than exist
    count = collection.count()
    if count == 0:
        return []
    effective_n = min(n_results, count)

    kwargs: Dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": effective_n,
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    # Flatten the nested lists returned by ChromaDB
    items = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i in range(len(ids)):
        items.append({
            "id": ids[i],
            "document": documents[i],
            "metadata": metadatas[i] if i < len(metadatas) else {},
            "distance": distances[i] if i < len(distances) else None,
        })

    return items


def delete_memory(user_id: int, doc_id: str) -> None:
    """Delete a single document from the user's memory collection."""
    collection = get_or_create_user_collection(user_id)
    collection.delete(ids=[doc_id])
    logger.debug(f"Deleted memory doc_id={doc_id} for user_id={user_id}")


def delete_user_collection(user_id: int) -> None:
    """Delete the entire memory collection for a user (e.g. on account deletion)."""
    client = _get_chroma_client()
    name = _collection_name(user_id)
    try:
        client.delete_collection(name=name)
        logger.info(f"Deleted memory collection {name}")
    except Exception:
        logger.debug(f"Collection {name} did not exist or already deleted")


def ingest_session_memory(user_id: int, session_id: int, notes: str, date_str: str) -> None:
    """
    Convenience function to ingest a workout session into memory.
    Creates a document with type=session metadata.
    """
    doc_id = f"session_{session_id}"
    text = f"Workout session on {date_str}: {notes}"
    metadata = {"type": "session", "date": date_str, "session_id": str(session_id)}
    add_memory(user_id=user_id, doc_id=doc_id, text=text, metadata=metadata)


def ingest_plan_memory(user_id: int, plan_id: int, plan_text: str) -> None:
    """
    Convenience function to ingest a generated plan into memory.
    Creates a document with type=plan metadata.
    """
    doc_id = f"plan_{plan_id}"
    metadata = {"type": "plan", "plan_id": str(plan_id)}
    add_memory(user_id=user_id, doc_id=doc_id, text=plan_text, metadata=metadata)
