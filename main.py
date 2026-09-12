import pandas as pd
import networkx as nx

from er.golden_entity import create_golden_entities
from er.matcher import similarity
from graph.load_graph import load_golden_entities


def build_matches(records, threshold=0.75):
    matches = []

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            r1 = records[i]
            r2 = records[j]
            score = similarity(r1, r2)

            if score >= threshold:
                matches.append({
                    "record1": r1["record_id"],
                    "record2": r2["record_id"],
                    "score": score,
                })

    return matches


def build_clusters(records, matches):
    G = nx.Graph()

    for record in records:
        G.add_node(record["record_id"])

    for match in matches:
        G.add_edge(match["record1"], match["record2"])

    return list(nx.connected_components(G))


def main():
    df = pd.read_csv("data/companies.csv")
    records = df.to_dict(orient="records")

    matches = build_matches(records)
    print("Matches")
    for match in matches:
        print(match)

    clusters = build_clusters(records, matches)
    print("\nClusters")
    for cluster in clusters:
        print(cluster)

    golden_entities = create_golden_entities(clusters, records)
    print("\nGolden Entities")
    for entity in golden_entities:
        print(entity["golden_id"], entity["name"])

    try:
        load_golden_entities(golden_entities, records)
        print("\nLoaded golden entities into Neo4j")
    except RuntimeError as exc:
        print(f"\nNeo4j not loaded: {exc}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
