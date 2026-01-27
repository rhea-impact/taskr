# Research

Technical research informing Taskr's design decisions.

## Search & Retrieval

| Document | Summary |
|----------|---------|
| [embedding-limitations-theory.md](./embedding-limitations-theory.md) | Why dense vectors fundamentally cannot work at scale (Google DeepMind LIMIT paper) |
| [hybrid-search-pgvector-rrf.md](./hybrid-search-pgvector-rrf.md) | Implementation guide for hybrid search with pgvector + RRF fusion |

## Key Takeaways

### Dense Vectors Have Hard Limits

From the theoretical limitations research:
- Embedding dimension limits how many top-k combinations can be retrieved
- At ~1.7M docs, 768-dim embeddings hit mathematical ceiling
- This is **not** solvable with better training or larger models

### Hybrid Search Is Required

From the RRF research:
- Combine BM25 (lexical) + pgvector (semantic)
- RRF fusion surfaces docs that rank well in either approach
- Tunable weights for different query types

## Adding Research

When adding new research:
1. Create a markdown file with clear sections
2. Include paper citations with links
3. Add practical implications for Taskr
4. Update this README with a summary
