import pytest
from raguard import verify


DOCS_Q3 = ["Q2 project was delivered on June 15. Next milestone is Q4 planning."]
DOCS_PERSON = ["The report was written by the engineering team. No named authors listed."]
DOCS_CONTRACT = ["The agreement was signed in 2023. Terms are valid for two years."]


class TestDateHallucination:
    def test_date_not_in_docs_returns_review(self):
        result = verify(
            query="What is the Q3 2024 deadline?",
            retrieved_docs=DOCS_Q3,
            llm_response="The Q3 2024 deadline is September 30, 2024.",
        )
        assert result.action == "review"
        assert result.summary.high >= 1
        texts = [w.text for w in result.warnings]
        assert any("September 30" in t or "2024" in t for t in texts)

    def test_date_present_in_docs_proceeds(self):
        result = verify(
            query="When was Q2 delivered?",
            retrieved_docs=["Q2 project was delivered on June 15, 2024."],
            llm_response="Q2 was delivered on June 15, 2024.",
        )
        assert result.action == "proceed"
        assert result.summary.high == 0


class TestEntityHallucination:
    def test_named_person_not_in_docs_returns_review(self):
        result = verify(
            query="Who wrote the report?",
            retrieved_docs=DOCS_PERSON,
            llm_response="The report was written by John Smith.",
        )
        assert result.action == "review"
        assert any(w.type == "missing_entity" for w in result.warnings)

    def test_entity_present_in_docs_proceeds(self):
        result = verify(
            query="Who wrote the report?",
            retrieved_docs=["The report was written by John Smith in 2024."],
            llm_response="John Smith wrote the report.",
        )
        assert result.action == "proceed"


class TestVagueReference:
    def test_vague_phrase_not_in_docs_returns_warning(self):
        result = verify(
            query="What does the agreement say?",
            retrieved_docs=DOCS_CONTRACT,
            llm_response="According to the recent report, the contract is still valid.",
        )
        vague_warnings = [w for w in result.warnings if w.type == "vague_reference"]
        assert len(vague_warnings) >= 1

    def test_vague_phrase_in_docs_no_warning(self):
        result = verify(
            query="What did the recent report say?",
            retrieved_docs=["According to the recent report, revenue is up 10%."],
            llm_response="The recent report shows revenue is up 10%.",
        )
        vague_warnings = [w for w in result.warnings if w.type == "vague_reference"]
        assert len(vague_warnings) == 0


class TestGuardLayer:
    def test_empty_response_returns_input_error(self):
        result = verify(query="q", retrieved_docs=["some doc"], llm_response="")
        assert result.action == "review"
        assert result.warnings[0].type == "input_error"

    def test_empty_docs_returns_input_error(self):
        result = verify(query="q", retrieved_docs=[], llm_response="some response")
        assert result.action == "review"
        assert result.warnings[0].type == "input_error"

    def test_whitespace_only_docs_returns_input_error(self):
        result = verify(query="q", retrieved_docs=["   ", "\n"], llm_response="response")
        assert result.action == "review"
        assert result.warnings[0].type == "input_error"

    def test_oversized_input_returns_input_error(self):
        big = "x" * 130_000
        result = verify(query="q", retrieved_docs=[big], llm_response="response")
        assert result.action == "review"
        assert result.warnings[0].type == "input_error"


class TestCompoundCardinal:
    def test_model_number_not_flagged(self):
        # "16" in "iPhone 16" must not produce a missing_entity warning
        result = verify(
            query="Which phone is recommended?",
            retrieved_docs=["The iPhone 16 Pro was released in late 2024 and features improved cameras."],
            llm_response="We recommend the iPhone 16 Pro for its camera system.",
        )
        entity_texts = [w.text for w in result.warnings if w.type == "missing_entity"]
        assert "16" not in entity_texts, f"'16' falsely flagged as missing entity: {entity_texts}"

    def test_software_version_not_flagged(self):
        result = verify(
            query="What OS version is supported?",
            retrieved_docs=["Windows 11 is fully supported. Minimum requirement is Windows 10."],
            llm_response="The software runs on Windows 11 and Windows 10.",
        )
        entity_texts = [w.text for w in result.warnings if w.type == "missing_entity"]
        assert "11" not in entity_texts
        assert "10" not in entity_texts

    def test_standalone_number_still_flagged(self):
        # A bare CARDINAL not attached to a proper noun should still be caught
        result = verify(
            query="What is the headcount?",
            retrieved_docs=["The company has 150 employees."],
            llm_response="The company has 320 employees in three offices.",
        )
        # 320 is not in docs; 150 is — but 320 as a standalone cardinal should be caught
        entity_texts = [w.text for w in result.warnings if w.type == "missing_entity"]
        assert "320" in entity_texts


class TestMultiChunk:
    def test_entity_found_across_chunks(self):
        # Entity is in the second chunk — concat must find it
        result = verify(
            query="Who approved the budget?",
            retrieved_docs=[
                "The budget was reviewed in Q1.",
                "Alice Johnson approved the final budget on March 10.",
            ],
            llm_response="Alice Johnson approved the budget.",
        )
        assert result.action == "proceed"
