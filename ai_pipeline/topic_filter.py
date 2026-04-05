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

        print(f"  [TopicFilter] Checking relevance against topic: \"{self._topic_text}\"")
        print(f"  [TopicFilter] Doubt text: \"{text}\"")

        # Basic keyword fallback for obvious relevance
        topic_words = set(self._topic_text.lower().replace("&", " ").replace(",", " ").split())
        # Remove small stop words from topic for matching
        topic_words = {w for w in topic_words if len(w) > 3}
        
        doubt_words = set(text.lower().split())
        overlap = topic_words.intersection(doubt_words)
        
        if overlap:
            print(f"  [TopicFilter] Keyword overlap found: {overlap}. Forcing relevance.")
            return TopicResult(is_relevant=True, similarity=1.0, topic=self._topic_text)

        # Special case: if topic is the generic default, allow everything (except toxicity which is handled elsewhere)
        is_generic_topic = self._topic_text.lower() == "a classroom lecture about a specific academic subject"
        if is_generic_topic:
            print(f"  [TopicFilter] Using generic topic. Allowing doubt.")
            return TopicResult(is_relevant=True, similarity=1.0, topic=self._topic_text)

        effective_threshold = config.TOPIC_SIMILARITY_THRESHOLD

        doubt_embedding = self._model.encode(
            text, normalize_embeddings=True
        )

        # Cosine similarity (both normalized, so dot product = cosine)
        similarity = float(np.dot(doubt_embedding, self._topic_embedding))
        print(f"  [TopicFilter] Similarity: {similarity:.4f} (threshold: {effective_threshold})")

        return TopicResult(
            is_relevant=similarity >= effective_threshold,
            similarity=similarity,
            topic=self._topic_text,
        )
