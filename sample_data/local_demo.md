# FabIQ Local Demo Document

FabIQ is a multi-agent retrieval augmented generation system for technical documentation intelligence. It uses role-based access control to make sure users only retrieve document chunks they are permitted to see.

Field engineers can access public documentation. Process engineers can access public and internal documentation. Admin users can access public, internal, and restricted documentation.

In Azure production mode, FabIQ uses Azure OpenAI for embeddings and answer generation, and Azure AI Search for hybrid vector and keyword retrieval.

In local demo mode, FabIQ uses a local JSON vector index and deterministic local embeddings so reviewers can verify ingestion, retrieval, citation formatting, API routes, and dashboard behavior without Azure credentials.
