"""Per-project artifact directories for the AI batch pipeline.

Batch artifacts are namespaced by project slug under the repo root:
batch_requests/<slug>/, analysis_results/<slug>/, batch_stats/<slug>/,
sql_batches/<slug>/, organic/<slug>/. Directories are created on first use.
"""

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class ProjectPaths:
    batch_requests: Path
    dimension_requests: Path
    analysis_results: Path
    batch_stats: Path
    sql_batches: Path
    organic: Path


def project_paths(slug: str) -> ProjectPaths:
    """The per-project artifact directories, created if absent."""
    paths = ProjectPaths(
        batch_requests=REPO_ROOT / "batch_requests" / slug,
        dimension_requests=REPO_ROOT / "dimension_requests" / slug,
        analysis_results=REPO_ROOT / "analysis_results" / slug,
        batch_stats=REPO_ROOT / "batch_stats" / slug,
        sql_batches=REPO_ROOT / "sql_batches" / slug,
        organic=REPO_ROOT / "organic" / slug,
    )
    for p in (paths.batch_requests, paths.dimension_requests, paths.analysis_results,
              paths.batch_stats, paths.sql_batches, paths.organic):
        p.mkdir(parents=True, exist_ok=True)
    return paths
