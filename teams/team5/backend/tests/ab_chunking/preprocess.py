"""Text preprocessing for chunking AB test."""

import re

BOILERPLATE_MARKERS = [
    "Meer over",
    "GroepenPraat mee",
    "Heb je gevonden wat je zocht",
    "LotgenotenVind lotgenoten",
]


def strip_boilerplate(text: str) -> str:
    """Remove kanker.nl footer boilerplate.

    Finds the earliest occurrence of any boilerplate marker
    and truncates the text there.
    """
    earliest = len(text)
    for marker in BOILERPLATE_MARKERS:
        idx = text.find(marker)
        if idx != -1 and idx < earliest:
            earliest = idx
    result = text[:earliest].strip()
    return result if result else text.strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using period + capital letter and newline boundaries.

    Handles Dutch text where abbreviations are less common than English.
    """
    # Split on newlines first, then on sentence boundaries within each line
    sentences = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Split on ". " followed by uppercase, "? ", "! "
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', line)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences
