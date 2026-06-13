# Technical Architecture Design: UniApply RAG-Based Admissions Agent

## 1. Strategic System Overview

The UniApply Agent is engineered to address the high-stakes environment of German university admissions, where information is highly structured, legally sensitive, and subject to frequent updates. In this domain, relying on the "parametric memory" of a Large Language Model (LLM) is unacceptable due to the risk of hallucinations regarding deadlines or credit requirements. We prioritize a source-grounded Retrieval-Augmented Generation (RAG) system that treats external official documents as the absolute source of truth. This modular, "production-flavored" architecture is strategically superior to a broad autonomous agent; it emphasizes reliability, auditability, and a controlled scope over unpredictable reasoning loops.

### Core Objectives

- **Fact-Based Reliability:** Responses must be derived strictly from a curated corpus of official university documents.
- **Verifiable Citations:** Every claim must be backed by granular, chunk-level citations mapping to primary source PDFs and websites.
- **Refusal-First Posture:** The system is designed to refuse out-of-scope or ungrounded queries rather than inferring missing information.

### High-Level Schematic

The system is structured into a "Two-Lane" architecture to separate data preparation from real-time serving:

## 1. Offline Ingestion Lane: Handles the acquisition of source documents (HTML/PDF), normalization into structured Markdown, semantic vectorization, and storage in a vector database.
## 2. Online Serving Lane: Processes live user queries through an embedding-retrieval-rerank-generation loop, yielding structured JSON responses via a FastAPI interface.

### The "So What?" Layer

This "intentionally boring" design choice mitigates the risks of LLM non-determinism. By decoupling data ingestion from generative logic, we ensure that the system's "non-parametric memory" can be audited, versioned, and corrected without retraining the underlying model. In a domain where an incorrect ECTS count can invalidate an application, this transparency is the primary engineering requirement.

Transitioning from the system overview, the integrity of the agent depends first on the rigor of the data acquisition and normalization pipeline.

## 2. Ingestion Pipeline and Document Normalization

Admissions data is heterogeneous, existing in complex multi-column PDFs, nested HTML tables, and official regulations. A layout-aware ingestion pipeline is mandatory to transform these formats into structured text while preserving the semantic hierarchy—such as the relationship between a degree program and its specific ECTS prerequisites.

### Source Registry & Acquisition

We adopt an "Official-First" strategy. Primary sources include university program pages (e.g., TUM, RWTH Aachen), uni-assist procedural guides, and DAAD databases.

- **Legal Compliance:** In accordance with § 44b UrhG, we implement "polite-fetching" by strictly honoring robots.txt rules.
- **Data Rights:** Following the OLG Hamburg (LAION) ruling, we acknowledge that natural language reservations are increasingly contested. Therefore, we utilize a conservative, manual-download approach for a small, non-commercial corpus to ensure compliance with rights-holder opt-outs that may not yet be machine-readable.

### Parsing and Normalization

To ensure downstream accuracy, we move beyond plain text extraction:

- **Docling / LlamaParse:** These vision-language-based parsers are preferred for their ability to comprehend multi-column layouts and nested tables, converting them into clean Markdown.
- **PyMuPDF4LLM:** A lightweight alternative for Markdown extraction that preserves page-level context.
- **Beautiful Soup:** Utilized for parsing structured HTML from university web portals.

Normalizing all inputs to Markdown is critical for preserving headers and table structures, which allows the LLM to reason over complex requirements (e.g., language certificate levels) without losing structural context.

### The "So What?" Layer

Layout-aware parsing prevents the "flattening" of data. If a table of language requirements is converted to a plain string, the LLM may lose the row-column relationship. Preserving Markdown tables ensures the model understands exactly which certificate applies to which degree program.

Once documents are normalized, they are segmented into searchable units through structural chunking.

## 3. Structural Chunking and Semantic Vectorization

Naive token-splitting is insufficient for regulatory text. We utilize section-aware chunking to preserve the semantic context of admissions rules.

### Chunking Logic

We implement a heuristic of 400–700 tokens per chunk with a 50-100 token overlap. We utilize structural chunking, using Markdown headers (##, ###) as logical boundaries. This ensures that a single requirement or FAQ remains a self-contained unit within the vector space.

### Embedding Strategy

Given the bilingual (German/English) nature of the corpus, we require multilingual embeddings. While paraphrase-multilingual-MiniLM-L12-v2 is a light default, we prioritize bge-m3 or gte-multilingual-base for superior cross-lingual retrieval performance, ensuring an English query can accurately retrieve German regulatory text.

### The "So What?" Layer

To mitigate the "Lost in the Middle" phenomenon, we employ the Parent-Document Retrieval pattern. We store small chunks for high-precision vector search but retrieve the larger parent section (e.g., the entire "Language Requirements" chapter) to provide the LLM with sufficient context for synthesis.

These vectors and their associated metadata are stored in a specialized infrastructure for precise retrieval.

## 4. Vector Infrastructure and Metadata Management

The vector database serves as the system's "non-parametric memory," allowing for high-speed similarity search coupled with strict business logic filtering.

### Database Selection

We recommend Qdrant for production-flavored implementations. Unlike Chroma (which is suitable for local prototyping), Qdrant offers native support for sparse/dense hybrid search, gRPC interfaces, and advanced payload filtering.

### Metadata Schema

A strict Pydantic-based manifest is attached to every chunk to enable pre-retrieval filtering:

- **university_slug:** e.g., "tum-munich"
- **programme_slug:** e.g., "msc-data-science"
- **source_type:** e.g., "deadline_schedule" or "v_p_d_info"
- **country_scope:** Essential for handling APS certificate logic for Indian or Chinese applicants.
- **lang:** (de/en) to manage language-specific retrieval.
- **last_updated:** ISO timestamp to track information staleness.

### The "So What?" Layer

Metadata filtering acts as a "business logic layer." By applying a filter such as university_slug == "rwth-aachen" before search, we mathematically guarantee the system will not conflate requirements between different universities, a common failure point in "naive" RAG systems.

The retrieval process uses this infrastructure to isolate the most relevant evidence for the generator.

## 5. Retrieval Strategy and Precision Engineering

In admissions, missing a single deadline can invalidate an application. Therefore, retrieval must move beyond simple similarity search.

### The Retrieval Loop

## 1. Query Embedding: Multilingual vectorization of the user question.
## 2. Metadata Filtering: Pre-filtering the search space based on program or university.
## 3. Dense Semantic Search: Initial top-K retrieval via vector similarity.

Advanced Retrieval (V2) We implement Hybrid Search, combining dense vector embeddings with sparse keyword search (BM25). These results are merged via Reciprocal Rank Fusion (RRF) using the smoothing constant k=60. A final Cross-Encoder Reranker is used to distill the top-K candidates down to the absolute most relevant 5 chunks.

### The "So What?" Layer

We implement a "Retrieval Gate": if the similarity score of the top chunks falls below a predefined threshold, the system triggers a deterministic refusal. This prevents the LLM from being forced to synthesize an answer from irrelevant context.

Retrieved evidence is then synthesized into a structured output contract.

## 6. Grounded Generation and Structured Synthesis

To integrate with applicant tracking or checklist systems, the agent must provide structured, deterministic outputs via the Instructor library and Pydantic.

Structured Output Contracts Responses must adhere to a strict JSON schema:

- **answer:** The natural language synthesis.
- **citations[]:** IDs linking to source chunks.
- **insufficient_context_flag:** Boolean.
- **confidence_score:** Float.

The Grounded Prompt Contract The generator LLM is governed by strict directives:

## 1. Use only provided context.
## 2. If the answer is not present, output exactly: "Information not found in the official documents."
## 3. Synthesize facts such as uni-assist fees (€75 for the first course, €30 for subsequent courses) and VPD processing times (usually 4–6 weeks) only if found in the context.

### The "So What?" Layer

The Instructor library's validation-retry loop ensures that the output is not just "JSON-like" but strictly valid according to the Pydantic model. This transforms the agent from a chatbot into a reliable data service for downstream processing, such as automated checklist rendering.

Verifiability is finalized at the API layer, where citations are packaged for the user.

## 7. Verifiability and the API Layer

The UniApply Agent must be auditable. We utilize spatial citations to map claims back to official documentation.

Citation Packaging We map chunk IDs back to original source URLs and page numbers. Hallucinated citations are strictly forbidden; citations must correspond only to the retrieved chunks.

### API Architecture

Built on FastAPI, the system implements a provider-abstraction layer (using pydantic-settings). This allows us to swap between a MockLLM (for testing), Ollama (for local dev), or OpenAI/Gemini (for production) with zero pipeline rewrites.

- **/ask:** RAG Q&A.
- **/checklist:** Program requirement extraction.
- **/detect-missing:** Compares user profile JSON to program requirements.

### The "So What?" Layer

Using pydantic-settings for environment isolation and FastAPI’s auto-generated OpenAPI docs ensures this is a professional-grade backend service rather than a simple script wrapper.

## 8. The Roadmap: From RAG to Agentic Workflows

We follow an "Agent-Last" philosophy, ensuring the retrieval core is mathematically stable before introducing autonomous reasoning.

Phased Evolution

## 1. V1 (Core RAG): Deterministic endpoints for Q&A, checklists, and missing-document detection.
## 2. V2 (Orchestrated Tools): Intent routing and grounded email drafting using retrieved facts.
## 3. V3 (Agentic): LangGraph-based multi-step reasoning. This is introduced only when loops, stateful self-correction, or human-in-the-loop verification are required for complex reasoning over multiple documents.

### The "So What?" Layer

Early adoption of LangGraph often introduces infinite loops and unnecessary complexity. We justify it only when the system needs to "pause" for a human to verify a document or "loop" to retry a search that yielded "insufficient context."

## 9. Evaluation and Risk Framework

Professional credibility in AI requires mathematically verifiable metrics over subjective "vibe checks."

The RAG Triad Metrics We utilize RAGAS-style evaluation:

## 1. Faithfulness (Groundedness): Verifying answer claims against retrieved context.
## 2. Answer Relevance: Measuring alignment with the user's question.
## 3. Context Precision: Evaluating the retrieval pipeline’s ranking quality.

### The 50-Question Gold Dataset

Evaluation is conducted against a synthetic dataset of 50 questions distributed across:

- **Factual (50%):** Direct retrieval (e.g., uni-assist fees).
- **Multi-hop (20%):** Synthesis across multiple documents.
- **Reformulation (15%):** Resilience to typos/bad phrasing.
- **Out-of-Scope (15%):** Testing refusal behavior (e.g., Canadian visa queries).

### Risk Mitigation

Every response must include a legal disclaimer: "Not official admissions advice; verify with primary sources at the official university portal."

### Final Implementation Summary: Next 5 Tasks

## 1. Registry Setup: Define the Pydantic metadata schema including country_scope.
## 2. Ingestion: Build the Docling-based layout-aware parser and normalizer.
## 3. Indexing: Configure local Qdrant and execute the indexing pipeline.
## 4. Serving: Implement the FastAPI /ask endpoint with provider abstraction.
## 5. Evaluation: Create the 50-question "Gold Dataset" to benchmark reliability.
