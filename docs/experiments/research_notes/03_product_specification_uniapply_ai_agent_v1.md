# Product Specification: UniApply AI Agent (V1)

## 1. Executive Strategic Vision & Scope

In the high-stakes domain of international university admissions, accuracy and provenance are non-negotiable. Traditional "broad-but-shallow" AI agents often struggle with the granular, frequently changing regulations of specific academic systems, leading to hallucinations that can jeopardize a student's application. The UniApply AI Agent adopts a "narrow-but-deep" strategic approach, focusing exclusively on the German higher education landscape. By constraining the scope to a single country and a curated set of official sources, the system builds engineering credibility and user trust through verifiable, source-grounded intelligence rather than probabilistic guessing.

The decision to focus strictly on international Master’s applicants to Germany is driven by the reliability and structure of German academic data. Centralized entities such as DAAD and uni-assist, alongside specific university portals (e.g., TU Munich), provide authoritative—yet complex—frameworks. A multi-country scope increases the risk of blending incompatible admission rules; by mastering localized requirements, ECTS credit prerequisites, and specific document protocols like the Vorprüfungsdokumentation (VPD), this V1 release establishes a robust foundation of reliability.

### Product Mission

To provide a source-grounded, API-first RAG assistant that empowers international Master’s applicants to navigate the German admission process with high-fidelity information derived exclusively from official university and governmental sources.

### V1 Core Capabilities

- **Document Ingestion:** Layout-aware processing of curated official URLs and PDFs into normalized Markdown.
- **Source-Grounded Q&A:** A /ask endpoint providing answers supported by chunk-level inline citations.
- **Structured Checklist Generation:** Creation of program-specific application checklists in valid JSON format.
- **Missing-Document Detection:** Comparison of user-provided profiles against retrieved requirements to identify gaps.
- **Source-Anchored Email Drafting:** Generation of formal correspondence to admission offices, explicitly referencing retrieved facts.

This focused scope ensures that the underlying technical architecture remains modular and production-ready, prioritizing reliability over feature bloat.

## 2. Technical Architecture: The Modular "Boring" Stack

The engineering philosophy behind UniApply AI Agent is "intentional simplicity." This project utilizes a production-ready backbone to ensure stability and maintainability, prioritizing performance and type safety over the complexity of experimental agentic libraries.

The system employs a Two-Lane Architecture, separating heavy lifting from user interaction:

## 1. Ingestion Lane (Offline): Fetches raw sources via polite-fetch, normalizes content into Markdown, segments text into semantic chunks, generates vector embeddings, and stores them in Qdrant with rich metadata.
## 2. Serving Lane (Online): Processes user queries by applying metadata filters, performing hybrid retrieval, and utilizing an LLM to generate structured, grounded responses.

### Core Tech Stack Rationale

| Component | Selection (V1) | Engineering Justification |
| --- | --- | --- |
| Backend API | FastAPI | Native async support, automatic OpenAPI documentation, and high performance. |
| Data Validation | Pydantic v2 | Ensures strict type safety and enables reliable JSON schema generation for LLM outputs. |
| Vector Database | Qdrant | Native support for hybrid (dense/sparse) search and Reciprocal Rank Fusion (RRF); robust metadata filtering. |
| Parsing | Docling / PyMuPDF4LLM | Converts complex layouts into normalized Markdown, preserving structural elements like ECTS tables. |
| LLM / Embeddings | OpenAI | Industry-leading support for structured outputs and consistent multilingual embedding dimensions. |

### Directory Structure & Abstraction

A Provider Abstraction layer ensures the system remains model-agnostic, allowing for future transitions to local models (e.g., Ollama) or alternative vendors without modifying core business logic.

```text
uniapply_agent/
├── app/
│   ├── api/             # FastAPI routes (/ask, /checklist, /ingest)
│   ├── core/            # Configuration, settings, and logging
│   ├── models/          # Pydantic schemas for request/response validation
│   ├── services/
│   │   ├── rag/         # Ingestion, Retrieval, and Generation logic
│   │   └── providers/   # Abstracted LLM and Embedding interfaces
├── data/                # Raw source archive and local index persistence
├── tests/               # Unit and integration tests (RAGAS harness)
└── scripts/             # Ingestion and evaluation utility scripts
```

## 3. Data Engineering & Ingestion Pipeline

The integrity of the assistant depends on an "Official-First" data strategy. Primary information is sourced directly from university portals, while secondary sources like DAAD and uni-assist serve as fallback context.

### Legal Compliance & Sourcing Strategy

German admissions data is subject to strict copyright frameworks. To align with § 44b UrhG (German Copyright Act), the system avoids aggressive automated crawling. Instead, it utilizes a "Manual-Download + Polite-Fetch" strategy. This ensures that the corpus is lawfully accessed and maintained for personal, non-commercial use, honoring machine-readable opt-outs and robots.txt directives.

### Triple-Layer Storage Strategy

## 1. Raw Layer: A reproducibility archive of original HTML and PDF files.
## 2. Normalized Layer: Content converted to Markdown to facilitate semantic chunking and preserve table structures.
## 3. Index Layer: Vectorized chunks in Qdrant with associated metadata manifests.

### Metadata Schema Strategy

| Field | Description | Strategic Value |
| --- | --- | --- |
| university_slug | Unique ID for the university | Prevents mixing rules between different institutions. |
| programme_slug | Unique ID for the Master's program | Filters requirements specific to a field of study. |
| source_type | official_page, faq, pdf_guide | Prioritizes primary sources in the generation step. |
| url | The original source link | Required for verifiable user-facing citations. |
| last_updated | ISO timestamp of the last fetch | Manages info staleness; displayed to user for deadline safety. |
| country_scope | Target applicant origin (e.g., Non-EU) | Addresses differing requirements (e.g., APS certificates). |

## 4. Retrieval & Grounded Generation Strategy

UniApply AI Agent follows a "Retrieval-First, Prompt-Second" philosophy. The system's intelligence is derived from retrieved documents, while the LLM acts as a reasoning engine to synthesize that data.

### Advanced Retrieval Methodology

To navigate complex academic regulations, the system implements:

- **Parent-Document Retrieval:** The system stores small semantic chunks for high-precision search but passes the larger "parent" context block to the LLM to prevent context dilution.
- **Hybrid Search & RRF:** Combines dense semantic embeddings with sparse keyword search (BM25) to catch specific terms like "ECTS" or "VPD." Results are merged using Reciprocal Rank Fusion (RRF) to ensure mathematical ranking stability.

### Grounded Answering Contract

- Use only the provided retrieved context.
- Refuse to answer if context is insufficient or conflicting.
- Cite every claim with source anchors and explicitly display the last_updated timestamp to mitigate risk of outdated deadlines.

### Implementation of Structured Outputs

The system utilizes the Instructor library as the implementation layer for Pydantic/LLM integration. This ensures the LLM returns valid JSON for checklists and email drafts rather than free-form text, enabling deterministic interaction with the frontend.

## 5. 14-Day Implementation Roadmap

| Day | Build Task | Engineering Objective |
| --- | --- | --- |
| 1-2 | Foundation & Registry | Configure Pydantic schemas, env management, and seed official source registry. |
| 3-4 | Ingestion Pipeline | Implement layout-aware normalization to Markdown and Parent-Document chunking. |
| 5-6 | Vector Indexing | Deploy Qdrant via Docker; implement hybrid (dense/sparse) indexing with RRF. |
| 7 | Core RAG (/ask) | Build the serving endpoint with grounded retrieval and inline citations. |
| 8-10 | Structured Tools | Develop JSON endpoints using the Instructor library for checklists and email drafting. |
| 11-12 | Evaluation Harness | Measure performance using RAGAS (Faithfulness, Context Precision, Recall). |
| 13-14 | Testing & Portfolio | Finalize unit tests, documentation, and write the technical whitepaper. |

## 6. Evaluation Framework & Hallucination Guardrails

"Vibe checks" are insufficient for high-stakes admissions. The system employs a metric-driven approach using the RAGAS framework.

### The RAG Triad Metrics

## 1. Faithfulness: Verifies the answer is derived solely from the retrieved context.
## 2. Context Precision: Evaluates if the most relevant chunks are prioritized.
## 3. Context Recall: Ensures all necessary info was retrieved to answer the query.

Gold Dataset: Critical Test Cases

The system must pass these questions before V1-readiness:

## 1. "What is the application deadline for international applicants?"
## 2. "Is proof of English required for [Program X]?"
## 3. "Can I apply before my Bachelor’s degree is fully completed?"
## 4. "Do I need to use uni-assist or apply directly through the university portal?"
## 5. "What specific documents are required for the Preliminary Review Documentation (VPD)?"

## 7. Strategic Exclusions & Risk Mitigation

### V1 Non-Goals

- **Agentic Frameworks:** Avoidance of LangGraph or CrewAI to maintain deterministic reliability.
- **Live Web Crawling:** No dynamic scraping; use a curated, static source registry to ensure quality.
- **User Authentication:** No storage of sensitive personal data in the initial release.
- **OCR-Heavy Support:** Focus on digital-first PDFs and structured web pages.

### Legal & Ethical Disclaimer

UniApply AI Agent is a support assistant designed for informational purposes only. It is not an admissions authority. All users must verify deadlines, requirements, and protocols via official university portals and uni-assist. The system's output does not constitute a guarantee of admission. Information provided is based on data last updated on the timestamps provided in the citations.

This specification ensures a professional portfolio presentation that demonstrates mastery over RAG architecture, structured data extraction, and empirical AI evaluation.
