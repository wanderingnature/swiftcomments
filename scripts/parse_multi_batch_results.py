#!/usr/bin/env python3
"""
Multi-Batch Results Parser
Parses and consolidates results from multiple Together.ai batch result files

Usage:
    # Parse all results for a timestamp
    python scripts/parse_multi_batch_results.py --timestamp 20250908_093956
    
    # Parse specific result files
    python scripts/parse_multi_batch_results.py --files batch_requests/results_*.jsonl

Author: Classification System
Date: 2025-09-08
"""

import sys
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
import glob

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Through the repo root, not a bare `utils`: three other `utils` packages in the repo
# (streamlit_organic_app, comments_db/src, frontend) shadow it under the test suite.
from src.utils.logging_config import setup_logging  # noqa: E402
from shared.llm_client import TruncatedResponse


# The consolidated CSV's columns: one row per (comment, topic). load_classifications
# reads these same keys, whether from the CSV or from classification_rows() directly.
CSV_FIELDS = ('comment_id', 'sentiment', 'sentiment_strength',
              'topic_name', 'topic_confidence', 'supporting_phrases')


def parse_completion(comment_id, body):
    """One chat-completion body -> (classification, None) or (None, error).

    The single parse of a classification answer, shared by the batch-file parser
    and the re-classify runner (reclassify_groups.py). The classification carries
    comment_id, sentiment, sentiment_strength and the model's topics as returned.
    An error carries error_type, the full error_message and the full ai_response —
    nothing is cut. Reasoning models (the Qwen3 family) may return the object in
    the think channel with content empty; it is taken from there. A response that
    does not parse is discarded, never repaired.
    """
    choices = body.get('choices', [])
    if not choices:
        return None, {'comment_id': comment_id, 'error_type': 'no_choices',
                      'error_message': 'No choices in response'}
    message = choices[0].get('message', {}) or {}
    ai_response = message.get('content', '') or ''
    if not ai_response.strip():
        rc = message.get('reasoning_content') or ''
        if '{' in rc:
            ai_response = rc[rc.index('{'):]
    try:
        try:
            data = json.loads(ai_response.strip())
        except json.JSONDecodeError:
            raise TruncatedResponse(
                f"{comment_id}: truncated by the server — re-run it, never repair it")
        if not isinstance(data, dict) or 'sentiment' not in data or 'topics' not in data:
            raise ValueError("Missing required fields: sentiment or topics")
        parts = str(data['sentiment']).split('|')
        if len(parts) != 2:
            raise ValueError(f"Invalid sentiment format: {data['sentiment']}")
        return {'comment_id': comment_id, 'sentiment': parts[0],
                'sentiment_strength': parts[1], 'topics': data['topics']}, None
    except TruncatedResponse as e:
        return None, {'comment_id': comment_id, 'error_type': 'truncated',
                      'error_message': str(e), 'ai_response': ai_response}
    except (ValueError, KeyError, TypeError) as e:
        return None, {'comment_id': comment_id, 'error_type': 'parse_error',
                      'error_message': f"Failed to parse AI response: {e}",
                      'ai_response': ai_response}


def classification_rows(classification):
    """The CSV_FIELDS rows of one classification: one per topic, or one with an
    empty topic when the model returned none. supporting_phrases stays a list;
    the CSV writer joins it with '|'."""
    base = {'comment_id': classification['comment_id'],
            'sentiment': classification['sentiment'],
            'sentiment_strength': classification['sentiment_strength']}
    topics = classification['topics']
    if not topics:
        return [{**base, 'topic_name': '', 'topic_confidence': 0.0,
                 'supporting_phrases': []}]
    return [{**base, 'topic_name': t.get('topic_name', ''),
             'topic_confidence': t.get('confidence', 0.0),
             'supporting_phrases': list(t.get('supporting_phrases', []))}
            for t in topics]


class MultiBatchResultsParser:
    """Parse and consolidate results from multiple batch result files."""
    
    def __init__(self, slug):
        self.logger = setup_logging()
        self.slug = slug
        self.batch_requests_dir = Path("batch_requests") / slug
        
    def find_result_files_by_timestamp(self, timestamp):
        """Find all result files for a given timestamp."""
        pattern = f"results_{timestamp}_*.jsonl"
        files = list(self.batch_requests_dir.glob(pattern))
        files.sort()
        return files
        
    def parse_batch_result_file(self, result_file):
        """Parse a single batch result file."""
        self.logger.info(f"Parsing batch result file: {result_file}")
        
        classifications = []
        errors = []
        
        # Token usage tracking
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        
        with open(result_file, 'r', encoding='utf-8') as f:
            line_count = 0
            for line in f:
                line_count += 1
                try:
                    result = json.loads(line.strip())
                    
                    # Extract comment_id from custom_id
                    comment_id = result.get('custom_id', '')
                    
                    # Check for API errors
                    if 'error' in result:
                        error_info = {
                            'comment_id': comment_id,
                            'error_type': result['error'].get('type', 'unknown'),
                            'error_message': result['error'].get('message', 'unknown'),
                            'file': result_file.name,
                            'line': line_count
                        }
                        errors.append(error_info)
                        continue
                    
                    # Together wraps the completion in response.body; Fireworks'
                    # result line may carry the completion as response itself.
                    response = result.get('response', {}) or {}
                    body = (response.get('body') if isinstance(response.get('body'), dict)
                            else response) or {}

                    usage = body.get('usage', {}) or {}
                    total_prompt_tokens += usage.get('prompt_tokens', 0)
                    total_completion_tokens += usage.get('completion_tokens', 0)
                    total_tokens += usage.get('total_tokens', 0)

                    classification, error_info = parse_completion(comment_id, body)
                    if error_info is not None:
                        error_info.update(file=result_file.name, line=line_count)
                        errors.append(error_info)
                        continue
                    assert classification is not None
                    classification.update(file_source=result_file.name,
                                          line_number=line_count)
                    classifications.append(classification)

                except Exception as e:
                    error_info = {
                        'comment_id': 'unknown',
                        'error_type': 'json_error',
                        'error_message': f"Failed to parse JSON line: {str(e)}",
                        'file': result_file.name,
                        'line': line_count
                    }
                    errors.append(error_info)
                    continue
        
        # Calculate costs at Qwen/Qwen2.5-7B-Instruct-Turbo serverless rates
        # ($0.30/1M in and out, operator-confirmed 2026-07-23). Indicative only:
        # the true rate is per-model and lives with the provider.
        input_cost = (total_prompt_tokens / 1_000_000) * 0.30
        output_cost = (total_completion_tokens / 1_000_000) * 0.30
        total_cost = input_cost + output_cost
        
        token_usage = {
            'prompt_tokens': total_prompt_tokens,
            'completion_tokens': total_completion_tokens,
            'total_tokens': total_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost
        }
        
        self.logger.info(f"Parsed {len(classifications)} classifications and {len(errors)} errors from {result_file}")
        return classifications, errors, token_usage
        
    def consolidate_results(self, result_files):
        """Parse and consolidate results from multiple files."""
        print(f"Multi-Batch Results Parser")
        print("=" * 50)
        print(f"Processing {len(result_files)} result files")
        print()
        
        all_classifications = []
        all_errors = []
        file_stats = []
        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        for i, result_file in enumerate(result_files, 1):
            print(f"Processing file {i}/{len(result_files)}: {result_file.name}")
            
            classifications, errors, token_usage = self.parse_batch_result_file(result_file)
            
            all_classifications.extend(classifications)
            all_errors.extend(errors)
            total_cost += token_usage['total_cost']
            total_prompt_tokens += token_usage['prompt_tokens']
            total_completion_tokens += token_usage['completion_tokens']
            
            file_stats.append({
                'file': result_file.name,
                'classifications': len(classifications),
                'errors': len(errors),
                'total_lines': len(classifications) + len(errors),
                'token_usage': token_usage
            })
            
            print(f"  Classifications: {len(classifications)}")
            print(f"  Errors: {len(errors)}")
            print(f"  Token usage: {token_usage['prompt_tokens']:,} input + {token_usage['completion_tokens']:,} output = {token_usage['total_tokens']:,} total")
            print(f"  Cost: ${token_usage['total_cost']:.4f} (input: ${token_usage['input_cost']:.4f}, output: ${token_usage['output_cost']:.4f})")
            print()
        
        # Add total usage to file stats
        total_usage_summary = {
            'total_cost': total_cost,
            'total_prompt_tokens': total_prompt_tokens,
            'total_completion_tokens': total_completion_tokens,
            'total_tokens': total_prompt_tokens + total_completion_tokens
        }
        
        return all_classifications, all_errors, file_stats, total_usage_summary
        
    def save_consolidated_results(self, classifications, errors, file_stats, timestamp):
        """Save consolidated results to files."""
        output_dir = Path("analysis_results") / self.slug
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filenames
        output_files = {
            'classifications_csv': output_dir / f"consolidated_classifications_{timestamp}.csv",
            'errors_json': output_dir / f"consolidated_errors_{timestamp}.json",
            'stats_json': output_dir / f"consolidation_stats_{timestamp}.json"
        }
        
        # Save classifications as CSV
        print(f"Saving {len(classifications)} classifications to: {output_files['classifications_csv']}")
        with open(output_files['classifications_csv'], 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(list(CSV_FIELDS))
            
            for classification in classifications:
                for row in classification_rows(classification):
                    writer.writerow(['|'.join(row[k]) if k == 'supporting_phrases'
                                     else row[k] for k in CSV_FIELDS])

        # Save errors as JSON
        if errors:
            print(f"Saving {len(errors)} errors to: {output_files['errors_json']}")
            with open(output_files['errors_json'], 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2, ensure_ascii=False)
        
        # Save consolidation stats
        consolidation_stats = {
            'timestamp': timestamp,
            'processed_at': datetime.now().isoformat(),
            'total_files': len(file_stats),
            'total_classifications': len(classifications),
            'total_errors': len(errors),
            'success_rate': len(classifications) / (len(classifications) + len(errors)) * 100 if (len(classifications) + len(errors)) > 0 else 0,
            'file_breakdown': file_stats
        }
        
        print(f"Saving consolidation stats to: {output_files['stats_json']}")
        with open(output_files['stats_json'], 'w', encoding='utf-8') as f:
            json.dump(consolidation_stats, f, indent=2, ensure_ascii=False)
        
        return output_files, consolidation_stats
    
    def save_summary_to_file(self, timestamp, stats, usage_summary, output_files, classifications):
        """Save consolidation summary to a text file."""
        # Create batch_stats directory
        batch_stats_dir = Path("batch_stats") / self.slug
        batch_stats_dir.mkdir(parents=True, exist_ok=True)
        
        summary_file = batch_stats_dir / f"batch_{timestamp}_summary.txt"
        
        summary_lines = [
            "=" * 50,
            "CONSOLIDATION SUMMARY",
            "=" * 50,
            f"Total files processed: {stats['total_files']}",
            f"Total classifications: {stats['total_classifications']:,}",
            f"Total errors: {stats['total_errors']:,}",
            f"Success rate: {stats['success_rate']:.1f}%",
            "",
            "TOTAL USAGE & COST SUMMARY",
            "-" * 30,
            f"Total tokens: {usage_summary['total_tokens']:,} ({usage_summary['total_prompt_tokens']:,} input + {usage_summary['total_completion_tokens']:,} output)",
            f"Total cost: ${usage_summary['total_cost']:.4f}",
            f"  Input cost: ${(usage_summary['total_prompt_tokens'] / 1_000_000) * 0.30:.4f}",
            f"  Output cost: ${(usage_summary['total_completion_tokens'] / 1_000_000) * 0.30:.4f}",
            "",
            "Output files:"
        ]
        
        for key, path in output_files.items():
            summary_lines.append(f"  {key}: {path}")
        
        summary_lines.append("")
        
        if classifications:
            summary_lines.append("Next step - Load classifications into the analysis DB:")
            summary_lines.append(f"   python scripts/load_classifications.py --project {self.slug} {output_files['classifications_csv']}")
        
        # Write to file
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_lines))
        
        self.logger.info(f"Summary saved to: {summary_file}")
        return summary_file
        
    def parse_timestamp_results(self, timestamp):
        """Parse all result files for a timestamp."""
        result_files = self.find_result_files_by_timestamp(timestamp)
        
        if not result_files:
            print(f"No result files found for timestamp: {timestamp}")
            return
            
        # Consolidate results
        classifications, errors, file_stats, usage_summary = self.consolidate_results(result_files)
        
        # Save consolidated results
        output_files, stats = self.save_consolidated_results(classifications, errors, file_stats, timestamp)
        
        # Print summary
        print("=" * 50)
        print("CONSOLIDATION SUMMARY")
        print("=" * 50)
        print(f"Total files processed: {stats['total_files']}")
        print(f"Total classifications: {stats['total_classifications']:,}")
        print(f"Total errors: {stats['total_errors']:,}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print()
        print("TOTAL USAGE & COST SUMMARY")
        print("-" * 30)
        print(f"Total tokens: {usage_summary['total_tokens']:,} ({usage_summary['total_prompt_tokens']:,} input + {usage_summary['total_completion_tokens']:,} output)")
        print(f"Total cost: ${usage_summary['total_cost']:.4f}")
        print(f"  Input cost: ${(usage_summary['total_prompt_tokens'] / 1_000_000) * 0.30:.4f}")
        print(f"  Output cost: ${(usage_summary['total_completion_tokens'] / 1_000_000) * 0.30:.4f}")
        print()
        print("Output files:")
        for key, path in output_files.items():
            print(f"  {key}: {path}")
        print()
        
        if classifications:
            print("Next step - Load classifications into the analysis DB:")
            print(f"   python scripts/load_classifications.py --project {self.slug} {output_files['classifications_csv']}")
        
        # Save summary to file
        self.save_summary_to_file(timestamp, stats, usage_summary, output_files, classifications)
        
    def parse_specific_files(self, file_patterns):
        """Parse specific result files."""
        result_files = []
        for pattern in file_patterns:
            result_files.extend(Path(".").glob(pattern))
            
        if not result_files:
            print("No result files found matching patterns")
            return
            
        # Generate timestamp for output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Consolidate results
        classifications, errors, file_stats, usage_summary = self.consolidate_results(result_files)
        
        # Save consolidated results
        output_files, stats = self.save_consolidated_results(classifications, errors, file_stats, timestamp)
        
        # Print summary
        print("=" * 50)
        print("CONSOLIDATION SUMMARY")
        print("=" * 50)
        print(f"Total files processed: {stats['total_files']}")
        print(f"Total classifications: {stats['total_classifications']:,}")
        print(f"Total errors: {stats['total_errors']:,}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print()
        print("Output files:")
        for key, path in output_files.items():
            print(f"  {key}: {path}")
        
        # Save summary to file  
        self.save_summary_to_file(timestamp, stats, usage_summary, output_files, classifications)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Parse and consolidate results from multiple Together.ai batch result files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse all results for timestamp
  python scripts/parse_multi_batch_results.py --timestamp 20250908_093956
  
  # Parse specific files
  python scripts/parse_multi_batch_results.py --files batch_requests/results_*.jsonl
        """
    )
    
    parser.add_argument(
        '--project',
        type=str,
        required=True,
        help='Project slug (namespaces batch_requests/analysis_results/batch_stats)'
    )
    parser.add_argument(
        '--timestamp',
        type=str,
        help='Parse all result files for given timestamp (e.g., 20250908_093956)'
    )
    parser.add_argument(
        '--files',
        nargs='+',
        help='Parse specific result files (can use wildcards)'
    )
    
    args = parser.parse_args()
    
    if not any([args.timestamp, args.files]):
        print("Error: Must specify either --timestamp or --files")
        parser.print_help()
        sys.exit(1)
    
    parser_obj = MultiBatchResultsParser(args.project)
    
    try:
        if args.timestamp:
            parser_obj.parse_timestamp_results(args.timestamp)
        elif args.files:
            parser_obj.parse_specific_files(args.files)
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()