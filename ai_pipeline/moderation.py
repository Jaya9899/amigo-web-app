"""
Module 1: Moderation — Spam & Abuse Filter

Uses a pre-trained toxicity classifier (toxic-bert) plus
simple heuristics for spam detection.
"""

import re
from dataclasses import dataclass
from transformers import pipeline as hf_pipeline
from . import config


@dataclass
class ModResult:
    """Result from the moderation check."""
    is_clean: bool
    label: str        # "clean", "toxic", or "spam"
    confidence: float
    reason: str = ""


class ModerationFilter:
    """Filters out spam and abusive/toxic student doubts."""

    def __init__(self):
        print("  [Moderation] Loading toxic-bert model...")
        self._toxicity = hf_pipeline(
            "text-classification",
            model=config.MODERATION_MODEL,
            top_k=None,
            device=-1,  # CPU
        )
        print("  [Moderation] Ready.")

    def _check_spam(self, text: str) -> tuple[bool, str]:
        """Fast heuristic spam check before running the model."""
        stripped = text.strip()

        # Too short
        if len(stripped) < config.MIN_DOUBT_LENGTH:
            return True, "Too short to be a real doubt"

        # Repeated characters (e.g., "aaaaaaaaa" or "??????")
        if stripped:
            from collections import Counter
            counts = Counter(stripped.lower())
            most_common_count = counts.most_common(1)[0][1]
            if most_common_count / len(stripped) > config.MAX_REPEAT_RATIO:
                return True, "Repetitive characters detected"

        # Excessive caps (shouting)
        alpha_chars = [c for c in stripped if c.isalpha()]
        if alpha_chars:
            caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if caps_ratio > config.MAX_CAPS_RATIO and len(alpha_chars) > 10:
                return True, "Excessive caps / shouting"

        # Gibberish — no vowels in a long string
        if len(stripped) > 15:
            vowels = set("aeiouAEIOU")
            vowel_count = sum(1 for c in stripped if c in vowels)
            if vowel_count / len(stripped) < 0.05:
                return True, "Gibberish / no real words"

        return False, ""

    def check(self, text: str) -> ModResult:
        """
        Run moderation on a student doubt.
        Returns ModResult with is_clean=True if the doubt is acceptable.
        """
        # Step 1: Spam heuristics (fast)
        is_spam, spam_reason = self._check_spam(text)
        if is_spam:
            return ModResult(
                is_clean=False,
                label="spam",
                confidence=1.0,
                reason=spam_reason,
            )

        # Step 2: Toxicity model
        results = self._toxicity(text[:512])  # truncate to model max
        if results and isinstance(results[0], list):
            results = results[0]

        # Find the toxic label with highest score
        toxic_score = 0.0
        for r in results:
            label = r["label"].lower()
            if label == "toxic" or label == "1":
                toxic_score = r["score"]
                break

        if toxic_score > config.TOXICITY_THRESHOLD:
            return ModResult(
                is_clean=False,
                label="toxic",
                confidence=toxic_score,
                reason=f"Toxicity score: {toxic_score:.2f}",
            )

        return ModResult(
            is_clean=True,
            label="clean",
            confidence=1.0 - toxic_score,
        )
