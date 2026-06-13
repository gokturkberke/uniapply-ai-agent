# Data Curation Guide: Building a Reliable AI Assistant for University Admissions

## 1. The Philosophy of "Quality In, Quality Out"

In high-stakes environments like university admissions, the architecture of an AI system must prioritize factual integrity over generative flair. A standard Large Language Model (LLM) relies on its "parametric memory"—knowledge frozen at the time of training—which is prone to hallucinations and outdated information. To solve this, we implement Retrieval-Augmented Generation (RAG). This approach treats the LLM as an analyst rather than a database, forcing it to retrieve evidence from a curated, non-parametric dataset of official documents before synthesizing an answer.

### The "So What?": Why Precision is Mandatory

In German admissions, accuracy is not a luxury; it is a prerequisite for student success. Providing an incorrect processing fee (e.g., failing to mention the €75 initial fee or €30 additional course fee via uni-assist) or a stale processing window (e.g., missing the 4–6 week VPD evaluation period) can lead to missed deadlines and rejected applications. A single hallucinated requirement can derail a student's career and expose the provider to significant liability.

Before we can optimize the retrieval logic, we must first establish the hierarchy of truth among our sources.

## 2. Navigating the Source Hierarchy: Primary vs. Secondary Evidence

As an AI Architect, your first task is to define the "Source of Truth." Data curation must respect the institutional hierarchy of the German education system to ensure the assistant provides binding information rather than mere "orientation."

### The Admissions Source Hierarchy

| Source Type | Examples | Authority Level |
|---|---|---|
| Official University Pages | TUM (TU Munich), RWTH Aachen | Primary (Final Authority) |
| Standardized Portals | uni-assist | Secondary (Procedural) |
| National Databases | DAAD (German Academic Exchange) | Secondary (Orientation Only) |

### Why University Pages are the Final Authority

1. **Non-Binding Secondary Data:** The DAAD explicitly states its admissions database is for orientation only and is not legally binding.
2. **The "Update Lag" Risk:** Secondary databases are often stale. For example, the DAAD database version cited in current research was last updated in November 2021, making it dangerous for 2025/2026 application cycles.
3. **Procedural Nuance:** Secondary portals often act only as intermediaries. For instance, obtaining a Vorprüfungsdokumentation (VPD) from uni-assist does not constitute a full application to TUM; an additional application via the university's internal portal (TUMonline) is mandatory.

Identifying the source is only the first step; to make this information accessible to our retriever, we must wrap it in a layer of traceable metadata.

## 3. The Metadata Blueprint: Creating Traceable Intelligence

Metadata prevents "hallucinations" by allowing the system to apply hard filters before the semantic search even begins. If a student asks about "Data Science at TUM," the system should not even look at documents from other universities.

### Essential Metadata Fields

- **university_name**
  - **Primary Benefit:** Ensures the student receives rules specifically for their chosen institution, preventing the "blending" of requirements from different schools.
- **program_name**
  - **Primary Benefit:** Isolates program-specific ECTS credit prerequisites, which vary wildly even within the same faculty.
- **source_url**
  - **Primary Benefit:** Provides the user with a clickable citation, allowing for immediate human verification of the AI's claims.
- **last_updated**
  - **Primary Benefit:** Flags information as potentially "stale" if it dates back to previous semesters, such as the Nov 2021 DAAD datasets.
- **doc_type**
  - **Primary Benefit:** Allows the retriever to prioritize "Deadlines" or "Official Requirement" documents over "FAQ" pages for high-priority queries.
- **country_scope**
  - **Primary Benefit:** Crucial for managing specific mandates like the APS certificate required only for applicants from India, China, or Vietnam.

While technical metadata ensures precision, we must also ensure our data acquisition strategies comply with the evolving legal landscape of the European digital market.

## 4. Ethical Collection and German Copyright Law (§ 44b UrhG)

Data collection in Germany is governed by strict copyright frameworks. While § 44b UrhG allows for Text and Data Mining (TDM), the "Curriculum Specialist" must understand the data lifecycle: copies must be deleted once they are no longer required for the analysis.

### The Three Golden Rules for Students

1. **Strictly Personal/Educational Use:** Portals like uni-assist and DAAD only permit reproduction for private, non-commercial purposes. Commercial exploitation of this data without consent is a violation of the Impressum terms.
2. **The "Polite Fetch" Protocol:** Avoid aggressive crawling. Manually download PDFs or use the "Save as PDF" feature on DAAD to create a small, manageable, and compliant corpus.
3. **Lifecycle Deletion:** Under § 44b(2) UrhG, intermediate copies used for processing must be deleted once the specific mining task is complete.

> ⚠️ **Warning: Machine-Readable Opt-outs**  
> Always check the robots.txt and the "Impressum" (Legal Notice). Note the recent OLG Hamburg (LAION case, Dec 2024/2025) ruling: natural-language opt-outs (e.g., "Do not scrape this site") may be considered invalid if they are not machine-readable. Your system must specifically check for machine-readable headers or metadata reservations that signal a rightsholder's opt-out.

With a legally sound dataset secured, we transition from raw data collection to the technical normalization pipeline required for high-fidelity retrieval.

## 5. The Technical Journey: From Raw PDF to AI-Ready Markdown

Raw PDFs are a "format of last resort" for LLMs because they lack a semantic layer. To ensure the assistant understands tables and hierarchical lists, we must normalize the data into Markdown.

### The Normalization Pipeline

1. **Loading:** Aggregating official PDFs and HTML pages into a raw reproducibility archive.
2. **Parsing:** Utilizing layout-aware tools like Docling or PyMuPDF4LLM to extract text while preserving headers and table structures.
3. **Normalization:** Converting all content to Markdown. This preserves the relationship between a requirement and its value (e.g., "IELTS: 6.5").
4. **Chunking:** Segmenting the text for the vector database.

### Architectural Precision: Chunking & Embeddings

- **The Multilingual Requirement:** Since German admissions content is bilingual (DE/EN), you must use Multilingual Embeddings (e.g., paraphrase-multilingual-MiniLM-L12-v2). This allows a student to ask a question in English and retrieve the correct answer from a German-language PDF.
- **Structure-Aware Chunking vs. Fixed-Size:**
  - **Fixed-Size Splitting** (e.g., every 500 characters) often cuts a deadline off from the program name it belongs to.
  - **Structure-Aware Chunking** (splitting by headers) ensures that all "Language Requirements" stay in a single context block, providing the LLM with the full picture needed for an accurate response.

This technical foundation allows the data curator to hand over a verified corpus to the engineering team for final deployment.

## 6. Conclusion: The Curator’s Final Checklist

As a Data Curator, you are the final arbiter of truth. Your role is to bridge the gap between messy institutional websites and the structured needs of a RAG system. Before deploying your "UniApply" dataset, verify your work against this mandate:

- [ ] **Authority Check:** Are the primary university pages used as the source of truth for all deadlines and fees?
- [ ] **Metadata Integrity:** Does every chunk contain a university_name, source_url, and the critical country_scope for APS-related requirements?
- [ ] **Normalization:** Is the data in Markdown format with all tables and headers intact?
- [ ] **Legal Audit:** Have you verified the robots.txt for "machine-readable" opt-outs in accordance with the OLG Hamburg ruling?
- [ ] **Refusal Path:** Is the dataset accompanied by a "Refusal Instruction," directing the AI to state "Information not found in official documents" rather than guessing?

### The Curator’s Final Mandate

Your goal is to provide the AI with the right data, not the most data. By enforcing these standards, you transform a generic chatbot into a reliable, source-grounded admissions assistant that students can trust with their future.
