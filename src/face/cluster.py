"""
Face clustering module for PhotoSense-AI.

Uses DBSCAN for unsupervised clustering of face embeddings.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances

from src.face.encode import FaceEncoder

logger = logging.getLogger(__name__)


class FaceClusterer:
    """Face clusterer using DBSCAN."""

    def __init__(self, eps: float = 0.5, min_samples: int = 3):
        """
        Initialize DBSCAN clusterer.

        Args:
            eps: Maximum distance between samples in the same cluster
            min_samples: Minimum number of samples in a cluster
        """
        self.eps = eps
        self.min_samples = min_samples
        self.encoder = FaceEncoder()  # For loading embeddings
        logger.info(f"FaceClusterer initialized (eps={eps}, min_samples={min_samples})")

    def load_embeddings(
        self,
        face_records: List[Dict]
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Load embeddings for face records.

        Args:
            face_records: List of face record dictionaries

        Returns:
            Tuple of (embeddings array, face_ids list)
        """
        embeddings = []
        face_ids = []

        for face_record in face_records:
            embedding_path = face_record.get('embedding_path')
            face_id = face_record['id']

            if not embedding_path:
                logger.warning(f"Face {face_id} has no embedding path, skipping")
                continue

            try:
                embedding = self.encoder.load_embedding(embedding_path)
                if embedding is not None:
                    embeddings.append(embedding)
                    face_ids.append(face_id)
                else:
                    logger.warning(f"Failed to load embedding for face {face_id}")
            except Exception as e:
                logger.error(f"Error loading embedding for face {face_id}: {e}")

        if not embeddings:
            return np.array([]), []

        return np.array(embeddings), face_ids

    def cluster(
        self,
        embeddings: np.ndarray,
        metric: str = 'cosine'
    ) -> np.ndarray:
        """
        Cluster face embeddings using DBSCAN.

        Args:
            embeddings: Array of face embeddings (N x embedding_dim)
            metric: Distance metric ('cosine' or 'euclidean')

        Returns:
            Array of cluster labels (-1 for noise/outliers)
        """
        if len(embeddings) == 0:
            logger.warning("No embeddings provided for clustering")
            return np.array([])

        if len(embeddings) < self.min_samples:
            logger.warning(
                f"Not enough embeddings ({len(embeddings)}) for clustering "
                f"(min_samples={self.min_samples})"
            )
            # Assign all to noise
            return np.full(len(embeddings), -1)

        # Initialize DBSCAN
        # For cosine distance, we use 'precomputed' with cosine_distances
        if metric == 'cosine':
            # Compute pairwise cosine distances
            distance_matrix = cosine_distances(embeddings)
            clusterer = DBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
                metric='precomputed'
            )
            labels = clusterer.fit_predict(distance_matrix)
        else:
            # Use euclidean distance (default)
            clusterer = DBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
                metric=metric
            )
            labels = clusterer.fit_predict(embeddings)

        # Log clustering results
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        logger.info(
            f"Clustering complete: {n_clusters} clusters, {n_noise} noise points, "
            f"{len(embeddings)} total faces"
        )

        return labels

    def get_cluster_stats(self, labels: np.ndarray) -> Dict:
        """
        Get statistics about clustering results.

        Args:
            labels: Array of cluster labels

        Returns:
            Dictionary with clustering statistics
        """
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        cluster_sizes = {}
        for label in unique_labels:
            if label != -1:
                cluster_sizes[label] = list(labels).count(label)

        return {
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'n_total': len(labels),
            'cluster_sizes': cluster_sizes
        }
