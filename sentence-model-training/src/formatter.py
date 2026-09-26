"""
Gloss-to-English Sentence Formatter.
Provides a deterministic translation/formatting utility converting raw decoded glosses to natural sentences.
"""

from typing import List


# Common ISL idiom & phrase mappings for smooth sentence generation
IDIOM_MAP = {
    ("GOOD", "MORNING"): "Good morning.",
    ("GOOD", "AFTERNOON"): "Good afternoon.",
    ("GOOD", "EVENING"): "Good evening.",
    ("GOOD", "NIGHT"): "Good night.",
    ("THANK", "YOU"): "Thank you.",
    ("THANKYOU",): "Thank you.",
    ("HOW", "ARE", "YOU"): "How are you?",
    ("HOW", "YOU"): "How are you?",
    ("WHAT", "YOUR", "NAME"): "What is your name?",
    ("WHAT", "NAME"): "What is your name?",
    ("MY", "NAME"): "My name is...",
    ("NICE", "MEET", "YOU"): "Nice to meet you.",
    ("HELP", "ME"): "Please help me.",
    ("I", "LOVE", "YOU"): "I love you.",
    ("SEE", "YOU", "AGAIN"): "See you again.",
    ("WELCOME",): "Welcome.",
    ("PLEASE",): "Please.",
    ("SORRY",): "I am sorry.",
}


def format_gloss_to_sentence(glosses: List[str]) -> str:
    """
    Format a list of ISL gloss strings into an English sentence.
    
    Args:
        glosses: List of uppercase gloss strings, e.g. ["GOOD", "MORNING"]
    Returns:
        Formatted English string, e.g. "Good morning."
    """
    if not glosses:
        return ""

    normalized_glosses = tuple(g.strip().upper() for g in glosses if g.strip())
    if not normalized_glosses:
        return ""

    # Check direct idiom match
    if normalized_glosses in IDIOM_MAP:
        return IDIOM_MAP[normalized_glosses]

    # Sub-phrase matching or fallback concatenation
    words = [g.lower() for g in normalized_glosses]
    sentence = " ".join(words).capitalize()

    # Add appropriate trailing punctuation if missing
    if not sentence.endswith((".", "?", "!")):
        if any(w in words for w in ["what", "how", "why", "where", "when", "who"]):
            sentence += "?"
        else:
            sentence += "."

    return sentence


DEMO_GLOSS_TO_ENGLISH = {
    "thank you so much": "Thank you so much",
    "how old you": "How old are you",
    "i help you": "Can I help you",
    "do not worry": "Do not worry",
    "you welcome": "You are welcome",
}


def format_gloss_to_english(gloss_text: str) -> str:
    """
    Convert a predicted gloss sequence to a natural English sentence.
    Uses an exact lookup against known reliable demo sentences (Step 8B).
    Falls back to a capitalized gloss string with a marker if the
    predicted sequence is outside the current reliable demo set.
    """
    key = gloss_text.strip().lower()
    if key in DEMO_GLOSS_TO_ENGLISH:
        return DEMO_GLOSS_TO_ENGLISH[key]
    return gloss_text.strip().capitalize() + " (unrecognized sentence)"

