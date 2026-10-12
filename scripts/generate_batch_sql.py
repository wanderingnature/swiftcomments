#!/usr/bin/env python3
"""
Batch SQL Generator — project-scoped, metadata-snapshot-driven.

Not on the pipeline path: scripts/load_classifications.py loads the
consolidated CSV. This generator emits an INSERT … ON CONFLICT over
un-de-duplicated topic rows, which fails when a comment names the same topic
twice. Its load_snapshot is the one snapshot loader the loader reuses.

Takes the consolidated classifications CSV from parse_multi_batch_results.py
and produces SQL INSERT batches for the project's analysis schema. Deliberately
DB-free: the target schema, sentiment map, and model name all come from the
profile snapshot that generate_batch_fromfile.py wrote into
batch_requests/<slug>/batch_metadata_<TS>.json. A missing snapshot is a hard
error — never guessed, never defaulted.

Usage:
    python scripts/generate_batch_sql.py --project <slug> \\
        analysis_results/<slug>/consolidated_classifications_<TS>.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logging_config import setup_logging  # noqa: E402

SCHEMA_RE = re.compile(r'^[a-z_][a-z0-9_]{0,62}$')


def _q(value: str) -> str:
    """Escape a value for inclusion in a single-quoted SQL literal."""
    return value.replace("'", "''")


class BatchSQLGenerator:
    """Generate batch SQL files from classification results."""

    def __init__(self, slug: str, snapshot: Dict, batch_size: int = 1000):
        self.logger = setup_logging()
        self.slug = slug
        self.batch_size = batch_size

        self.schema = snapshot['analysis_schema']
        if not SCHEMA_RE.match(self.schema):
            raise ValueError(f"Invalid analysis_schema in snapshot: {self.schema!r}")
        self.sentiment_map = {k: int(v) for k, v in snapshot['sentiment_map'].items()}
        self.model_name = snapshot['model_name']

        self.output_dir = Path("sql_batches") / slug
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _extract_batch_id_from_results(self, file_path: str) -> str:
        """Extract batch ID from results filename."""
        filename = Path(file_path).stem
        batch_match = re.search(r'consolidated_classifications_(\d{8}_\d{6})', filename)
        if batch_match:
            return batch_match.group(1)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"batch_{timestamp}"

    def load_csv_results(self, csv_file: str) -> List[Dict]:
        """Load classification results from CSV file."""
        self.logger.info(f"Loading CSV results from: {csv_file}")
        results = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
        self.logger.info(f"Loaded {len(results)} classification records from CSV")
        return results

    def load_json_results(self, json_file: str) -> List[Dict]:
        """Load classification results from JSON file."""
        self.logger.info(f"Loading JSON results from: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'classifications' in data:
            results = data['classifications']
        else:
            results = data if isinstance(data, list) else []
        self.logger.info(f"Loaded {len(results)} classification records from JSON")
        return results

    def generate_classification_batch(self, classifications: List[Dict], batch_id: str,
                                      start_idx: int = 0, end_idx: Optional[int] = None) -> str:
        """Generate batch SQL for comment_classification table."""
        if end_idx is None:
            end_idx = len(classifications)

        batch_classifications = classifications[start_idx:end_idx]

        # Group by comment_id to get one classification per comment
        comment_classifications = {}

        for classification in batch_classifications:
            comment_id = classification.get('comment_id', '').strip()
            if not comment_id:
                continue

            if comment_id not in comment_classifications:
                # Parse sentiment from separate CSV columns - NO FALLBACKS!
                sentiment_stance = classification.get('sentiment', '').strip().upper()
                sentiment_strength = classification.get('sentiment_strength', '').strip().upper()

                if not sentiment_stance:
                    raise ValueError(f"Missing sentiment for comment {comment_id}")
                if not sentiment_strength:
                    raise ValueError(f"Missing sentiment_strength for comment {comment_id}")

                if sentiment_stance not in self.sentiment_map:
                    raise ValueError(f"Invalid sentiment '{sentiment_stance}' for comment {comment_id}. Valid: {list(self.sentiment_map.keys())}")

                if sentiment_strength not in ['HIGH', 'MEDIUM', 'LOW']:
                    raise ValueError(f"Invalid sentiment_strength '{sentiment_strength}' for comment {comment_id}. Valid: HIGH, MEDIUM, LOW")

                sentiment_id = self.sentiment_map[sentiment_stance]

                # Calculate average confidence for this comment across all topics
                comment_topics = [c for c in batch_classifications if c.get('comment_id') == comment_id]
                confidences = [float(c.get('topic_confidence', 0.0)) for c in comment_topics if c.get('topic_confidence')]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                comment_classifications[comment_id] = {
                    'comment_id': comment_id,
                    'sentiment_id': sentiment_id,
                    'sentiment_strength': sentiment_strength,
                    'confidence_score': round(avg_confidence, 3),
                    'custom_id': classification.get('custom_id', comment_id)
                }

        if not comment_classifications:
            return ""

        sql_lines = [
            f"-- Batch INSERT for comment_classification (batch {start_idx//self.batch_size + 1})",
            f"INSERT INTO {self.schema}.comment_classification (",
            "    comment_id, sentiment_id, sentiment_strength, batch_id, model_version,",
            "    custom_id, confidence_score, created_by, processed_date, is_active",
            ") VALUES"
        ]

        values = []
        for classification in comment_classifications.values():
            values.append(f"""    ('{_q(classification['comment_id'])}', {classification['sentiment_id']}, '{classification['sentiment_strength']}',
     '{_q(batch_id)}', '{_q(self.model_name)}', '{_q(classification['custom_id'])}',
     {classification['confidence_score']}, 'batch_processor', NOW(), true)""")

        sql_lines.append(",\n".join(values))
        sql_lines.append("ON CONFLICT (comment_id, batch_id) DO UPDATE SET")
        sql_lines.append("    sentiment_id = EXCLUDED.sentiment_id,")
        sql_lines.append("    sentiment_strength = EXCLUDED.sentiment_strength,")
        sql_lines.append("    confidence_score = EXCLUDED.confidence_score,")
        sql_lines.append("    updated_date = NOW(),")
        sql_lines.append("    updated_by = EXCLUDED.created_by;")
        sql_lines.append("")

        return "\n".join(sql_lines)

    def generate_topic_classification_batch(self, classifications: List[Dict], batch_id: str,
                                            start_idx: int = 0, end_idx: Optional[int] = None) -> str:
        """Generate batch SQL for classification_topics table."""
        if end_idx is None:
            end_idx = len(classifications)

        batch_classifications = classifications[start_idx:end_idx]

        sql_lines = [
            f"-- Batch INSERT for classification_topics (batch {start_idx//self.batch_size + 1})",
            "WITH vals(comment_id, batch_id, topic_name, confidence, supporting_phrases) AS (",
            "    VALUES"
        ]

        values = []
        skipped_no_phrases = 0
        for classification in batch_classifications:
            comment_id = classification.get('comment_id', '').strip()
            topic_name = classification.get('topic_name', '').strip()
            confidence = float(classification.get('topic_confidence', 0.0))

            # Parse supporting phrases - in CSV they're pipe-separated
            supporting_phrases = classification.get('supporting_phrases', '')
            if isinstance(supporting_phrases, str):
                phrases_list = [p.strip() for p in supporting_phrases.split('|') if p.strip()]
            else:
                phrases_list = supporting_phrases if isinstance(supporting_phrases, list) else []

            # Only include if we have valid topic data and confidence >= 0.7
            if comment_id and topic_name and confidence >= 0.7:
                if not phrases_list:
                    # A high-confidence topic with no phrases is the model
                    # declining to ground it — expected on low-signal comments.
                    # The DDL forbids phrase-less topic rows (chk_phrase_count >= 1),
                    # so skip this topic row (the comment's sentiment and any
                    # grounded topics still load). Counted and logged, never silent.
                    skipped_no_phrases += 1
                    continue
                phrases_array = "ARRAY[" + ", ".join([f"'{_q(p)}'" for p in phrases_list]) + "]"
                values.append(f"        ('{_q(comment_id)}', '{_q(batch_id)}', '{_q(topic_name)}', {confidence}, {phrases_array})")

        if skipped_no_phrases:
            self.logger.info(
                f"Skipped {skipped_no_phrases} phrase-less topic row(s) in batch"
                f" {start_idx//self.batch_size + 1} (grounding declined)")

        if not values:
            return ""

        sql_lines.append(",\n".join(values))
        sql_lines.append(")")
        sql_lines.append(f"INSERT INTO {self.schema}.classification_topics (")
        sql_lines.append("    classification_id, topic_id, confidence, supporting_phrases, rank_order, created_by, is_active")
        sql_lines.append(") SELECT")
        sql_lines.append("    cc.classification_id, t.topic_id, vals.confidence, vals.supporting_phrases,")
        sql_lines.append("    ROW_NUMBER() OVER (PARTITION BY cc.classification_id ORDER BY vals.confidence DESC),")
        sql_lines.append("    'batch_processor', true")
        sql_lines.append("FROM vals")
        sql_lines.append(f"JOIN {self.schema}.comment_classification cc ON cc.comment_id = vals.comment_id AND cc.batch_id = vals.batch_id")
        sql_lines.append(f"JOIN {self.schema}.topics t ON t.topic_name = vals.topic_name")
        sql_lines.append("ON CONFLICT (classification_id, topic_id) DO UPDATE SET")
        sql_lines.append("    confidence = EXCLUDED.confidence,")
        sql_lines.append("    supporting_phrases = EXCLUDED.supporting_phrases,")
        sql_lines.append("    rank_order = EXCLUDED.rank_order,")
        sql_lines.append("    updated_date = NOW(),")
        sql_lines.append("    updated_by = EXCLUDED.created_by;")
        sql_lines.append("")

        return "\n".join(sql_lines)

    def generate_batch_sql_files(self, input_file: str) -> List[str]:
        """Generate batch SQL files from classification results."""
        file_path = Path(input_file)

        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        if file_path.suffix.lower() == '.csv':
            classifications = self.load_csv_results(input_file)
        elif file_path.suffix.lower() == '.json':
            classifications = self.load_json_results(input_file)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        if not classifications:
            raise ValueError("No classifications found in input file")

        batch_id = self._extract_batch_id_from_results(input_file)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        self.logger.info(f"Generating batch SQL files for {len(classifications)} classifications")
        self.logger.info(f"Target schema: {self.schema}; batch ID: {batch_id}")

        generated_files = []
        total_batches = (len(classifications) + self.batch_size - 1) // self.batch_size
        unique_comments = len(set(c.get('comment_id', '') for c in classifications))

        self.logger.info(f"Found {len(classifications)} classification records from {unique_comments} unique comments")
        self.logger.info(f"Creating {total_batches} SQL batch files ({self.batch_size} records per file)")

        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(classifications))

            batch_file = self.output_dir / f"batch_{batch_num + 1:03d}_{timestamp}.sql"

            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write("-- Batch Classification SQL\n")
                f.write(f"-- Project: {self.slug} (schema {self.schema})\n")
                f.write(f"-- Generated: {datetime.now().isoformat()}\n")
                f.write(f"-- Batch: {batch_num + 1}/{total_batches}\n")
                f.write(f"-- Records: {start_idx + 1}-{end_idx}\n")
                f.write(f"-- Batch ID: {batch_id}\n\n")

                f.write("BEGIN;\n\n")

                # First, deactivate any existing classifications for comments being reprocessed
                comment_ids_in_batch = [c['comment_id'] for c in classifications[start_idx:end_idx] if c.get('comment_id')]
                if comment_ids_in_batch:
                    comment_ids_list = "', '".join(_q(c) for c in comment_ids_in_batch)
                    f.write("-- Deactivate existing classifications for reprocessed comments\n")
                    f.write(f"UPDATE {self.schema}.comment_classification \n")
                    f.write("SET is_active = false, updated_date = NOW(), updated_by = 'batch_processor'\n")
                    f.write(f"WHERE comment_id IN ('{comment_ids_list}') AND is_active = true;\n\n")

                    f.write(f"UPDATE {self.schema}.classification_topics \n")
                    f.write("SET is_active = false, updated_date = NOW(), updated_by = 'batch_processor'\n")
                    f.write("WHERE classification_id IN (\n")
                    f.write(f"    SELECT classification_id FROM {self.schema}.comment_classification \n")
                    f.write(f"    WHERE comment_id IN ('{comment_ids_list}') AND is_active = false\n")
                    f.write(");\n\n")

                classification_sql = self.generate_classification_batch(
                    classifications, batch_id, start_idx, end_idx
                )
                f.write(classification_sql)

                topic_sql = self.generate_topic_classification_batch(
                    classifications, batch_id, start_idx, end_idx
                )
                f.write(topic_sql)

                f.write("COMMIT;\n")

            generated_files.append(str(batch_file))
            self.logger.info(f"Generated batch {batch_num + 1}/{total_batches}: {batch_file}")

        # Generate execution script
        exec_script = self.output_dir / f"execute_batches_{timestamp}.sh"
        with open(exec_script, 'w', encoding='utf-8') as f:
            f.write("#!/bin/bash\n")
            f.write("# Batch SQL Execution Script\n")
            f.write(f"# Project: {self.slug}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write('if [ -z "$PGPASSWORD" ]; then\n')
            f.write('    echo "Error: PGPASSWORD environment variable not set"\n')
            f.write('    exit 1\n')
            f.write('fi\n\n')
            f.write("echo 'Executing batch SQL files...'\n\n")

            for i in range(total_batches):
                batch_file = self.output_dir / f"batch_{i + 1:03d}_{timestamp}.sql"
                f.write(f"echo 'Running batch {i + 1}/{total_batches}...'\n")
                f.write(f"psql -v ON_ERROR_STOP=1 -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f {batch_file}\n")
                f.write("if [ $? -ne 0 ]; then\n")
                f.write(f"    echo 'Error in batch {i + 1}, stopping execution'\n")
                f.write("    exit 1\n")
                f.write("fi\n\n")

            f.write("echo 'All batches completed successfully!'\n")

        os.chmod(exec_script, 0o755)
        generated_files.append(str(exec_script))

        self.logger.info(f"Generated execution script: {exec_script}")
        self.logger.info(f"Total files generated: {len(generated_files)}")

        return generated_files


def load_snapshot(slug: str, input_file: str, metadata_path: Optional[str] = None) -> Dict:
    """Load the profile snapshot for the batch the input CSV came from.

    The consolidated CSV carries the generation timestamp in its name; the
    matching batch_metadata_<TS>.json (written by generate_batch_fromfile.py)
    holds the profile snapshot. Missing snapshot = hard error.
    """
    if metadata_path:
        metadata_file = Path(metadata_path)
    else:
        match = re.search(r'(\d{8}_\d{6})', Path(input_file).stem)
        if not match:
            raise ValueError(
                f"Cannot derive batch timestamp from {input_file!r} —"
                " pass --metadata batch_requests/<slug>/batch_metadata_<TS>.json")
        metadata_file = Path("batch_requests") / slug / f"batch_metadata_{match.group(1)}.json"

    if not metadata_file.exists():
        raise FileNotFoundError(
            f"Profile snapshot not found: {metadata_file} — generate_batch_fromfile.py"
            " writes it at batch generation; without it the target schema and"
            " sentiment map are unknown.")

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    if 'profile' not in metadata:
        raise ValueError(f"{metadata_file} has no 'profile' snapshot — regenerate the batch")
    return metadata['profile']


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate batch SQL files from classification results"
    )
    parser.add_argument('--project', required=True, help='Project slug')
    parser.add_argument('input_file', help='Path to CSV or JSON classification results file')
    parser.add_argument('--metadata',
                        help='Explicit path to the batch_metadata_<TS>.json snapshot'
                             ' (default: derived from the input filename)')
    parser.add_argument('--batch-size', type=int, default=1000,
                        help='Classification records (CSV rows) per batch SQL file, not comments (default: 1000)')

    args = parser.parse_args()

    print("Batch SQL Generator")
    print("=" * 40)

    try:
        snapshot = load_snapshot(args.project, args.input_file, args.metadata)
        generator = BatchSQLGenerator(args.project, snapshot, batch_size=args.batch_size)
        generated_files = generator.generate_batch_sql_files(args.input_file)

        if Path(args.input_file).suffix.lower() == '.csv':
            classifications = generator.load_csv_results(args.input_file)
        else:
            classifications = generator.load_json_results(args.input_file)

        unique_comments = len(set(c.get('comment_id', '') for c in classifications))
        total_batches = len([f for f in generated_files if f.endswith('.sql')])

        print(f"\nGenerated {total_batches} SQL batch files:")
        print(f"   {len(classifications)} classification records from {unique_comments} unique comments")
        print(f"   Target schema: {snapshot['analysis_schema']}")
        print()
        print("Generated files:")
        for file in generated_files:
            print(f"   {file}")

        print("\nNext steps:")
        print("   1. Set database environment variables (DB_HOST/DB_PORT/DB_NAME/DB_USER/PGPASSWORD)")
        exec_script = [f for f in generated_files if f.endswith('.sh')][0]
        print(f"   2. Execute the batch script: ./{exec_script}")

    except Exception as e:
        print(f"Error generating batch SQL files: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
