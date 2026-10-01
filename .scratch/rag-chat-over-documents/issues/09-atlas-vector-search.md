# 09: Atlas vector search, scoped to a session

**What to build:** Real retrieval replaces the local adapter. The Atlas index definition is documented as a one-time setup step sufficient to bring up a fresh cluster, the Atlas adapter lands behind the same vector store port and is chosen by configuration, and session scoping is a filter on the search itself rather than a post-filter. Verifiable through tests and a temporary debug surface: asking for something only session B holds while scoped to session A returns nothing.

**Blocked by:** 06 (Upload and ingest text-format documents)

**Status:** done

- [x] The Atlas vector index definition is documented as a one-time setup step sufficient to bring up a fresh cluster
- [x] Retrieval runs through Atlas vector search behind the existing vector store port, selected by configuration rather than by code change
- [x] The index declares the vector field with the embedding model's dimensions and cosine similarity, and declares the session field as a filter field
- [x] A query scoped to one session never returns a chunk belonging to another, even when the other session matches the query better
- [x] Retrieval returns the top-k most similar chunks in relevance order
- [x] A mismatch between the configured embedding model's dimensions and the index fails explicitly rather than silently returning nothing
- [x] The local adapter remains selectable by configuration for environments without an Atlas index
