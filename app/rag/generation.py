"""Grounded answer generation behind a provider-agnostic LLM abstraction.

The serving lane synthesizes an answer ONLY from retrieved context. When the
Retrieval Gate reports insufficient context, generation returns the exact refusal
string without calling the LLM. A deterministic ``MockLLMClient`` keeps tests fully
offline; ``LocalOpenAICompatibleLLMClient`` calls a local OpenAI-compatible server
(Ollama / LM Studio) and validates the JSON reply against the schema.
"""

import json
import re
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.rag.retrieval import RetrievalResult

REFUSAL_MESSAGE = "Information not found in the official documents."
DISCLAIMER = (
    "This is informational support only, not official admissions advice. Verify all "
    "requirements, deadlines, and fees with the official university portal and uni-assist "
    "before applying."
)

T = TypeVar("T", bound=BaseModel)


class Citation(BaseModel):
    """A source the answer is grounded in."""

    source_id: str
    heading_path: list[str]


class GroundedAnswer(BaseModel):
    """Structured grounded answer (the LLM's structured-output schema)."""

    answer: str
    citations: list[Citation]
    insufficient_context: bool
    confidence: float


class LLMClient(Protocol):
    """Generates a validated structured object from a system + user prompt."""

    def generate(self, *, system: str, user: str, output_model: type[T]) -> T: ...


class MockLLMClient:
    """Deterministic, offline client that returns a canned response (for tests)."""

    def __init__(self, response: BaseModel) -> None:
        self._response = response

    def generate(self, *, system: str, user: str, output_model: type[T]) -> T:
        return self._response  # type: ignore[return-value]


class LLMOutputError(Exception):
    """Raised when a provider's raw output cannot be parsed/validated into the schema."""


def _extract_json(text: str) -> str:
    """Extract one JSON object from model text, tolerating ```json fences / prose."""

    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return stripped[start : end + 1]
    raise LLMOutputError("no JSON object found in model output")


class LocalOpenAICompatibleLLMClient:
    """OpenAI-compatible chat client (Ollama / LM Studio) over httpx.

    Local models are unreliable with strict structured output, so the JSON schema is
    embedded in the prompt and the reply is JSON-extracted + Pydantic-validated. Any
    HTTP, response-shape, JSON-decode, or schema-validation failure is converted to
    ``LLMOutputError`` so callers can fall back to a grounded refusal. No other
    exception type is produced here.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        max_tokens: int,
        temperature: float | None = None,
        seed: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._seed = seed
        self._http_client = http_client

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=httpx.Timeout(120.0),
            )
        return self._http_client

    def generate(self, *, system: str, user: str, output_model: type[T]) -> T:
        system_with_schema = (
            f"{system}\n\nReturn ONLY a single JSON object that conforms to this JSON "
            f"Schema. No prose, no markdown fences:\n{json.dumps(output_model.model_json_schema())}"
        )
        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system_with_schema},
                {"role": "user", "content": user},
            ],
        }
        # Pin sampling only when configured; ``is not None`` so temperature=0.0 is kept.
        if self._temperature is not None:
            body["temperature"] = self._temperature
        if self._seed is not None:
            body["seed"] = self._seed
        try:
            response = self._client().post("/chat/completions", json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMOutputError(f"local LLM request/response failure: {exc}") from exc

        if not isinstance(content, str):
            raise LLMOutputError("local LLM returned non-string message content")

        try:
            return output_model.model_validate_json(_extract_json(content))
        except ValidationError as exc:
            raise LLMOutputError(f"local LLM output failed schema validation: {exc}") from exc


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Return the LLM client selected by ``llm_provider``."""

    settings = settings or get_settings()
    if settings.llm_provider == "mock":
        return MockLLMClient(
            GroundedAnswer(
                answer="[mock] grounded answer",
                citations=[],
                insufficient_context=False,
                confidence=1.0,
            )
        )
    if settings.llm_provider == "local_openai":
        return LocalOpenAICompatibleLLMClient(
            base_url=settings.local_llm_base_url,
            model=settings.local_llm_model,
            api_key=settings.local_llm_api_key,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.local_llm_temperature,
            seed=settings.local_llm_seed,
        )
    raise ValueError(f"unknown llm_provider: {settings.llm_provider!r}")


def safe_generate(
    llm_client: LLMClient,
    *,
    system: str,
    user: str,
    output_model: type[T],
    fallback: T,
) -> T:
    """Call ``generate``, returning ``fallback`` only on ``LLMOutputError``.

    Only the local provider raises ``LLMOutputError`` (parse/validation failure);
    ``MockLLMClient`` never does, so its behavior and unexpected errors are unaffected.
    """

    try:
        return llm_client.generate(system=system, user=user, output_model=output_model)
    except LLMOutputError:
        return fallback


def format_context(retrieval_result: RetrievalResult) -> str:
    """Format retrieved parent sections into a labeled context block for prompts.

    Shared by grounded Q&A and the artifact generators. Each block is labeled with
    its source id, authority (primary/secondary), and heading path.
    """

    authority_by_source = {
        hit.chunk.source_id: hit.chunk.source_authority.value
        for hit in retrieval_result.hits
    }
    blocks: list[str] = []
    for parent in retrieval_result.parents:
        heading = " > ".join(parent.heading_path) or "(no heading)"
        authority = authority_by_source.get(parent.source_id, "unknown")
        blocks.append(
            f"[source: {parent.source_id} | authority: {authority} | section: {heading}]\n"
            f"{parent.text}"
        )
    return "\n\n---\n\n".join(blocks) if blocks else "(no context)"


def is_groundable(retrieval_result: RetrievalResult) -> bool:
    """True when there is grounding context to answer from (gate passed + parents present)."""

    return retrieval_result.sufficient_context and bool(retrieval_result.parents)


def ground_citations(
    citations: list[Citation], retrieval_result: RetrievalResult
) -> list[Citation]:
    """Drop citations whose source id is not present in the retrieved context."""

    allowed_sources = {parent.source_id for parent in retrieval_result.parents}
    return [citation for citation in citations if citation.source_id in allowed_sources]


def build_grounded_prompt(question: str, retrieval_result: RetrievalResult) -> tuple[str, str]:
    """Build the (system, user) prompt enforcing the grounded-answering contract."""

    system = (
        "You are UniApply, an assistant for international applicants to German Master's "
        "programmes. Answer ONLY using the provided context from official admission "
        "documents. Rules:\n"
        "1. Use only the provided context; do not use outside or prior knowledge.\n"
        "2. Prefer primary university sources over secondary ones (uni-assist, DAAD) when "
        "they conflict; each source is labeled with its authority.\n"
        "3. If sources conflict, state the discrepancy explicitly rather than choosing "
        "silently.\n"
        "4. If the context lacks enough information, set insufficient_context to true and "
        f'set answer to exactly: "{REFUSAL_MESSAGE}"\n'
        "5. Do not infer eligibility, admission outcomes, or legal certainties.\n"
        "6. Cite only sources present in the context, by their source id."
    )
    user = f"Question:\n{question}\n\nContext:\n{format_context(retrieval_result)}"
    return system, user


def _refusal_answer() -> GroundedAnswer:
    """The canonical refusal: exact message, no citations, zero confidence."""

    return GroundedAnswer(
        answer=REFUSAL_MESSAGE,
        citations=[],
        insufficient_context=True,
        confidence=0.0,
    )


def generate_grounded_answer(
    question: str,
    retrieval_result: RetrievalResult,
    *,
    llm_client: LLMClient,
) -> GroundedAnswer:
    """Synthesize a grounded answer, or refuse when context is insufficient.

    Refuses without calling the LLM when the Retrieval Gate fails OR there is no
    grounding context (e.g. parent/artifact drift left ``parents`` empty). Otherwise
    calls the LLM; if the model itself reports insufficient context, the answer is
    normalized to the exact refusal; finally any citation whose source id was not in
    the retrieved context is dropped (guard against hallucinated citations).
    """

    if not is_groundable(retrieval_result):
        return _refusal_answer()

    system, user = build_grounded_prompt(question, retrieval_result)
    answer = safe_generate(
        llm_client,
        system=system,
        user=user,
        output_model=GroundedAnswer,
        fallback=_refusal_answer(),
    )

    # A grounded answer must cite at least one in-context source. If the model
    # reported insufficient context, or none of its citations survive the grounding
    # filter, refuse rather than return an uncited answer.
    grounded = ground_citations(answer.citations, retrieval_result)
    if answer.insufficient_context or not grounded:
        return _refusal_answer()

    return answer.model_copy(update={"citations": grounded})
