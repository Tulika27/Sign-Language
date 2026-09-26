"""
Vocabulary Manager for Continuous ISL English Word-Token Sequences.
Handles word-to-index and index-to-word mappings with reserved CTC blank token at ID 0.

Note:
The available sentence annotations are English transcript tokens used as sequence
targets for CTC training. They are not manually annotated ISL glosses.
"""

import csv
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def tokenize_english_transcript(text: str) -> List[str]:
    """
    Normalize and tokenize an English sentence transcript into a sequence of word tokens.

    Normalization steps:
        1. Converts to lowercase
        2. Strips punctuation while preserving words / numbers
        3. Normalizes whitespace
        4. Returns deterministic token list

    Examples:
        "How are you?" -> ["how", "are", "you"]
        "THANK YOU!"   -> ["thank", "you"]
        "good morning" -> ["good", "morning"]
    """
    if not text or not isinstance(text, str):
        return []
    text_clean = text.lower()
    # Extract alphanumeric word tokens
    tokens = re.findall(r"\b\w+\b", text_clean)
    return tokens


def tokenize_gloss_sequence(text: str) -> List[str]:
    """Tokenize an ISL gloss annotation string."""
    if not text or not isinstance(text, str):
        return []
    return text.strip().split()


class GlossVocabulary:
    """
    Manages word/token vocabulary mapping for CTC training and inference.
    
    Structure:
        - ID 0: <blank> (Reserved for CTC decoding)
        - ID 1: <unk>   (Out-of-vocabulary unknown token)
        - ID 2+: Word tokens (e.g., 'good', 'morning', 'thank', 'you', ...)
    """

    BLANK_TOKEN = "<blank>"
    UNK_TOKEN = "<unk>"

    def __init__(self, token_to_id: Optional[Dict[str, int]] = None, token_freqs: Optional[Dict[str, int]] = None):
        if token_to_id is not None:
            self.token_to_id = dict(token_to_id)
            self.id_to_token = {v: k for k, v in self.token_to_id.items()}
        else:
            self.token_to_id = {
                self.BLANK_TOKEN: 0,
                self.UNK_TOKEN: 1,
            }
            self.id_to_token = {
                0: self.BLANK_TOKEN,
                1: self.UNK_TOKEN,
            }
        self.token_freqs = dict(token_freqs) if token_freqs is not None else {}

    @property
    def blank_id(self) -> int:
        return self.token_to_id[self.BLANK_TOKEN]

    @property
    def unk_id(self) -> int:
        return self.token_to_id[self.UNK_TOKEN]

    def __len__(self) -> int:
        return len(self.token_to_id)

    def add_token(self, token: str) -> int:
        """Add a new word token to the vocabulary if not present."""
        token_clean = token.strip().lower()
        if not token_clean:
            return self.unk_id
        if token_clean not in self.token_to_id:
            new_id = len(self.token_to_id)
            self.token_to_id[token_clean] = new_id
            self.id_to_token[new_id] = token_clean
            return new_id
        return self.token_to_id[token_clean]

    def build_from_csv(
        self,
        csv_path: Union[str, Path],
        text_col: str = "SIGN GLOSSES",
        min_freq: int = 1,
        delimiter: str = ",",
    ) -> None:
        """
        Build vocabulary from an English transcript CSV file.
        
        Args:
            csv_path: Path to CSV annotation file.
            text_col: Column name containing English transcript text.
            min_freq: Minimum frequency for a token to be added to vocabulary.
                      Tokens with frequency < min_freq are mapped to <unk> during encoding.
            delimiter: CSV field delimiter (default: ',').
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV annotation file not found: {csv_path}")

        counter = Counter()
        row_count = 0

        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if reader.fieldnames is None or text_col not in reader.fieldnames:
                raise ValueError(
                    f"Column '{text_col}' not found in CSV '{csv_path}'. "
                    f"Available columns: {reader.fieldnames}"
                )
            for row in reader:
                raw_text = row.get(text_col, "")
                tokens = tokenize_gloss_sequence(raw_text)
                counter.update(tokens)
                row_count += 1

        self.token_freqs = {k.lower(): v for k, v in counter.items()}
        self._populate_from_counter(counter, min_freq=min_freq)
        logger.info(
            f"Built vocabulary from CSV '{csv_path.name}' ({row_count} rows): "
            f"{len(self)} total tokens (including special tokens), min_freq={min_freq}."
        )

    def build_from_texts(self, texts: List[str], min_freq: int = 1) -> None:
        """Build vocabulary from a list of English transcript sentences."""
        counter = Counter()
        for text in texts:
            tokens = tokenize_english_transcript(text)
            counter.update(tokens)

        self.token_freqs = {k.lower(): v for k, v in counter.items()}
        self._populate_from_counter(counter, min_freq=min_freq)
        logger.info(
            f"Built vocabulary from {len(texts)} text items: "
            f"{len(self)} total tokens, min_freq={min_freq}."
        )

    def _populate_from_counter(self, counter: Counter, min_freq: int = 1) -> None:
        """Populate tokens from counter with deterministic sorting (frequency descending, then alphabetical)."""
        # Filter by min_freq and sort deterministically
        eligible_tokens = [
            (tok, freq) for tok, freq in counter.items()
            if freq >= min_freq and tok not in (self.BLANK_TOKEN, self.UNK_TOKEN)
        ]
        # Sort by frequency desc, then alphabetical asc
        eligible_tokens.sort(key=lambda x: (-x[1], x[0]))

        # Re-initialize basic mapping
        self.token_to_id = {
            self.BLANK_TOKEN: 0,
            self.UNK_TOKEN: 1,
        }
        self.id_to_token = {
            0: self.BLANK_TOKEN,
            1: self.UNK_TOKEN,
        }

        for tok, _ in eligible_tokens:
            tok_lower = tok.lower()
            if tok_lower in self.token_to_id:
                continue
            new_id = len(self.token_to_id)
            self.token_to_id[tok_lower] = new_id
            self.id_to_token[new_id] = tok_lower

    def build_from_annotations(self, annotation_items: List[Dict]) -> None:
        """
        Build vocabulary from legacy annotation samples.
        Expected format per item:
            {"glosses": ["good", "morning"], ...} or {"text": "Good morning", ...}
        """
        for item in annotation_items:
            if "glosses" in item:
                glosses = item["glosses"]
                if isinstance(glosses, str):
                    glosses = glosses.split()
                for g in glosses:
                    self.add_token(g)
            elif "text" in item:
                tokens = tokenize_english_transcript(item["text"])
                for t in tokens:
                    self.add_token(t)
            elif "english" in item:
                tokens = tokenize_english_transcript(item["english"])
                for t in tokens:
                    self.add_token(t)
        logger.info(f"Built vocabulary containing {len(self)} tokens (including special tokens).")

    def build_from_gloss_list(self, gloss_list: List[str]) -> None:
        """Build vocabulary from a flat list of token strings."""
        for g in gloss_list:
            self.add_token(g)
        logger.info(f"Built vocabulary containing {len(self)} tokens.")

    def token_to_id_lookup(self, token: str) -> int:
        """Convert a word token string to its token ID (case-insensitive)."""
        token_clean = token.strip().lower()
        return self.token_to_id.get(token_clean, self.unk_id)

    # Aliases for backward compatibility and intuitive access
    gloss_to_id = token_to_id_lookup
    word_to_id = token_to_id_lookup

    def id_to_token_lookup(self, idx: int) -> str:
        """Convert a token ID to its word string."""
        return self.id_to_token.get(idx, self.UNK_TOKEN)

    # Aliases for backward compatibility and intuitive access
    id_to_gloss = id_to_token_lookup
    id_to_word = id_to_token_lookup

    def encode_tokens(self, tokens: List[str]) -> List[int]:
        """Convert a list of word tokens into integer IDs."""
        return [self.token_to_id_lookup(t) for t in tokens]

    encode_sequence = encode_tokens

    def encode_text(self, text: str) -> List[int]:
        """Tokenize an English text transcript and convert to integer IDs."""
        tokens = tokenize_english_transcript(text)
        return self.encode_tokens(tokens)

    def decode_tokens(self, ids: List[int], remove_special: bool = True) -> List[str]:
        """Convert integer token IDs back to a list of word tokens."""
        result = []
        for idx in ids:
            token = self.id_to_token_lookup(idx)
            if remove_special and token in (self.BLANK_TOKEN, self.UNK_TOKEN):
                continue
            result.append(token)
        return result

    decode_sequence = decode_tokens

    def decode_to_text(self, ids: List[int], remove_special: bool = True) -> str:
        """Decode integer token IDs directly into a space-separated string."""
        tokens = self.decode_tokens(ids, remove_special=remove_special)
        return " ".join(tokens)

    def save_to_json(self, filepath: Union[str, Path]) -> None:
        """Save vocabulary mapping and frequency metadata to JSON."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "token_to_id": self.token_to_id,
            "token_freqs": self.token_freqs,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved vocabulary ({len(self)} tokens) to {filepath}")

    @classmethod
    def load_from_json(cls, filepath: Union[str, Path]) -> "GlossVocabulary":
        """Load vocabulary from a JSON file (supports legacy flat dict or modern schema)."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "token_to_id" in data:
            return cls(token_to_id=data["token_to_id"], token_freqs=data.get("token_freqs"))
        return cls(token_to_id=data)


# Type alias for general naming clarity
WordVocabulary = GlossVocabulary
