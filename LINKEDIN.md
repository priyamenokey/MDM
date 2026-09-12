# Building an Entity Resolution + Knowledge Graph System (LinkedIn Post)

## 🔗 Entity Resolution Meets Graph Databases

Just built a practical POC that combines **entity resolution** with **Neo4j** to solve a classic data problem: messy, duplicate, and inconsistent entity naming.

### The Problem
Real-world data is messy. The same entity appears under different names:
- "Entity A", "Entity-A", "Entity A Inc.", "Entity A Incorporated"

Traditional databases treat these as separate records. Your query layer can't connect the dots.

### The Solution
**Three-layer architecture:**

1️⃣ **Entity Resolution Layer** (Python + RapidFuzz)
- Normalize names → compare similarity → cluster duplicates
- Transform noisy source records into canonical golden entities
- 60% name similarity + 30% address + 10% country match = golden clusters

2️⃣ **Knowledge Graph** (Neo4j)
- Store both source records AND canonical entities
- Preserve lineage: `SourceRecord → RESOLVES_TO → GoldenEntity`
- Build relationships: `Entity → PRODUCES → Item`

3️⃣ **Query Layer** (LLM + Neo4j)
- Natural language: "What records relate to Entity A?"
- Hybrid approach: LLM for intent extraction + deterministic Cypher for execution
- Returns both canonical and source lineage

### Key Principle
> Don't ask the LLM to decide canonical identity. Use deterministic ER first, then query the graph.

This keeps the system **trustworthy** and **auditable**.

### Tech Stack
- Python (pandas, RapidFuzz, NetworkX)
- Neo4j AuraDB
- OpenAI (intent extraction)
- Streamlit (UI)

### Why This Matters
You don't need expensive MDM tools to start. This pattern is:
- ✅ Simple to implement
- ✅ Predictable and debuggable
- ✅ Scales with better ER logic
- ✅ Foundation for production systems

The repo is open source and ready to fork: **[GitHub: MDM](https://github.com/priyamenokey/MDM)**

What's your biggest entity resolution challenge? Drop a comment below.

#DataEngineering #EntityResolution #Knowledge Graphs #Neo4j #Python
