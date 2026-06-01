from __future__ import annotations
from typing import TYPE_CHECKING
from ..models import Warning

if TYPE_CHECKING:
    import spacy

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy  # noqa: F811
        try:
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
        except OSError:
            raise RuntimeError(
                "spaCy model not found. Run: python -m spacy download en_core_web_sm"
            )
    return _nlp


# Entity types worth cross-checking (DATE handled separately by dates.py)
_TARGET_LABELS = {"PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "MONEY", "CARDINAL", "ORDINAL"}


def extract_entities(text: str) -> set[str]:
    nlp = _get_nlp()
    doc = nlp(text)
    return {ent.text.strip() for ent in doc.ents if ent.label_ in _TARGET_LABELS}


def check_entities(response: str, docs_concat: str) -> list[Warning]:
    response_entities = extract_entities(response)
    warnings: list[Warning] = []

    for entity in response_entities:
        if entity.lower() not in docs_concat.lower():
            warnings.append(Warning(
                severity="high",
                type="missing_entity",
                text=entity,
                suggestion=f'"{entity}" not found in retrieved documents. This may be hallucinated.',
            ))
    return warnings
