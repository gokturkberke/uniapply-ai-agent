"""Grounded answer generation behind a provider-agnostic LLM abstraction.

The serving lane synthesizes an answer ONLY from retrieved context. When the
Retrieval Gate reports insufficient context, generation returns the exact refusal
string without calling the LLM. A deterministic ``MockLLMClient`` keeps tests fully
offline; the real ``AnthropicLLMClient`` is lazily constructed and uses the SDK's
native structured outputs (``messages.parse``, verified against anthropic>=0.109).
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

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


class AnthropicLLMClient:
    """Real client using the Anthropic SDK's native structured outputs.

    Lazily constructs the SDK client so importing this module never requires a key
    or network. ``api_key=None`` lets the SDK resolve ``ANTHROPIC_API_KEY`` from the
    environment.
    """

    def __init__(self, *, model: str, api_key: str | None, max_tokens: int) -> None:
        self._model = model
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._client = None  # type: ignore[var-annotated]

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(self, *, system: str, user: str, output_model: type[T]) -> T:
        response = self._get_client().messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=output_model,
        )
        for block in response.content:
            if block.type == "text" and block.parsed_output is not None:
                return block.parsed_output
        raise ValueError(
            f"Anthropic returned no parsed output (stop_reason={response.stop_reason})"
        )


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
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            max_tokens=settings.llm_max_tokens,
        )
    raise ValueError(f"unknown llm_provider: {settings.llm_provider!r}")


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
    context = "\n\n---\n\n".join(blocks) if blocks else "(no context)"

    user = f"Question:\n{question}\n\nContext:\n{context}"
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

    if not retrieval_result.sufficient_context or not retrieval_result.parents:
        return _refusal_answer()

    system, user = build_grounded_prompt(question, retrieval_result)
    answer = llm_client.generate(system=system, user=user, output_model=GroundedAnswer)

    if answer.insufficient_context:
        return _refusal_answer()

    allowed_sources = {parent.source_id for parent in retrieval_result.parents}
    grounded_citations = [c for c in answer.citations if c.source_id in allowed_sources]
    return answer.model_copy(update={"citations": grounded_citations})
