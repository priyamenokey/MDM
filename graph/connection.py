import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def get_driver():
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        raise RuntimeError(
            "Missing Neo4j credentials. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in .env"
        )

    return GraphDatabase.driver(uri, auth=(username, password))


def test_connection():
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print("Connected to Neo4j")
    finally:
        driver.close()
