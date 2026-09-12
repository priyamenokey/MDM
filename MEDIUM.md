# Entity Resolution + Knowledge Graph: A Practical POC

*Building a deterministic, scalable data quality system with Python, Neo4j, and LLMs*

---

## Introduction

Data quality is a silent killer.

Real-world entity data is messy. The same entity appears under 5+ variations of its name, with inconsistent addresses, across different systems. Your analytics team wastes weeks reconciling it manually. Your ML pipeline gets poisoned. Your reporting looks unreliable.

This article walks you through a **production-adjacent approach** to entity resolution using Python, Neo4j, and a hybrid LLM layer that turns hours of manual work into seconds of automated insights.

---

## The Problem: Three Data Quality Challenges

### 1. Manual Reconciliation Overhead

- Hours spent comparing and matching duplicate records
- Subject-matter experts required to make deduplication decisions
- Non-scalable: 10,000 records → weeks of work

### 2. Trust & Auditability

- LLMs alone can't reliably decide canonical entities
- No way to trace why a record was matched
- Can't explain decisions to compliance teams

### 3. Lost Relationships

- Once you merge duplicates, you lose lineage to source records
- Downstream queries can't explain "where did this come from?"
- Debugging becomes impossible

**Before:** 20+ hours/week of manual matching  
**After:** 99% automated in seconds, fully auditable

---

## The Solution: Three-Layer ER + Knowledge Graph

Deterministic entity resolution (Python) → Canonical graph (Neo4j) → Natural language queries (LLM + Cypher)

```
Step 1: Normalize messy names (remove punctuation, standardize aliases)
  ↓
Step 2: Score pairwise similarity (RapidFuzz, weighted matching)
  ↓
Step 3: Cluster duplicates (NetworkX connected components)
  ↓
Step 4: Canonicalize into golden entities (pick best record from each cluster)
  ↓
Step 5: Load into Neo4j (preserve source → golden lineage)
  ↓
Step 6: Query with natural language (LLM extracts intent, Cypher executes)
```

---

## Architecture: Three Layers of Intelligence

[Insert image: ER+KG Architecture diagram with three layers]

### Layer 1: Entity Resolution Engine (Python)

Takes messy source records and resolves them into canonical golden entities.

```python
from er.normalize import normalize_company_name
from er.matcher import score_pair_match
import networkx as nx

# Input: 1000 messy records
# Output: 250 deduplicated golden entities

# Step 1: Normalize
df['normalized_name'] = df['name'].apply(normalize_company_name)

# Step 2: Score all pairs
matches = []
for i in range(len(df)):
    for j in range(i + 1, len(df)):
        score = score_pair_match(df.iloc[i], df.iloc[j])
        if score > 0.75:  # Threshold
            matches.append({'i': i, 'j': j, 'score': score})

# Step 3: Cluster
G = nx.Graph()
for i in range(len(df)):
    G.add_node(i)
for match in matches:
    G.add_edge(match['i'], match['j'])

clusters = list(nx.connected_components(G))

# Step 4: Canonicalize
golden_entities = {}
for cluster_id, cluster in enumerate(clusters, 1):
    best_record = df[df.index.isin(cluster)].iloc[0]
    golden_entities[f'GE-{cluster_id:03d}'] = {
        'name': best_record['name'],
        'source_records': list(cluster)
    }
```

**Key insight:** Don't use ML to pick canonical entities. Use deterministic rules. Your graph becomes auditable.

### Layer 2: Neo4j Knowledge Graph

Store both source records AND canonical entities. Preserve lineage.

```cypher
// Node types
CREATE (:SourceRecord {id: 1, name: "Entity A", address: "123 Main St"})
CREATE (:GoldenEntity {id: 'GE-001', name: 'Entity A'})
CREATE (:Item {id: 'ITEM-001', name: 'Product X'})
CREATE (:CaseRecord {id: 'CASE-100', status: 'active'})

// Relationships
CREATE (r:SourceRecord)-[:RESOLVES_TO]->(g:GoldenEntity)
CREATE (g:GoldenEntity)-[:PRODUCES]->(i:Item)
CREATE (c:CaseRecord)-[:CONCERNS]->(i:Item)
```

**Why this design?**
- Preserves lineage: Query → Golden Entity → Source Record
- Auditable: every edge explains a relationship
- Graph-efficient: Neo4j traverses relationships in milliseconds

### Layer 3: Query Layer (LLM + Cypher)

Let users ask natural-language questions. LLM handles intent, Cypher handles execution.

```python
from openai import OpenAI
from neo4j import GraphDatabase

def answer_question(question):
    # Step 1: LLM extracts intent & entity
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": 
                "Extract: intent (entity_records|item_entity|list_entities), "
                "entity (string or empty). Return JSON only."},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    plan = json.loads(response.choices[0].message.content)
    
    # Step 2: Route to appropriate Cypher query
    if plan['intent'] == 'entity_records':
        cypher = """
        MATCH (r:SourceRecord)-[:RESOLVES_TO]->(g:GoldenEntity)
        WHERE toLower(g.name) = toLower($entity)
        OPTIONAL MATCH (g)-[:PRODUCES]->(i:Item)<-[:CONCERNS]-(c:CaseRecord)
        RETURN g.name, i.name, c.id
        """
    
    # Step 3: Execute & return
    rows = driver.execute_query(cypher, entity=plan['entity'])
    return format_results(rows)
```

---

## Query Flow: End-to-End

[Insert image: Query flow diagram]

**Scenario: "What records relate to Entity A?"**

```
Natural Language Query
    ↓
LLM Extracts Intent & Entity
    ↓
Routes to Cypher Query
    ↓
Neo4j Executes (traces SourceRecord → GoldenEntity → Item → CaseRecord)
    ↓
Returns Structured Results
    ↓
Displays with Lineage
```

---

## Design Principles That Make This Work

### 1. Determinism First

> Don't ask an LLM to decide canonical identity. Use deterministic ER first.

LLMs are great at understanding intent. They're terrible at data governance.

By separating concerns:
- **Auditability**: every ER decision can be inspected & explained
- **Consistency**: same entity always has same ID
- **Debuggability**: results are reproducible

### 2. Preserve Lineage

Never delete source records. Store the mapping: `SourceRecord → RESOLVES_TO → GoldenEntity`

If a query result looks wrong:
```
Result ← Golden Entity ← Source Record ← Original data entry
```

You can trace the entire chain.

### 3. Layer Incrementally

Start simple:
- Name normalization + RapidFuzz matching
- NetworkX clustering
- Basic Cypher queries

Then scale:
- Machine learning matching
- Active learning for hard cases
- Evolutionary algorithms for optimization

---

## Implementation: 5 Steps

### Step 1: Load Sample Data

```python
import pandas as pd

data = [
    {"record_id": 1, "name": "Entity A", "address": "123 Main St", "city": "Boston"},
    {"record_id": 2, "name": "Entity-A", "address": "123 Main Street", "city": "Boston"},
    {"record_id": 3, "name": "Entity A Inc.", "address": "123 Main St", "city": "Boston"},
    {"record_id": 4, "name": "Entity B", "address": "456 Oak Ave", "city": "Cambridge"},
]

df = pd.DataFrame(data)
```

### Step 2: Normalize & Match

Remove punctuation, standardize names, score similarity:

```python
from er.normalize import normalize_company_name
from er.matcher import score_pair_match

# Normalize
df['normalized_name'] = df['name'].apply(normalize_company_name)

# Score pairs
matches = []
for i in range(len(df)):
    for j in range(i + 1, len(df)):
        score = score_pair_match(df.iloc[i], df.iloc[j])
        if score > 0.75:
            matches.append({'i': i, 'j': j, 'score': score})
```

### Step 3: Cluster & Canonicalize

Use NetworkX to find connected components:

```python
import networkx as nx

G = nx.Graph()
for i in range(1, len(df) + 1):
    G.add_node(i)

for match in matches:
    G.add_edge(match['i'], match['j'])

clusters = list(nx.connected_components(G))

# Create golden entities
golden_entities = {}
for cluster_id, cluster in enumerate(clusters, 1):
    best_record = df[df.index.isin(cluster)].iloc[0]
    golden_entities[f'GE-{cluster_id:03d}'] = {
        'name': best_record['name'],
        'source_records': list(cluster)
    }
```

### Step 4: Load into Neo4j

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j+s://...", auth=("neo4j", "password"))

def load_golden_entities(session, entities):
    for ge_id, entity in entities.items():
        session.run(
            "CREATE (g:GoldenEntity {id: $id, name: $name})",
            id=ge_id, name=entity['name']
        )
        for source_id in entity['source_records']:
            session.run(
                "MATCH (r:SourceRecord {id: $src}) "
                "MATCH (g:GoldenEntity {id: $ge}) "
                "CREATE (r)-[:RESOLVES_TO]->(g)",
                src=source_id, ge=ge_id
            )

with driver.session() as session:
    load_golden_entities(session, golden_entities)
```

### Step 5: Query via Streamlit UI

```python
import streamlit as st
from agent.query_graph import answer_question

st.title("Entity Resolution Demo")
question = st.text_input(
    "Ask about entities:",
    placeholder="What records relate to Entity A?"
)

if st.button("Search"):
    result = answer_question(question)
    st.write(result['answer'])
    if result['results']:
        st.table(result['results'])
```

---

## Real-World Challenges

### Challenge 1: Name Variations

**Problem:** "Corp", "Inc", "Ltd" might be truncated, expanded, or misspelled.

**Solution:** Aggressive normalization.

```python
def normalize_company_name(name):
    name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
    name = re.sub(r'\b(inc|corp|ltd|llc|co)\b', '', name, flags=re.IGNORECASE)
    return name.lower().strip()
```

### Challenge 2: Address Variations

**Problem:** "123 Main St" vs "123 Main Street" vs "123 Main Str".

**Solution:** Token-based fuzzy matching.

```python
from rapidfuzz import fuzz
address_score = fuzz.token_sort_ratio(addr1, addr2) / 100
```

### Challenge 3: Threshold Tuning

**Problem:** Is 0.75 too high? Too low?

**Solution:** Use a validation set. Manually label 100 pairs, measure precision/recall.

```python
from sklearn.metrics import precision_recall_curve
precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
# Find the threshold that balances precision & recall
```

### Challenge 4: Scale

**Problem:** 1M records = 1 trillion pairwise comparisons.

**Solution:** Block before scoring. Only compare records within the same "block".

```python
# Block by first letter
blocks = df.groupby(df['normalized_name'].str[0])
for letter, block_df in blocks:
    # Compare within block only
    ...
```

---

## Lessons Learned

1. **Start with normalization** — 50% of ER wins come from just cleaning names
2. **Graph clustering is your friend** — NetworkX connected components are trivial & effective
3. **Preserve lineage** — Never delete source → golden mappings
4. **Separate determinism from learning** — Let LLM do intent routing, not entity decisions
5. **Test each layer independently** — ER, graph loading, and queries before combining

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "ui/streamlit_app.py"]
```

### Linux Server

```bash
sudo apt install python3-pip
pip install streamlit neo4j rapidfuzz networkx openai
streamlit run ui/streamlit_app.py
```

### Security

- Store `NEO4J_PASSWORD` & `OPENAI_API_KEY` in env variables
- Rotate credentials regularly
- Scrub sensitive data from LLM queries
- Audit dashboard access logs

---

## Getting Started

```bash
git clone https://github.com/priyamenokey/MDM
cd er-knowledge-graph

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure Neo4j
export NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
export OPENAI_API_KEY="your-key"

# Run entity resolution
python main.py

# Launch UI
streamlit run ui/streamlit_app.py
```

---

## Next Steps

- **Active learning** — flag uncertain matches for human review
- **MLOps pipeline** — retrain matcher as new data arrives
- **Spark integration** — scale to billions of records
- **Alias tables** — maintain hand-curated entity aliases
- **Graph algorithms** — use Neo4j's PageRank, Community Detection

---

## Conclusion

Entity resolution isn't magic. It's a disciplined, repeatable process:

1. Normalize
2. Match
3. Cluster
4. Canonicalize
5. Query

Combine deterministic ER (Python) + auditable graph (Neo4j) + conversational interface (LLM + Streamlit), and you solve data quality at scale.

Your messy data problem isn't unsolvable. It just needs the right architecture.

**Deploy it. Questions? Drop them in the comments.**
