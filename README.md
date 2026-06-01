# RAGuard

![license](https://img.shields.io/badge/license-MIT-blue)
![last commit](https://img.shields.io/github/last-commit/serdaraytac/raguard)
![pypi](https://img.shields.io/pypi/v/raguard-py)
![python](https://img.shields.io/pypi/pyversions/raguard-py)

Runtime hallucination detection middleware for RAG applications.

`raguard` intercepts LLM responses and flags claims not supported by your retrieved documents — before they reach the user.

## When to use RAGuard

RAGuard is a middleware library — not a UI component. It integrates directly into your RAG pipeline. Call `verify()` after the LLM produces a response and before it is delivered to the user.

```
User → App → RAG retrieval → LLM → [verify()] → User
                                         ↓
                              Response + warnings surfaced
```

Use RAGuard when:
- Your RAG chatbot answers questions about documents, contracts, or policies where factual errors have real consequences (legal, financial, medical)
- You want runtime protection without adding LLM-call latency or API cost
- You need a drop-in signal that something in the response needs human review

## Install

```bash
pip install raguard-py
python -m spacy download en_core_web_sm
```

## Multi-language Support

raguard uses spaCy for named-entity recognition. The default model is `en_core_web_sm` (English). If your RAG pipeline runs on Turkish, French, or another language, you install the spaCy model yourself and pass `lang=` to `verify()`.

**Step 1 — install the spaCy model for your language:**

```bash
# Turkish
python -m spacy download tr_core_news_sm

# French
python -m spacy download fr_core_news_sm

# German
python -m spacy download de_core_news_sm

# Spanish
python -m spacy download es_core_news_sm
```

**Step 2 — pass `lang=` to `verify()`:**

```python
from raguard import verify

result = verify(
    query="Q3 2024 teslim tarihi nedir?",
    retrieved_docs=["Q2 projesi 15 Haziran'da tamamlandı."],
    llm_response="Q3 2024 teslim tarihi 30 Eylül 2024'tür.",
    lang="tr",
)
```

raguard maps the `lang` code to the standard spaCy model name. If you use a custom or fine-tuned model, pass the full model name directly:

```python
result = verify(..., lang="my_org/custom-tr-ner-model")
```

> **Note on Turkish NER quality:** `tr_core_news_sm` has limited accuracy on proper nouns and dates compared to `en_core_web_sm`. The date regex rules and vague-reference checks work language-independently and will still flag issues. Entity-level recall on Turkish text is beta. See [Limitations](#limitations).

## Usage

```python
from raguard import verify

result = verify(
    query="What is the Q3 2024 deadline?",
    retrieved_docs=["Q2 project was delivered on June 15. Next milestone is Q4 planning."],
    llm_response="The Q3 2024 deadline is September 30, 2024.",
)

print(result.action)                  # "review"
print(result.warnings[0].text)        # "September 30, 2024"
print(result.warnings[0].suggestion)  # '"September 30, 2024" not found in retrieved documents.'
```

`result.action` is either `"proceed"` (no high-severity issues) or `"review"` (at least one high-severity warning). Your application decides what to show the user.

## What it detects

| Type | Severity | Example |
|------|----------|---------|
| `unsupported_date` | high | Response says "September 30" — not in any doc |
| `missing_entity` | high | Response names "John Smith" — not in any doc |
| `vague_reference` | medium | Response says "the recent report" — phrase not in docs |
| `input_error` | high | Empty response, empty docs, or input exceeds size limit |

## VerifyResult shape

```python
@dataclass
class VerifyResult:
    action: Literal["proceed", "review"]
    warnings: list[Warning]
    summary: Summary  # {high: int, medium: int, low: int}

@dataclass
class Warning:
    severity: Literal["high", "medium", "low"]
    type: Literal["unsupported_date", "missing_entity", "vague_reference", "input_error"]
    text: str        # the problematic span in the response
    suggestion: str  # human-readable explanation
```

`verify()` never raises — guard-layer violations return `VerifyResult(action="review", warnings=[{type:"input_error", ...}])`.

## Multiple documents

Pass each chunk as a separate list item. Chunks are joined internally with a `\n\n---\n\n` separator. **Order matters:** boundary artifacts can occur if a number at the end of one chunk runs into text at the start of the next. Keep each chunk self-contained.

```python
result = verify(
    query="Who approved the budget?",
    retrieved_docs=[
        "The budget was reviewed in Q1.",
        "Alice Johnson approved the final budget on March 10.",
    ],
    llm_response="Alice Johnson approved the budget.",
)
# result.action == "proceed"
```

Source attribution per chunk is a v2 feature. Passing `list[Document]` instead of `list[str]` will be a breaking API change at that point.

## How it works

v1 is rule-based — no LLM calls, no API key required, p95 < 10ms:

1. **Guard layer** — validates inputs, returns early on empty or oversized content
2. **Date check** — extracts dates from the response with regex, looks for each in the docs
3. **Entity check** — runs spaCy NER on the response, checks every PERSON/ORG/GPE/LOC/MONEY entity against the docs; compound model numbers (e.g. "iPhone 16") are filtered to avoid false positives
4. **Vague reference check** — matches a curated phrase list against the response and docs

Rules are derived from public hallucination datasets (RAGTruth, HaluEval, TruthfulQA).

## Performance

Measured on Python 3.12, Apple M-series, after warm-up:

| Metric | Value |
|--------|-------|
| p50 | ~5.4ms |
| p95 | ~6.0ms |

First call loads the spaCy model (~200ms). Subsequent calls are fast.

## Limitations

- **Turkish NER quality is beta-level.** The `en_core_web_sm` model has limited accuracy on Turkish proper nouns and dates. A dedicated Turkish model will be added in v2.
- **Numerical hallucinations are not detected in v1.** If the LLM says 18% where the document says 15%, raguard will not flag it. Semantic numerical grounding requires an LLM pass (v2).
- **Compound model numbers may produce false positives.** Numbers inside product names like "iPhone 16" or "Windows 11" are filtered via noun-chunk analysis, but edge cases remain (e.g. when the parser fails to resolve the compound).
- **Semantic hallucinations are out of scope for v1.** A response that correctly uses entities but draws a wrong conclusion from the documents will not be flagged. This requires a grounding pass against each claim, planned for v2.

## Roadmap

**v1 — current**
- Rule-based engine: unsupported dates, missing entities, vague references
- Zero API cost, no LLM calls, p95 < 10ms
- English-first with compound noun filtering

**v2 — planned**
- Optional LLM semantic pass for claim-level grounding (OpenAI / Anthropic / local)
- Numerical hallucination detection
- False positive reduction via confidence scoring
- Turkish NER via Hugging Face `turkish-ner` model
- Per-chunk source attribution (`list[Document]` API)
- Warning deduplication and severity grouping

## License

MIT
