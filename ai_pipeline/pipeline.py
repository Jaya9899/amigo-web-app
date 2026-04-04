"""
Full Pipeline Orchestrator

Ties all 5 modules together:
1. Moderation (spam/abuse)
2. Topic Relevance
3. Embedding + Storage
4. Clustering (DBSCAN)
5. Summarization (T5)
"""

from dataclasses import dataclass, field
from .moderation import ModerationFilter, ModResult
from .topic_filter import TopicFilter, TopicResult
from .embeddings import EmbeddingEngine
from .clustering import DoubtClusterer, ClusterResult
from .summarizer import DoubtSummarizer


@dataclass
class DoubtSubmission:
    """Result of submitting a single doubt through the pipeline."""
    text: str
    accepted: bool
    doubt_id: int | None = None
    rejection_reason: str = ""
    mod_result: ModResult | None = None
    topic_result: TopicResult | None = None


@dataclass
class ClusterSummary:
    """A clustered and summarized group of doubts."""
    cluster_id: int
    doubts: list[str]
    count: int
    summary: str


@dataclass
class PipelineOutput:
    """Full output of the clustering + summarization step."""
    clusters: list[ClusterSummary]
    unclustered: list[str]  # doubts that didn't fit any cluster
    total_accepted: int
    total_rejected: int


class DoubtPipeline:
    """
    Main pipeline class.
    
    Usage:
        pipeline = DoubtPipeline()
        pipeline.set_topic("DBMS Normalization")
        
        # Submit doubts one by one
        result = pipeline.submit_doubt("What is 2NF?")
        
        # Get clustered + summarized output
        output = pipeline.get_clustered_summary()
    """

    def __init__(self):
        print("\n--- Initializing Amigo AI Pipeline ---\n")

        self._moderator = ModerationFilter()
        self._topic_filter = TopicFilter()
        self._engine = EmbeddingEngine(model=self._topic_filter._model)
        self._clusterer = DoubtClusterer()
        self._summarizer = DoubtSummarizer()

        self._accepted_count = 0
        self._rejected_count = 0
        self._submissions: list[DoubtSubmission] = []

        print("\n[OK] Pipeline ready!\n")

    def set_topic(self, topic: str):
        """Set the session topic for relevance filtering."""
        self._topic_filter.set_topic(topic)
        print(f"[TOPIC] Session topic: \"{topic}\"\n")

    def submit_doubt(self, text: str) -> DoubtSubmission:
        """
        Process a single student doubt through the full pipeline.
        
        Steps:
        1. Moderation check (spam + toxicity)
        2. Topic relevance check
        3. Store embedding in FAISS
        
        Returns DoubtSubmission with result details.
        """
        # Step 1: Moderation
        mod_result = self._moderator.check(text)
        if not mod_result.is_clean:
            self._rejected_count += 1
            sub = DoubtSubmission(
                text=text,
                accepted=False,
                rejection_reason=f"[{mod_result.label}] {mod_result.reason}",
                mod_result=mod_result,
            )
            self._submissions.append(sub)
            return sub

        # Step 2: Topic relevance
        topic_result = self._topic_filter.check(text)
        if not topic_result.is_relevant:
            self._rejected_count += 1
            sub = DoubtSubmission(
                text=text,
                accepted=False,
                rejection_reason=f"Off-topic (similarity: {topic_result.similarity:.2f})",
                topic_result=topic_result,
            )
            self._submissions.append(sub)
            return sub

        # Step 3: Store in FAISS
        doubt_id = self._engine.add_doubt(text)
        self._accepted_count += 1

        sub = DoubtSubmission(
            text=text,
            accepted=True,
            doubt_id=doubt_id,
            mod_result=mod_result,
            topic_result=topic_result,
        )
        self._submissions.append(sub)
        return sub

    def get_clustered_summary(self) -> PipelineOutput:
        """
        Cluster all accepted doubts and generate summaries.
        
        Steps:
        4. Run DBSCAN clustering on all embeddings
        5. Summarize each cluster into one question
        
        Returns PipelineOutput with all clusters and summaries.
        """
        # Step 4: Cluster
        cluster_result = self._clusterer.cluster(self._engine)

        # Step 5: Summarize each cluster
        cluster_summaries = []

        for cid, doubt_ids in cluster_result.clusters.items():
            doubt_texts = [self._engine.get_doubt_text(did) for did in doubt_ids]
            summary = self._summarizer.summarize_cluster(doubt_texts)

            cluster_summaries.append(ClusterSummary(
                cluster_id=cid,
                doubts=doubt_texts,
                count=len(doubt_texts),
                summary=summary,
            ))

        # Sort by cluster size (biggest first)
        cluster_summaries.sort(key=lambda c: c.count, reverse=True)

        # Unclustered (noise) doubts
        unclustered = [self._engine.get_doubt_text(did) for did in cluster_result.noise]

        return PipelineOutput(
            clusters=cluster_summaries,
            unclustered=unclustered,
            total_accepted=self._accepted_count,
            total_rejected=self._rejected_count,
        )

    def reset(self):
        """Reset the pipeline for a new session."""
        self._engine.reset()
        self._accepted_count = 0
        self._rejected_count = 0
        self._submissions.clear()
