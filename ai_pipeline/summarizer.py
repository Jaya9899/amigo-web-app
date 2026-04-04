"""
Module 5: Summarization

For each cluster of similar doubts, generates a single
clean, representative question using T5.
"""

from transformers import pipeline as hf_pipeline
from . import config


class DoubtSummarizer:
    """
    Summarizes a cluster of similar doubts into one clean question.
    Uses T5-small for lightweight, fast summarization.
    """

    def __init__(self):
        print("  [Summarizer] Loading T5 model...")
        self._summarizer = hf_pipeline(
            "summarization",
            model=config.SUMMARIZER_MODEL,
            device=-1,  # CPU
        )
        print("  [Summarizer] Ready.")

    def summarize_cluster(self, doubts: list[str]) -> str:
        """
        Given a list of similar doubt texts, produce one summary question.
        
        Args:
            doubts: List of doubt strings in the same cluster
            
        Returns:
            A single summarized question string
        """
        if not doubts:
            return ""

        if len(doubts) == 1:
            return doubts[0]

        # Combine all doubts into one block for summarization
        combined = " | ".join(doubts)

        # T5 needs "summarize: " prefix
        if config.SUMMARIZER_MODEL.startswith("t5"):
            combined = "summarize: " + combined

        try:
            result = self._summarizer(
                combined,
                max_length=config.SUMMARIZER_MAX_LENGTH,
                min_length=config.SUMMARIZER_MIN_LENGTH,
                do_sample=False,
                truncation=True,
            )
            summary = result[0]["summary_text"].strip()

            # If summary is too short or gibberish, fall back to longest doubt
            if len(summary) < 10:
                return max(doubts, key=len)

            return summary

        except Exception as e:
            print(f"  [Summarizer] Error: {e}")
            # Fallback: return the longest doubt
            return max(doubts, key=len)
