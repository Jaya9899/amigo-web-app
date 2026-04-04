"""
Module 3: Embedding Engine + FAISS Vector Store

Generates embeddings using sentence-transformers and stores
them in a FAISS index for fast similarity search.
"""

from dataclasses import dataclass, field
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from . import config


@dataclass
class SimilarDoubt:
    """A similar doubt found via FAISS search."""
    doubt_id: int
    text: str
    distance: float


class EmbeddingEngine:
    """
    Manages doubt embeddings + FAISS index.
    
    - add_doubt(text) → stores embedding, returns ID
    - find_similar(text, top_k) → returns nearest neighbors
    - get_all_embeddings() → returns all stored embeddings (for clustering)
    """

    def __init__(self, model: SentenceTransformer = None):
        if model is not None:
            self._model = model
        else:
            print("  [EmbeddingEngine] Loading embedding model...")
            self._model = SentenceTransformer(config.EMBEDDING_MODEL)
            print("  [EmbeddingEngine] Ready.")

        # FAISS index (L2 distance)
        self._index = faiss.IndexFlatL2(config.EMBEDDING_DIM)

        # Storage for doubt texts (indexed by ID)
        self._doubts: list[str] = []
        self._embeddings: list[np.ndarray] = []

    @property
    def count(self) -> int:
        """Number of doubts stored."""
        return len(self._doubts)

    def add_doubt(self, text: str) -> int:
        """
        Generate embedding for a doubt, store it, and return the doubt ID.
        """
        embedding = self._model.encode(
            text, normalize_embeddings=True
        ).astype(np.float32)

        doubt_id = len(self._doubts)
        self._doubts.append(text)
        self._embeddings.append(embedding)

        # Add to FAISS (expects 2D array)
        self._index.add(embedding.reshape(1, -1))

        return doubt_id

    def find_similar(self, text: str, top_k: int = 5) -> list[SimilarDoubt]:
        """
        Find the top_k most similar doubts to the given text.
        """
        if self._index.ntotal == 0:
            return []

        embedding = self._model.encode(
            text, normalize_embeddings=True
        ).astype(np.float32)

        k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(embedding.reshape(1, -1), k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self._doubts):
                results.append(SimilarDoubt(
                    doubt_id=int(idx),
                    text=self._doubts[idx],
                    distance=float(dist),
                ))
        return results

    def get_all_embeddings(self) -> np.ndarray:
        """Return all stored embeddings as a 2D numpy array."""
        if not self._embeddings:
            return np.array([]).reshape(0, config.EMBEDDING_DIM)
        return np.vstack(self._embeddings)

    def get_doubt_text(self, doubt_id: int) -> str:
        """Get the text for a given doubt ID."""
        if 0 <= doubt_id < len(self._doubts):
            return self._doubts[doubt_id]
        return ""

    def get_all_doubts(self) -> list[str]:
        """Get all stored doubt texts."""
        return list(self._doubts)

    def reset(self):
        """Clear all stored doubts and reset the index."""
        self._doubts.clear()
        self._embeddings.clear()
        self._index = faiss.IndexFlatL2(config.EMBEDDING_DIM)
