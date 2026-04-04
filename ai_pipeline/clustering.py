"""
Module 4: DBSCAN Clustering

Groups similar doubts into clusters using DBSCAN
on the stored embeddings from the EmbeddingEngine.
"""

from dataclasses import dataclass
import numpy as np
from sklearn.cluster import DBSCAN
from . import config
from .embeddings import EmbeddingEngine


@dataclass
class ClusterResult:
    """Result of clustering all stored doubts."""
    clusters: dict[int, list[int]]    # cluster_id → list of doubt_ids
    noise: list[int]                   # doubt_ids that didn't fit any cluster
    num_clusters: int


class DoubtClusterer:
    """
    Clusters doubts using DBSCAN on their embeddings.
    
    DBSCAN is chosen because:
    - Doesn't require specifying number of clusters
    - Handles noise well (lone/unique doubts)
    - Works great with embeddings
    """

    def __init__(self):
        self._dbscan = DBSCAN(
            eps=config.DBSCAN_EPS,
            min_samples=config.DBSCAN_MIN_SAMPLES,
            metric="euclidean",
        )

    def cluster(self, engine: EmbeddingEngine) -> ClusterResult:
        """
        Run DBSCAN on all embeddings in the engine.
        Returns ClusterResult with grouped doubt IDs.
        """
        embeddings = engine.get_all_embeddings()

        if embeddings.shape[0] == 0:
            return ClusterResult(clusters={}, noise=[], num_clusters=0)

        if embeddings.shape[0] == 1:
            return ClusterResult(clusters={}, noise=[0], num_clusters=0)

        # Run DBSCAN
        labels = self._dbscan.fit_predict(embeddings)

        # Group by cluster
        clusters: dict[int, list[int]] = {}
        noise: list[int] = []

        for doubt_id, label in enumerate(labels):
            if label == -1:
                noise.append(doubt_id)
            else:
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(doubt_id)

        return ClusterResult(
            clusters=clusters,
            noise=noise,
            num_clusters=len(clusters),
        )
