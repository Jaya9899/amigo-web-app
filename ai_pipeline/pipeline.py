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
    source: str = "live"  # "live" or "dashboard"
    doubt_id: int | None = None
    rejection_reason: str = ""
    mod_result: ModResult | None = None
    topic_result: TopicResult | None = None
    file_url: str | None = None
    link: str | None = None
    status: str = "pending"  # "pending" or "resolved"
    resolution_text: str | None = None
    resolution_file_url: str | None = None
    resolution_audio_url: str | None = None


@dataclass
class ClusterSummary:
    """A clustered and summarized group of doubts."""
    cluster_id: int
    doubts: list[dict]  # Changed from list[str] to list[dict] to store text + extras
    count: int
    summary: str


@dataclass
class PipelineOutput:
    """Full output of the clustering + summarization step."""
    clusters: list[ClusterSummary]
    unclustered: list[dict]  # Changed from list[str] to list[dict]
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

    def resolve_doubt(self, doubt_text: str, res_text: str = None, res_file: str = None, res_audio: str = None):
        """Mark a doubt as resolved and store the teacher's response."""
        for sub in self._submissions:
            if sub.text == doubt_text:
                sub.status = "resolved"
                sub.resolution_text = res_text
                sub.resolution_file_url = res_file
                sub.resolution_audio_url = res_audio
                print(f"[RESOLVE] Doubt \"{doubt_text[:30]}...\" resolved.")
                return True
        return False

    def submit_doubt(self, text: str, file_url: str = None, link: str = None, source: str = "live") -> DoubtSubmission:
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
                source=source,
                rejection_reason=f"[{mod_result.label}] {mod_result.reason}",
                mod_result=mod_result,
                file_url=file_url,
                link=link
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
                source=source,
                rejection_reason=f"Off-topic for \"{topic_result.topic}\" (similarity: {topic_result.similarity:.2f})",
                topic_result=topic_result,
                file_url=file_url,
                link=link
            )
            self._submissions.append(sub)
            return sub

        # Step 3: Store in FAISS
        doubt_id = self._engine.add_doubt(text)
        self._accepted_count += 1

        sub = DoubtSubmission(
            text=text,
            accepted=True,
            source=source,
            doubt_id=doubt_id,
            mod_result=mod_result,
            topic_result=topic_result,
            file_url=file_url,
            link=link
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

        # Map to quickly find submission details by text
        # (Using text as key for simplicity since engine stores text, 
        # but in production you'd use a stable ID)
        sub_map = { s.text: s for s in self._submissions if s.accepted }

        for cid, doubt_ids in cluster_result.clusters.items():
            doubt_texts = [self._engine.get_doubt_text(did) for did in doubt_ids]
            summary = self._summarizer.summarize_cluster(doubt_texts)
            
            # Enrich with original submission details
            enriched_doubts = []
            for dt in doubt_texts:
                s = sub_map.get(dt)
                enriched_doubts.append({
                    "text": dt,
                    "file_url": s.file_url if s else None,
                    "link": s.link if s else None,
                    "status": s.status if s else "pending",
                    "resolution_text": s.resolution_text if s else None,
                    "resolution_file_url": s.resolution_file_url if s else None,
                    "resolution_audio_url": s.resolution_audio_url if s else None
                })

            cluster_summaries.append(ClusterSummary(
                cluster_id=cid,
                doubts=enriched_doubts,
                count=len(enriched_doubts),
                summary=summary,
            ))

        # Sort by cluster size (biggest first)
        cluster_summaries.sort(key=lambda c: c.count, reverse=True)

        # Unclustered (noise) doubts
        unclustered = []
        for did in cluster_result.noise:
            dt = self._engine.get_doubt_text(did)
            s = sub_map.get(dt)
            unclustered.append({
                "text": dt,
                "file_url": s.file_url if s else None,
                "link": s.link if s else None,
                "status": s.status if s else "pending",
                "resolution_text": s.resolution_text if s else None,
                "resolution_file_url": s.resolution_file_url if s else None,
                "resolution_audio_url": s.resolution_audio_url if s else None
            })

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
