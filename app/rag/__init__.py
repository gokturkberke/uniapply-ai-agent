"""Domain layer for the source-grounded RAG pipeline.

Phase 1 provides the source registry and the metadata contracts. Ingestion,
chunking, retrieval, and generation are added in later phases. The FastAPI
delivery layer (``app/api``) stays thin and depends on this package, never the
other way around.
"""
