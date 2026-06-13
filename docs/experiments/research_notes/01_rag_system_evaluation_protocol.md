# RAG System Evaluation Protocol: Quality Assurance for Admissions Intelligence

## 1. Strategic Foundation: The Imperative for RAG Evaluation

In the high-stakes domain of university admissions, the margin for error is non-existent. The distinction between an experimental chatbot and a production-grade AI agent lies in its evaluation framework. Misinformation regarding application deadlines or misinterpreted document protocols carries profound legal and academic risks, potentially derailing an applicant’s career and exposing the institution to liability. Because LLMs are inherently non-deterministic, they cannot be deployed in this sector without a protocol that transforms probabilistic outputs into a mathematically verifiable information service.

The primary objective of this protocol is to ensure that the UniApply AI Agent functions as a reliable information assistant. By implementing a rigorous quality assurance pipeline, we move beyond subjective "vibe checks" toward a system where every claim is grounded in official evidence and every failure is programmatically detectable. This reliability is anchored in the "RAG Triad" and the "LLM-as-a-Judge" paradigm, providing the engineering rigor necessary for admissions intelligence.

## 2. The RAG Triad: Core Quality Metrics

The strategic importance of the "RAG Triad" lies in its ability to isolate failures within the pipeline. By decoupling the retrieval stage (finding the evidence) from the generation stage (synthesizing the answer), we can diagnose whether a hallucination is the result of poor data acquisition or a failure in model reasoning.

### Core Quality Metrics

- **Contextual Relevancy:** Measures the alignment between the user query and the retrieved document chunks. This metric penalizes redundant or irrelevant data. For instance, if a user asks about "TU Munich Master's fees," retrieving undergraduate data for RWTH Aachen is a failure that increases noise and token costs.
- **Faithfulness (Groundedness):** Verifies that all claims are derived strictly from the retrieved context. In admissions, this is critical for factual granularity—for example, ensuring the system accurately reports that uni-assist fees are €75.00 for the first course and €30.00 for each additional course, rather than a generic or hallucinated flat fee.
- **Context Precision & Recall:** Evaluates whether the retrieval stage successfully captured all necessary evidence (Recall) and whether the most relevant documents are ranked at the top (Precision). High precision is achieved through technical interventions like Reciprocal Rank Fusion (RRF) or Cross-encoder Reranking.
- **Spatial Source Citations:** A core requirement for auditability. Unlike standard RAG, which may only list a URL, this protocol requires spatial anchoring—mapping claims to specific page numbers or bounding boxes within a PDF. This necessitates layout-aware parsing using tools like Docling or LlamaParse to preserve tabular and hierarchical structures.

### RAG Triad Impact Analysis

| Metric | Failure Mode Detected | Business & User Risk |
|---|---|---|
| Contextual Relevancy | Poor Retrieval / Noise | Increased latency/cost; model confusion leading to incorrect advice. |
| Faithfulness | Hallucination | Legal liability; financial loss for applicants; violation of § 44b UrhG. |
| Context Recall | Missing Information | Applicant misses critical deadlines (e.g., the 4–6 week VPD window). |
| Context Precision | Poor Document Ranking | Critical instructions are "lost in the middle" of the context window. |

## 3. The LLM-as-a-Judge Paradigm

To achieve the scalability required for professional deployment, we shift from manual review to automated, high-tier verification. This paradigm uses an advanced model (the "Judge") to score the performance of the primary RAG agent against the metrics defined in the Triad.

### Implementation Requirements

- **High-Tier Judges:** We utilize advanced models such as GPT-4o-mini or Llama 3 (deployed via Ollama) to evaluate the primary system. The Judge is provided with the Query, the Context, and the Answer to assign objective scores.
- **Zero-Cost Evaluation Loops:** Local judge frameworks (e.g., DeepEval or RAGAS) are implemented to maintain continuous verification during development. This allows for rapid iteration on chunking strategies (e.g., 400–700 tokens with 50–100 token overlap) without incurring external API costs.
- **Auditability:** The Judge must provide a "reasoning" string for each score, allowing architects to analyze why a specific response was flagged as unfaithful or irrelevant.

## 4. Synthetic Dataset Architecture and Generation

A "gold set" of data provides the ground-truth baseline required for the system. We generate a 50-question synthetic dataset using the source corpus (official university pages, uni-assist, and DAAD guidelines).

### Synthetic Question Categories

- **Simple Factual:** Direct retrieval of specific data points (e.g., "What is the processing fee for a second course application at uni-assist?").
- **Multi-hop:** Reasoning across multiple documents (e.g., comparing uni-assist’s 4–6 week VPD processing time against a specific TU Munich application deadline).
- **Reformulation:** Stress-testing robustness against poor phrasing and typos (e.g., "need 2 apply munich when?").
- **Out-of-Scope:** Critical testing of refusal behavior. The system must refuse irrelevant queries, such as "What are the study visa rules for Canada?", since the corpus is Germany-focused.

### Ground Truth Triplet Structure (JSONL)

The dataset is stored in a structured JSONL format to enable automated comparison:

```json
{
  "question": "How long does uni-assist take to process a VPD?",
  "context": "According to uni-assist, evaluation results usually arrive in 4 to 6 weeks from the day the application is received. Applicants should apply at least 8 weeks before the deadline.",
  "answer": "Processing typically takes 4 to 6 weeks. It is recommended to apply at least 8 weeks in advance.",
  "metadata": {
    "source": "uni-assist_procedural_guide",
    "page": 4
  }
}
```

## 5. Guardrails: Rejection Logic and Refusal Behavior

In an admissions context, "Grounding or Refusal" is the primary defense against hallucination. The system must be engineered to favor silence over inaccuracy.

### The Grounded-Answering Prompt Contract

The LLM must adhere to a strict six-point contract enforced via system prompts:

1. **Exclusive Reliance:** Synthesize answers using only the provided, retrieved context.
2. **Source Hierarchy:** Prefer primary university sources over secondary orientation sources (DAAD or uni-assist).
3. **Conflict Resolution:** If information is conflicting, state the discrepancy explicitly (e.g., "DAAD lists X, but the University portal states Y").
4. **Mandatory Refusal Phrasing:** Use the exact string "Information not found in the official documents" if the context is insufficient.
5. **No Inference:** Strictly prohibit inferring eligibility, admission outcomes, or legal certainties.
6. **Structured-First Output:** Return a structured JSON response (containing answer, citations, and confidence) before rendering text to the user.

### The Retrieval Gate

A "Retrieval Gate" mechanism serves as the single biggest hallucination reducer. It calculates a threshold score for contextual relevancy. If the retrieved chunks do not meet the minimum threshold, the "Grounded or Refuse" behavior is triggered, preventing the generator from attempting to formulate an answer from irrelevant data.

## 6. Operational Metrics and Implementation Reporting

A professional RAG implementation balances accuracy with engineering efficiency, including considerations of German copyright law (§ 44b UrhG) and current case law (e.g., Kneschke v. LAION e.V. regarding machine-readable opt-outs).

### Quality Assurance Dashboard

| Metric Category | Target Threshold | Verification Tool |
|---|---:|---|
| Faithfulness | > 95% | RAGAS / DeepEval |
| Context Precision | > 90% | RAGAS |
| Context Recall | > 90% | RAGAS |
| Latency (Streaming) | < 200ms (TTFT) | FastAPI / LangSmith |
| Hallucination Rate | < 2% | LLM-as-a-Judge |

### Evaluation Report Requirements

A professional portfolio submission must include an Evaluation Report detailing:

- **Corpus Scope:** The specific programs and official URLs ingested.
- **Parsing Logic:** Evidence of layout-aware parsing (e.g., Docling) to handle complex academic tables.
- **Iterative Improvements:** Documentation of how adding a reranker or RRF impacted Context Precision scores.
- **Failure Case Analysis:** Analysis of at least three cases where the system correctly refused an out-of-scope query.

### Risks and Limitations

This system is an experimental information assistant and is governed by the following mandatory disclaimers:

1. **Not an Authority:** This tool is for information support only and is not an official admissions decision tool.
2. **Precedence of Sources:** Official university websites, regulations, and admissions offices take absolute precedence.
3. **Variation of Rules:** Requirements may vary significantly by applicant background, nationality, prior degree, and application route.
4. **Information Staleness:** Admissions data (fees, deadlines) changes annually; users must verify rules before submitting applications.
5. **Sensitive Data:** Users must not upload sensitive personal data (e.g., passports) in public demos or screenshots.
6. **Review Requirement:** All generated artifacts, including email drafts, must be reviewed by the applicant for accuracy before use.
