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
            # parser enabled: required for noun_chunks (compound cardinal detection)
            _nlp = spacy.load("en_core_web_sm", disable=["lemmatizer"])
        except OSError:
            raise RuntimeError(
                "spaCy model not found. Run: python -m spacy download en_core_web_sm"
            )
    return _nlp


# Entity types worth cross-checking (DATE handled separately by dates.py)
_TARGET_LABELS = {"PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "MONEY", "CARDINAL", "ORDINAL"}

# Head POS/entity types that signal a compound proper-noun chunk
_COMPOUND_HEAD_POS = {"PROPN"}
_COMPOUND_HEAD_ENT = {"PRODUCT", "ORG", "PERSON"}


def _compound_cardinal_indices(doc) -> frozenset[int]:
    """Return token indices of CARDINAL numbers that are part of a compound
    proper-noun chunk (e.g. '16' in 'iPhone 16', '11' in 'Windows 11').

    A CARDINAL token is considered compound when:
      - it falls inside a noun chunk, AND
      - that chunk's syntactic head has POS PROPN or entity type PRODUCT/ORG/PERSON.
    """
    compound: set[int] = set()
    for chunk in doc.noun_chunks:
        head = chunk.root
        if head.pos_ in _COMPOUND_HEAD_POS or head.ent_type_ in _COMPOUND_HEAD_ENT:
            for tok in chunk:
                if tok.pos_ == "NUM":
                    compound.add(tok.i)
    return frozenset(compound)


def extract_entities(text: str) -> set[str]:
    nlp = _get_nlp()
    doc = nlp(text)
    compound = _compound_cardinal_indices(doc)
    return {
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ in _TARGET_LABELS
        and not (
            ent.label_ == "CARDINAL"
            and any(tok.i in compound for tok in ent)
        )
    }


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
