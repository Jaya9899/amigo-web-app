"""
Central configuration for the AI doubt moderation pipeline.
All model names, thresholds, and settings live here.
"""

# ─── Embedding Model ───
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # ~80MB, fast, good quality
EMBEDDING_DIM = 384  # output dimension of all-MiniLM-L6-v2

# ─── Moderation Model ───
MODERATION_MODEL = "unitary/toxic-bert"  # toxicity classifier
TOXICITY_THRESHOLD = 0.5  # above this = toxic

# ─── Spam Detection ───
MIN_DOUBT_LENGTH = 5  # chars — anything shorter is spam
MAX_REPEAT_RATIO = 0.6  # if >60% of chars are the same char → spam
MAX_CAPS_RATIO = 0.8  # if >80% uppercase → likely spam/shouting

# ─── Topic Relevance ───
TOPIC_SIMILARITY_THRESHOLD = 0.20  # cosine similarity cutoff (lower = more lenient)

# ─── Clustering (DBSCAN) ───
DBSCAN_EPS = 0.45  # max distance between two samples in same cluster
DBSCAN_MIN_SAMPLES = 2  # minimum points to form a cluster

# ─── Summarization Model ───
SUMMARIZER_MODEL = "t5-small"  # ~242MB, lightweight
SUMMARIZER_MAX_LENGTH = 80
SUMMARIZER_MIN_LENGTH = 10
