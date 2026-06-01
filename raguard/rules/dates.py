import re
from ..models import Warning

# Matches: 2024-01-15, 01/15/2024, January 15 2024, 15 Jan 2024, Q3 2024, etc.
_DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b",
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2}(?:,?\s+\d{4})?\b",
    r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"(?:\s+\d{4})?\b",
    r"\bQ[1-4]\s+\d{4}\b",
    r"\b\d{4}\b",  # bare year — lowest confidence, kept for coverage
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _DATE_PATTERNS]


def extract_dates(text: str) -> set[str]:
    found: set[str] = set()
    for pattern in _COMPILED:
        for m in pattern.finditer(text):
            found.add(m.group().strip())
    return found


def check_dates(response: str, docs_concat: str) -> list[Warning]:
    response_dates = extract_dates(response)
    doc_dates = extract_dates(docs_concat)

    warnings: list[Warning] = []
    for date in response_dates:
        # Bare 4-digit years are common false positives; require exact word match in docs
        if date not in doc_dates and date.lower() not in docs_concat.lower():
            warnings.append(Warning(
                severity="high",
                type="unsupported_date",
                text=date,
                suggestion=f'"{date}" not found in retrieved documents. Verify the source.',
            ))
    return warnings
