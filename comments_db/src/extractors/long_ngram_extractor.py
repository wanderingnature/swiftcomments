"""
Long N-gram Extractor for Template Detection
Extracts 6, 7, and 8 word n-grams for advanced pattern detection

Tokens come from shared.text_norm.tokenize: the same markup, entity, NFKD and
fold rules the sentence keys use (one normalizer), numerals kept, and every token
carrying its (start, end) offsets into the original text so an n-gram
occurrence can be mapped back to the characters it covers.
"""

import hashlib
import sys
from pathlib import Path
from typing import Any, List, Set, Dict, Tuple, Optional
from collections import defaultdict, Counter
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # repo root: shared

from shared.text_norm import Token, sentence_index, tokenize  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LongNgramExtractor:
    """
    Extract and analyze long n-grams (6-8 words) for template detection.
    """

    # Common stopwords to optionally filter
    STOPWORDS = frozenset([
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is',
        'was', 'are', 'were', 'been', 'be', 'have', 'has',
        'had', 'do', 'does', 'did', 'will', 'would', 'shall',
        'should', 'may', 'might', 'must', 'can', 'could'
    ])

    def __init__(
        self,
        min_n: int = 6,
        max_n: int = 8,
        remove_stopwords: bool = False,
        lowercase: bool = True,
        min_word_length: int = 2
    ):
        """
        Initialize the long n-gram extractor.

        Args:
            min_n: Minimum n-gram size (default 6)
            max_n: Maximum n-gram size (default 8)
            remove_stopwords: Whether to remove stopwords
            lowercase: Convert text to lowercase
            min_word_length: Minimum word length to consider
        """
        self.min_n = min_n
        self.max_n = max_n
        self.remove_stopwords = remove_stopwords
        self.lowercase = lowercase
        self.min_word_length = min_word_length

        # Storage for corpus-level statistics
        self.ngram_frequencies = defaultdict(int)
        self.ngram_to_docs = defaultdict(set)
        self.document_count = 0

    def tokens(self, text: str) -> List[Token]:
        """The shared tokenizer's tokens, each with (start, end) offsets into
        `text`. Lowercasing, NFKD, markup, entities, contractions, URLs and
        numerals are its rules (shared.text_norm.tokenize); `min_word_length`
        is the minimum letters of an alphabetic token."""
        toks = tokenize(text, min_alpha=self.min_word_length)
        if self.remove_stopwords:
            toks = [t for t in toks if t.text not in self.STOPWORDS]
        return toks

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        return [t.text for t in self.tokens(text)]

    def extract_ngrams(
        self,
        text: str,
        n: Optional[int] = None
    ) -> Dict[int, List[Tuple[str, ...]]]:
        """
        Extract n-grams from text.

        Args:
            text: Input text
            n: Specific n-gram size (if None, extract all sizes)

        Returns:
            Dictionary mapping n-gram size to list of n-grams
        """
        tokens = self.tokenize(text)

        if len(tokens) < self.min_n:
            return {}

        ngrams_by_size = {}

        # Determine which n-gram sizes to extract
        if n is not None:
            sizes = [n] if self.min_n <= n <= self.max_n else []
        else:
            sizes = range(self.min_n, min(self.max_n + 1, len(tokens) + 1))

        for size in sizes:
            ngrams = []
            for i in range(len(tokens) - size + 1):
                ngram = tuple(tokens[i:i + size])
                ngrams.append(ngram)
            ngrams_by_size[size] = ngrams

        return ngrams_by_size

    def hash_ngram(self, ngram: Tuple[str, ...]) -> str:
        """
        Create a hash for an n-gram.

        Args:
            ngram: Tuple of words

        Returns:
            MD5 hash string
        """
        ngram_text = ' '.join(ngram)
        return hashlib.md5(ngram_text.encode()).hexdigest()

    def extract_with_positions(
        self,
        text: str,
        filter_stopword_redundancy: bool = True
    ) -> Dict[int, List[Dict]]:
        """
        Extract n-grams with their positions in the text.

        Args:
            text: Input text
            filter_stopword_redundancy: Remove n-grams that are redundant due to stopwords

        Returns:
            Dictionary mapping n-gram size to list of n-gram info dicts
        """
        toks = self.tokens(text)

        if len(toks) < self.min_n:
            return {}

        # The sentence an n-gram starts in, by the SAME splitter the sentence
        # keys use (shared.text_norm.sentences), which does not cut decimals
        # or abbreviations.
        sentence_at = sentence_index(text)
        surfaces = [t.text for t in toks]

        # First pass: generate all n-grams
        all_ngrams_by_size = {}
        for size in range(self.min_n, min(self.max_n + 1, len(toks) + 1)):
            ngram_list = []

            for i in range(len(toks) - size + 1):
                ngram = tuple(surfaces[i:i + size])

                ngram_info = {
                    'ngram': ngram,
                    'hash': self.hash_ngram(ngram),
                    'text': ' '.join(ngram),
                    'position': i,
                    'sentence_position': sentence_at(toks[i].start),
                    # The characters of the original text this occurrence
                    # covers: first token's start to last token's end.
                    'char_start': toks[i].start,
                    'char_end': toks[i + size - 1].end,
                    'first_words': ' '.join(ngram[:3]),
                    'last_words': ' '.join(ngram[-3:])
                }
                ngram_list.append(ngram_info)

            all_ngrams_by_size[size] = ngram_list

        # Second pass: filter n-grams that start or end with stopwords
        if filter_stopword_redundancy:
            filtered_ngrams_by_size = {}

            for size, ngram_list in all_ngrams_by_size.items():
                filtered_list = []

                for ng_info in ngram_list:
                    ngram = ng_info['ngram']

                    # Simply skip if starts or ends with a stopword
                    # (ngram is already lowercase from normalization)
                    if ngram[0] in self.STOPWORDS or ngram[-1] in self.STOPWORDS:
                        continue  # Skip this n-gram

                    # Keep this n-gram
                    filtered_list.append(ng_info)

                if filtered_list:
                    filtered_ngrams_by_size[size] = filtered_list

            # Don't log per-comment - too spammy
            return filtered_ngrams_by_size

        return all_ngrams_by_size

    def fit_corpus(self, documents: List[Dict[str, Any]]):
        """
        Fit the extractor on a corpus of documents.

        Args:
            documents: List of document dicts with 'comment_id' and 'comment_text'
        """
        logger.info(f"Fitting on {len(documents)} documents")

        self.ngram_frequencies.clear()
        self.ngram_to_docs.clear()
        self.document_count = len(documents)

        for doc in documents:
            doc_id = doc['comment_id']
            text = doc['comment_text']

            ngrams_by_size = self.extract_ngrams(text)

            # Track unique n-grams per document
            seen_in_doc = set()

            for size, ngrams in ngrams_by_size.items():
                for ngram in ngrams:
                    ngram_hash = self.hash_ngram(ngram)

                    if ngram_hash not in seen_in_doc:
                        self.ngram_frequencies[ngram_hash] += 1
                        self.ngram_to_docs[ngram_hash].add(doc_id)
                        seen_in_doc.add(ngram_hash)

        logger.info(f"Extracted {len(self.ngram_frequencies)} unique n-grams")

    def detect_template_blocks(
        self,
        text: str,
        template_hashes: Set[str],
        min_block_size: int = 2
    ) -> List[Dict]:
        """
        Detect consecutive template n-grams forming blocks.

        Args:
            text: Input text
            template_hashes: Set of known template n-gram hashes
            min_block_size: Minimum consecutive n-grams to form a block

        Returns:
            List of template block information
        """
        ngrams_with_pos = self.extract_with_positions(text)

        template_blocks = []

        for size, ngram_list in ngrams_with_pos.items():
            # Mark which n-grams are templates
            is_template = [
                ng['hash'] in template_hashes for ng in ngram_list
            ]

            # Find consecutive runs of template n-grams
            blocks = []
            current_block = []

            for i, is_tmpl in enumerate(is_template):
                if is_tmpl:
                    current_block.append(i)
                else:
                    if len(current_block) >= min_block_size:
                        blocks.append(current_block)
                    current_block = []

            # Check final block
            if len(current_block) >= min_block_size:
                blocks.append(current_block)

            # Create block information
            for block_indices in blocks:
                start_idx = block_indices[0]
                end_idx = block_indices[-1]

                block_ngrams = [ngram_list[i] for i in block_indices]
                block_hashes = [ng['hash'] for ng in block_ngrams]

                # Create block hash from sequence
                block_hash = hashlib.md5(
                    ''.join(block_hashes).encode()
                ).hexdigest()

                template_blocks.append({
                    'block_hash': block_hash,
                    'ngram_sequence': block_hashes,
                    'start_position': block_ngrams[0]['position'],
                    'end_position': block_ngrams[-1]['position'] + size - 1,
                    'total_words': (end_idx - start_idx + 1) * size,
                    'block_length': len(block_indices),
                    'n': size
                })

        return template_blocks

    def calculate_overlap(
        self,
        doc1_ngrams: Set[str],
        doc2_ngrams: Set[str]
    ) -> Dict[str, Any]:
        """
        Calculate overlap metrics between two documents.

        Args:
            doc1_ngrams: Set of n-gram hashes from document 1
            doc2_ngrams: Set of n-gram hashes from document 2

        Returns:
            Dictionary of overlap metrics
        """
        intersection = doc1_ngrams & doc2_ngrams
        union = doc1_ngrams | doc2_ngrams

        jaccard = len(intersection) / len(union) if union else 0
        overlap_ratio = len(intersection) / min(len(doc1_ngrams), len(doc2_ngrams)) if doc1_ngrams and doc2_ngrams else 0

        return {
            'shared_ngrams': len(intersection),
            'jaccard_similarity': jaccard,
            'overlap_ratio': overlap_ratio,
            'doc1_unique': len(doc1_ngrams - doc2_ngrams),
            'doc2_unique': len(doc2_ngrams - doc1_ngrams)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get corpus-level statistics.

        Returns:
            Dictionary of statistics
        """
        doc_frequencies = [len(docs) for docs in self.ngram_to_docs.values()]

        stats = {
            'total_documents': self.document_count,
            'unique_ngrams': len(self.ngram_frequencies),
            'avg_doc_frequency': sum(doc_frequencies) / len(doc_frequencies) if doc_frequencies else 0,
            'max_doc_frequency': max(doc_frequencies) if doc_frequencies else 0,
            'min_doc_frequency': min(doc_frequencies) if doc_frequencies else 0,
            'singleton_ngrams': sum(1 for freq in doc_frequencies if freq == 1),
            'template_candidates': sum(1 for freq in doc_frequencies if freq >= 5)
        }

        return stats