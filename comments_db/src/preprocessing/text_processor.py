"""
Text preprocessing and normalization functions.
"""

import re
import string
import hashlib
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # repo root: shared

from shared.text_norm import unescape_text  # noqa: E402

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TextProcessor:
    """
    Text preprocessing and normalization utilities.
    """

    def __init__(self, preserve_case: bool = False):
        """
        Initialize text processor.

        Args:
            preserve_case: Whether to preserve text case
        """
        self.preserve_case = preserve_case
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        self.email_pattern = re.compile(r'\S+@\S+')
        self.number_pattern = re.compile(r'\d+')
        self.whitespace_pattern = re.compile(r'\s+')

    def normalize(self, text: str) -> str:
        """
        Normalize text for processing.

        Args:
            text: Raw text

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to string if needed
        text = str(text)

        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)

        # Replace URLs
        text = self.url_pattern.sub(' URL ', text)

        # Replace emails
        text = self.email_pattern.sub(' EMAIL ', text)

        # Remove HTML tags if present
        text = re.sub(r'<[^>]+>', ' ', text)

        # Handle special characters
        text = text.replace('\n', ' ')
        text = text.replace('\t', ' ')
        text = text.replace('\r', ' ')

        # Normalize whitespace
        text = self.whitespace_pattern.sub(' ', text)

        # Case normalization
        if not self.preserve_case:
            text = text.lower()

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def clean(self, text: str) -> str:
        """
        Clean text for analysis.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        text = self.normalize(text)

        # Remove punctuation except sentence endings
        text = re.sub(r'[^\w\s.!?]', ' ', text)

        # Normalize numbers
        text = self.number_pattern.sub(' NUM ', text)

        # Remove extra whitespace
        text = self.whitespace_pattern.sub(' ', text)

        return text.strip()

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Clean first
        text = self.clean(text)

        # Split on whitespace
        tokens = text.split()

        # Filter empty tokens
        tokens = [t for t in tokens if t]

        return tokens

    def remove_stopwords(
        self,
        tokens: List[str],
        stopwords: Optional[set] = None
    ) -> List[str]:
        """
        Remove stopwords from token list.

        Args:
            tokens: List of tokens
            stopwords: Set of stopwords to remove

        Returns:
            Filtered token list
        """
        if stopwords is None:
            # Basic English stopwords
            stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
                'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'shall', 'should', 'may', 'might', 'must',
                'can', 'could', 'this', 'that', 'these', 'those', 'i', 'you',
                'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
                'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
                'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own',
                'same', 'so', 'than', 'too', 'very', 'just', 'me', 'him',
                'her', 'us', 'them'
            }

        return [t for t in tokens if t.lower() not in stopwords]

    def get_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Normalize first
        text = self.normalize(text)

        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)

        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def process_batch(
        self,
        texts: List[str],
        normalize: bool = True,
        clean: bool = False,
        tokenize: bool = False
    ) -> List[Any]:
        """
        Process a batch of texts.

        Args:
            texts: List of texts
            normalize: Whether to normalize
            clean: Whether to clean
            tokenize: Whether to tokenize

        Returns:
            List of processed texts
        """
        results = []

        for text in texts:
            if tokenize:
                result = self.tokenize(text)
            elif clean:
                result = self.clean(text)
            elif normalize:
                result = self.normalize(text)
            else:
                result = text

            results.append(result)

        return results

    def calculate_text_statistics(self, text: str) -> Dict[str, Any]:
        """
        Calculate basic text statistics.

        Args:
            text: Input text

        Returns:
            Dictionary of statistics
        """
        tokens = self.tokenize(text)
        sentences = self.get_sentences(text)

        stats = {
            "char_count": len(text),
            "word_count": len(tokens),
            "sentence_count": len(sentences),
            "avg_word_length": (
                sum(len(t) for t in tokens) / len(tokens)
                if tokens else 0
            ),
            "avg_sentence_length": (
                len(tokens) / len(sentences)
                if sentences else 0
            ),
            "unique_word_count": len(set(tokens)),
            "lexical_diversity": (
                len(set(tokens)) / len(tokens)
                if tokens else 0
            )
        }

        return stats

    def get_canonical_text(self, text: str) -> str:
        """
        Get canonical version of text for deduplication.

        Args:
            text: Input text

        Returns:
            Canonical text suitable for hashing
        """
        if not text:
            return ""

        # Convert to string if needed
        text = str(text)

        # The submission form's markup and entities are not content: '<br/>'
        # stripped of its punctuation below would be the word 'br' and '&amp;'
        # the word 'amp', and two copies of one letter differing only in a
        # line break would hash apart. One normalizer for every
        # reading of comment text: shared.text_norm.
        text = unescape_text(text)

        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)

        # Convert to lowercase for consistency
        text = text.lower()

        # Remove all whitespace variations and normalize to single spaces
        text = re.sub(r'\s+', ' ', text)

        # Remove all punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)

        # Remove numbers (optional - depending on use case)
        # text = re.sub(r'\d+', '', text)

        # Final strip
        text = text.strip()

        return text

    def get_hashes(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate SHA256 and MD5 hashes for text.

        Args:
            text: Input text

        Returns:
            Tuple of (sha256_hash, md5_hash) or (None, None) if text is empty
        """
        # Get canonical text for consistent hashing
        canonical_text = self.get_canonical_text(text)

        if not canonical_text:
            return None, None

        # Encode to bytes
        text_bytes = canonical_text.encode('utf-8')

        # Generate SHA256 hash (primary)
        sha256_hash = hashlib.sha256(text_bytes).hexdigest()

        # Generate MD5 hash (for compatibility)
        md5_hash = hashlib.md5(text_bytes).hexdigest()

        return sha256_hash, md5_hash