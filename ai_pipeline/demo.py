"""
Demo Script - AI Doubt Moderation Pipeline

Simulates a DBMS Normalization classroom session with
sample doubts (including duplicates, spam, off-topic, and abuse).
Shows the full pipeline in action.

Usage:
    cd "se project/se project"
    python -m ai_pipeline.demo
"""

import sys
import os
import io

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_pipeline.pipeline import DoubtPipeline


def main():
    # --- Session Setup ---
    SESSION_TOPIC = "DBMS Normalization - 1NF, 2NF, 3NF, BCNF"

    # --- Sample Doubts ---
    # Mix of: valid (some duplicates), off-topic, spam, abusive
    SAMPLE_DOUBTS = [
        # Valid - Normalization questions (with duplicates)
        "What is Second Normal Form (2NF)?",
        "Can you explain 2NF with an example?",
        "2NF meaning??",
        "What is the difference between 2NF and 3NF?",
        "How is 3NF different from BCNF?",
        "Explain 3NF vs BCNF with example",
        "What is 1NF? What are the rules?",
        "Explain first normal form",
        "Why do we need normalization in databases?",
        "What is the purpose of normalization?",
        "Can a table be in 2NF but not 3NF? Give an example.",

        # Off-topic
        "What is photosynthesis?",
        "How to make pasta at home?",
        "Who won the IPL last year?",

        # Spam
        "aaaaaaaaaaaaaaa",
        "hi",
        "???",
        "asdfghjklqwerty",

        # Abusive
        "This class is stupid and you're an idiot",
        "I hate this damn subject so much",
    ]

    # --- Run Pipeline ---
    pipeline = DoubtPipeline()
    pipeline.set_topic(SESSION_TOPIC)

    print("=" * 60)
    print("  SUBMITTING DOUBTS")
    print("=" * 60)

    for i, doubt in enumerate(SAMPLE_DOUBTS, 1):
        result = pipeline.submit_doubt(doubt)

        status = "[ACCEPTED]" if result.accepted else "[REJECTED]"
        print(f"\n  [{i:2d}] {status}")
        print(f'       "{doubt}"')

        if not result.accepted:
            print(f"       Reason: {result.rejection_reason}")
        else:
            if result.topic_result:
                print(f"       Topic similarity: {result.topic_result.similarity:.2f}")

    # --- Get Results ---
    print("\n")
    print("=" * 60)
    print("  PIPELINE RESULTS")
    print("=" * 60)

    output = pipeline.get_clustered_summary()

    print(f"\n  Total submitted:  {output.total_accepted + output.total_rejected}")
    print(f"  Accepted:         {output.total_accepted}")
    print(f"  Rejected:         {output.total_rejected}")
    print(f"  Clusters found:   {len(output.clusters)}")
    print(f"  Unclustered:      {len(output.unclustered)}")

    # --- Show Clusters ---
    print("\n")
    print("=" * 60)
    print("  CLUSTERED DOUBTS (grouped + summarized)")
    print("=" * 60)

    for cluster in output.clusters:
        print(f"\n  +-- Cluster #{cluster.cluster_id + 1}  ({cluster.count} students)")
        print(f"  |")
        for doubt in cluster.doubts:
            print(f'  |  * "{doubt}"')
        print(f"  |")
        print(f'  |  Summary: "{cluster.summary}"')
        print(f"  +--------------------------------------")

    if output.unclustered:
        print(f"\n  Unique doubts (no cluster):")
        for doubt in output.unclustered:
            print(f'     * "{doubt}"')

    print("\n" + "=" * 60)
    print("  Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
