"""Tests for the local OpenAI-compatible LLM provider (offline via httpx.MockTransport)."""

import httpx
import pytest

from app.core.config import Settings
from app.rag.evaluation import FaithfulnessVerdict, judge_faithfulness
from app.rag.generation import (
    AnthropicLLMClient,
    Citation,
    GroundedAnswer,
    LLMOutputError,
    LocalOpenAICompatibleLLMClient,
    MockLLMClient,
    REFUSAL_MESSAGE,
    _extract_json,
    _refusal_answer,
    generate_grounded_answer,
    get_llm_client,
    safe_generate,
)
from app.rag.metadata import Chunk, Language, ParentSection, SourceAuthority
from app.rag.retrieval import RetrievalResult, RetrievedChunk

VALID_ANSWER_JSON = (
    '{"answer": "IELTS 6.5 overall is required.", '
    '"citations": [{"source_id": "alpha-src", "heading_path": ["Language Requirements"]}], '
    '"insufficient_context": false, "confidence": 0.9}'
)


def _local_client(handler) -> LocalOpenAICompatibleLLMClient:  # type: ignore[no-untyped-def]
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://local.test/v1"
    )
    return LocalOpenAICompatibleLLMClient(
        base_url="http://local.test/v1",
        model="qwen3:4b",
        api_key="ollama",
        max_tokens=256,
        http_client=http_client,
    )


def _content_client(content: str) -> LocalOpenAICompatibleLLMClient:
    return _local_client(
        lambda request: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
    )


def _result(*, sufficient: bool) -> RetrievalResult:
    parent = ParentSection(
        parent_id="alpha-src::section::000",
        source_id="alpha-src",
        heading_path=["Language Requirements"],
        text="IELTS 6.5 overall is required.",
    )
    chunk = Chunk(
        chunk_id="alpha-src::0000",
        parent_id=parent.parent_id,
        source_id="alpha-src",
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        source_authority=SourceAuthority.primary,
        lang=Language.en,
        country_scope=["all"],
        heading_path=["Language Requirements"],
        text="IELTS 6.5",
        token_estimate=2,
    )
    return RetrievalResult(
        query="q",
        university_slug="uni-alpha",
        programme_slug="msc-data-science",
        hits=[RetrievedChunk(chunk=chunk, score=0.8)],
        sufficient_context=sufficient,
        top_score=0.8,
        parents=[parent],
    )


# --- happy path + tolerance ------------------------------------------------

def test_happy_path_parses_and_validates() -> None:
    client = _content_client(VALID_ANSWER_JSON)

    answer = client.generate(system="s", user="u", output_model=GroundedAnswer)

    assert isinstance(answer, GroundedAnswer)
    assert answer.answer == "IELTS 6.5 overall is required."
    assert answer.citations[0].source_id == "alpha-src"


def test_tolerates_fenced_json_and_prose() -> None:
    content = f"Sure, here you go:\n```json\n{VALID_ANSWER_JSON}\n```\nHope that helps!"
    client = _content_client(content)

    answer = client.generate(system="s", user="u", output_model=GroundedAnswer)

    assert answer.answer == "IELTS 6.5 overall is required."


def test_extract_json_helpers() -> None:
    assert _extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _extract_json('prefix {"a": 1} suffix') == '{"a": 1}'
    with pytest.raises(LLMOutputError):
        _extract_json("no json here")


# --- failure modes -> LLMOutputError ---------------------------------------

def test_malformed_response_shape_raises() -> None:
    client = _local_client(lambda request: httpx.Response(200, json={"unexpected": "shape"}))

    with pytest.raises(LLMOutputError):
        client.generate(system="s", user="u", output_model=GroundedAnswer)


def test_http_error_raises() -> None:
    client = _local_client(lambda request: httpx.Response(500, json={"error": "boom"}))

    with pytest.raises(LLMOutputError):
        client.generate(system="s", user="u", output_model=GroundedAnswer)


def test_invalid_json_content_raises() -> None:
    client = _content_client("{not valid json,,,}")

    with pytest.raises(LLMOutputError):
        client.generate(system="s", user="u", output_model=GroundedAnswer)


def test_schema_invalid_content_raises() -> None:
    client = _content_client('{"answer": "only this field"}')  # missing required fields

    with pytest.raises(LLMOutputError):
        client.generate(system="s", user="u", output_model=GroundedAnswer)


# --- safe fallback ---------------------------------------------------------

def test_safe_generate_returns_fallback_on_llm_output_error() -> None:
    client = _content_client("not json")
    fallback = _refusal_answer()

    result = safe_generate(
        client, system="s", user="u", output_model=GroundedAnswer, fallback=fallback
    )

    assert result is fallback


def test_generate_grounded_answer_refuses_on_local_failure() -> None:
    client = _content_client("garbage, not json")

    answer = generate_grounded_answer("q", _result(sufficient=True), llm_client=client)

    assert answer.insufficient_context is True
    assert answer.answer == REFUSAL_MESSAGE


def test_judge_falls_back_to_unsupported_on_local_failure() -> None:
    client = _content_client("not parseable")

    verdict = judge_faithfulness("q", "some answer", _result(sufficient=True), judge_client=client)

    assert verdict.supported is False


# --- provider selection (existing paths unaffected) ------------------------

def test_get_llm_client_selects_local() -> None:
    client = get_llm_client(Settings(llm_provider="local_openai"))
    assert isinstance(client, LocalOpenAICompatibleLLMClient)


def test_get_llm_client_mock_and_anthropic_unaffected() -> None:
    assert isinstance(get_llm_client(Settings(llm_provider="mock")), MockLLMClient)
    assert isinstance(get_llm_client(Settings(llm_provider="anthropic")), AnthropicLLMClient)
