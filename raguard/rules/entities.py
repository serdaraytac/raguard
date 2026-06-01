from __future__ import annotations
from typing import TYPE_CHECKING
from ..models import Warning

if TYPE_CHECKING:
    import spacy

_DEFAULT_MODELS: dict[str, str] = {
    "en": "en_core_web_sm",
    "tr": "tr_core_news_sm",
    "fr": "fr_core_news_sm",
    "de": "de_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "nl": "nl_core_news_sm",
    "pt": "pt_core_news_sm",
}

_nlp_cache: dict[str, object] = {}


def _get_nlp(lang: str = "en"):
    if lang not in _nlp_cache:
        import spacy  # noqa: F811
        model = _DEFAULT_MODELS.get(lang, lang)  # fall back to lang as model name
        try:
            # parser enabled: required for noun_chunks (compound cardinal detection)
            _nlp_cache[lang] = spacy.load(model, disable=["lemmatizer"])
        except OSError:
            raise RuntimeError(
                f"spaCy model '{model}' not found. "
                f"Run: python -m spacy download {model}"
            )
    return _nlp_cache[lang]


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


def extract_entities(text: str, lang: str = "en") -> set[str]:
    nlp = _get_nlp(lang)
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


def check_entities(response: str, docs_concat: str, lang: str = "en") -> list[Warning]:
    response_entities = extract_entities(response, lang=lang)
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
