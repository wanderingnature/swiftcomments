"""
Configuration module for lexical analysis pipeline.

Tuning knobs only. Everything project-scoped — DB connection, schema names,
filesystem paths (models/cache/logs/checkpoint/status) — comes from
shared.project_context.ProjectContext, passed explicitly by entry points.
SQL is written with {analysis}/{src} tokens and rendered per project.
"""

from typing import Dict, Any

# Processing configuration
PROCESSING_CONFIG = {
    "batch_size": 1000,
    "max_workers": 4,
    "memory_limit_gb": 16,
    "cache_enabled": True,
    "processing_version": "1.0.0"
}

# Feature extraction configuration
FEATURE_CONFIG = {
    "min_comment_length": 600,
    "max_features_tfidf": 10000,
    "ngram_range": (3, 5),  # For phrasal analysis
    "max_ngram_features": 20000,
    "embedding_model": "BAAI/bge-large-en-v1.5",
    "embedding_batch_size": 64
}

# Clustering configuration
CLUSTERING_CONFIG = {
    "pca_components": 50,
    "gmm_components": 10,
    "gmm_covariance_type": "full",
    "outlier_std_threshold": 2.0,  # Standard deviation threshold for 2-sigma outlier detection
    "random_state": 42
}

# SpaCy configuration
SPACY_CONFIG = {
    "model": "en_core_web_md",  # Medium model for balance
    "disable_pipes": ["ner", "textcat"],  # Disable unnecessary components
    "batch_size": 1000,
    "n_process": 4
}

# Logging configuration (the log FILE path is per-project: entry points pass
# ctx.logs_dir / "lexical_analysis.log" to setup_logging)
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5
}

# Corpus selection query
CORPUS_QUERY = """
    SELECT comment_id, comment_text
    FROM {analysis}.v_truly_unique_comments
    WHERE comment_length > %(min_length)s
    AND comment_text IS NOT NULL
    ORDER BY comment_id
    LIMIT %(limit)s OFFSET %(offset)s
"""


def get_config() -> Dict[str, Any]:
    """
    Get full configuration dictionary.
    """
    return {
        "processing": PROCESSING_CONFIG,
        "features": FEATURE_CONFIG,
        "clustering": CLUSTERING_CONFIG,
        "spacy": SPACY_CONFIG,
        "logging": LOGGING_CONFIG,
    }
