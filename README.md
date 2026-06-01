# raguard

Runtime hallucination detection middleware for RAG applications.

`raguard` intercepts LLM responses and flags claims not supported by your retrieved documents — before they reach the user.

## Install

```bash
pip install raguard
python -m spacy download en_core_web_sm
```

## Usage

```python
from raguard import verify

result = verify(
    query="What is the Q3 2024 deadline?",
    retrieved_docs=["Q2 project was delivered on June 15. Next milestone is Q4 planning."],
    llm_response="The Q3 2024 deadline is September 30, 2024.",
)

print(result.action)   # "review"
print(result.warnings[0].text)       # "September 30, 2024"
print(result.warnings[0].suggestion) # '"September 30, 2024" not found in retrieved documents.'
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
3. **Entity check** — runs spaCy NER on the response, checks every PERSON/ORG/GPE/LOC/MONEY entity against the docs
4. **Vague reference check** — matches a curated phrase list against the response and docs

Rules are derived from public hallucination datasets (RAGTruth, HaluEval, TruthfulQA). v2 will add an optional LLM grounding pass for semantic hallucinations the rule engine misses.

## Performance

Measured on Python 3.12, Apple M-series, after warm-up:

| Metric | Value |
|--------|-------|
| p50 | ~4.5ms |
| p95 | ~5.2ms |

First call loads the spaCy model (~200ms). Subsequent calls are fast.

## License

MIT
