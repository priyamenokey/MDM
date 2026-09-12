import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Ensure project root is on sys.path when Streamlit runs the script so
# our local `agent`, `er`, and `graph` packages can be imported.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

from neo4j.exceptions import ServiceUnavailable

from agent.query_graph import answer_question


st.set_page_config(page_title="ER Knowledge Graph - Ask", layout="wide")

st.title("ER Knowledge Graph — Ask a question")

st.markdown(
    """
    Ask a natural-language question about an entity or item, for example:
    `What records are related to Entity A?` or `Show me Entity B records.`
    The app resolves the entity name and queries the Neo4j knowledge graph.
    """
)

question = st.text_input(
    "Question",
    value="",
    placeholder="Example: What records are related to Entity A?",
)

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Resolving the company and querying the graph..."):
            try:
                result = answer_question(question)
                rows = result.get("results", []) or []
                entity_name = result.get("entity_name")

                if entity_name:
                    st.success(result["answer"])
                else:
                    st.info(result["answer"])

                if rows:
                    normalized_rows = []
                    for row in rows:
                        if isinstance(row, dict):
                            if "entity" in row:
                                normalized_rows.append({
                                    "entity": row.get("entity"),
                                })
                            else:
                                normalized_rows.append({
                                    "entity": row.get("golden_name") or row.get("entity_name") or entity_name,
                                    "item": row.get("item_name"),
                                    "record_id": row.get("record_id"),
                                })

                if normalized_rows:
                        st.table(normalized_rows)
                else:
                    st.info("No matching results were found.")

            except ServiceUnavailable as e:
                st.error("Neo4j connection error: " + str(e))
                st.write(
                    "Ensure your `.env` contains valid `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`, and that the database is reachable."
                )
            except Exception as e:
                st.error("Unexpected error: " + str(e))

st.markdown("---")
st.caption("Dynamic ER + Knowledge Graph demo")
