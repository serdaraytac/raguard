import re
from ..models import Warning

# v1: static phrase list. v2: NLP-based unresolved pronoun/reference detection.
_VAGUE_PHRASES = [
    "the team", "the management", "the manager", "the director",
    "the department", "the committee", "the board",
    "recent report", "the report", "the study", "the analysis",
    "the document", "the contract", "the agreement",
    "recently", "in recent months", "in recent years",
    "as mentioned", "as stated", "as noted",
    "the project", "the initiative", "the program",
]

_COMPILED = [(p, re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)) for p in _VAGUE_PHRASES]


def check_vague_references(response: str, docs_concat: str) -> list[Warning]:
    warnings: list[Warning] = []
    for phrase, pattern in _COMPILED:
        if pattern.search(response) and not pattern.search(docs_concat):
            warnings.append(Warning(
                severity="medium",
                type="vague_reference",
                text=phrase,
                suggestion=f'"{phrase}" in the response has no specific referent in retrieved documents.',
            ))
    return warnings
