"""
Module 2: Topic Relevance Filter

Uses sentence-transformers to compute semantic similarity
between a student doubt and the current session topic.
Rejects off-topic doubts.
"""

from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer
from . import config


@dataclass
class TopicResult:
    """Result from topic relevance check."""
    is_relevant: bool
    similarity: float
    topic: str


class TopicFilter:
    """Filters doubts by semantic similarity to the session topic."""

    def __init__(self):
        print("  [TopicFilter] Loading embedding model...")
        self._model = SentenceTransformer(config.EMBEDDING_MODEL)
        self._topic_embedding = None
        self._topic_text = ""
        print("  [TopicFilter] Ready.")

    def set_topic(self, topic: str):
        """Set the current session topic. Call this at session start."""
        self._topic_text = topic
        self._topic_embedding = self._model.encode(
            topic, normalize_embeddings=True
        )

    def check(self, text: str) -> TopicResult:
        """
        Check if a doubt is relevant to the current session topic.
        Returns TopicResult with is_relevant=True if on-topic.
        """
        if self._topic_embedding is None:
            # No topic set — allow everything
            return TopicResult(is_relevant=True, similarity=1.0, topic="(none)")

        doubt_embedding = self._model.encode(
            text, normalize_embeddings=True
        )

        # Cosine similarity (both normalized, so dot product = cosine)
        similarity = float(np.dot(doubt_embedding, self._topic_embedding))

        return TopicResult(
            is_relevant=similarity >= config.TOPIC_SIMILARITY_THRESHOLD,
            similarity=similarity,
            topic=self._topic_text,
        )
