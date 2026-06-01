from .models import VerifyResult, Summary, Warning
from .rules.dates import check_dates
from .rules.entities import check_entities
from .rules.vague import check_vague_references

# ~128k chars ≈ safe upper bound before NER becomes slow
_MAX_CHARS = 128_000
_CHUNK_SEPARATOR = "\n\n---\n\n"


def verify(
    query: str,
    retrieved_docs: list[str],
    llm_response: str,
    lang: str = "en",
) -> VerifyResult:
    """Check llm_response for claims not supported by retrieved_docs.

    lang: BCP-47 language code for NER model selection (default "en").
    The spaCy model for the chosen language must be installed separately.
    See README → Multi-language Support.

    retrieved_docs order matters: chunks are joined with a separator, so
    boundary artifacts are possible if chunks are not self-contained.
    Source attribution per chunk is a v2 feature.
    """
    # Guard layer — never raises, always returns VerifyResult
    if not llm_response or not llm_response.strip():
        return VerifyResult.input_error("llm_response is empty.")
    if not retrieved_docs:
        return VerifyResult.input_error("retrieved_docs is empty.")

    docs_concat = _CHUNK_SEPARATOR.join(d.strip() for d in retrieved_docs if d.strip())
    if not docs_concat:
        return VerifyResult.input_error("All retrieved_docs are empty.")

    total_chars = len(llm_response) + len(docs_concat)
    if total_chars > _MAX_CHARS:
        return VerifyResult(
            action="review",
            warnings=[Warning(
                severity="high",
                type="input_error",
                text=f"Input size {total_chars} chars exceeds limit {_MAX_CHARS}.",
                suggestion="Split retrieved_docs into smaller batches.",
            )],
            summary=Summary(high=1),
        )

    warnings: list[Warning] = []
    warnings.extend(check_dates(llm_response, docs_concat))
    warnings.extend(check_entities(llm_response, docs_concat, lang=lang))
    warnings.extend(check_vague_references(llm_response, docs_concat))

    summary = Summary(
        high=sum(1 for w in warnings if w.severity == "high"),
        medium=sum(1 for w in warnings if w.severity == "medium"),
        low=sum(1 for w in warnings if w.severity == "low"),
    )
    action = "review" if summary.high > 0 else "proceed"

    return VerifyResult(action=action, warnings=warnings, summary=summary)
