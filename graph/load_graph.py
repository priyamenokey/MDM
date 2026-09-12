from graph.connection import get_driver


def create_golden_entity(entity):
    driver = get_driver()
    try:
        query = """
        MERGE (g:GoldenEntity {id: $id})
        SET g.name = $name,
            g.country = $country
        """

        driver.execute_query(
            query,
            id=entity["golden_id"],
            name=entity["name"],
            country=entity["country"],
            database_="neo4j",
        )
    finally:
        driver.close()


def create_source_record(record, golden_id):
    driver = get_driver()
    try:
        query = """
        MERGE (r:SourceRecord {id: $record_id})
        SET r.name = $name,
            r.source = $source

        WITH r

        MATCH (g:GoldenEntity {id: $golden_id})

        MERGE (r)-[:RESOLVES_TO]->(g)
        """

        driver.execute_query(
            query,
            record_id=str(record["record_id"]),
            name=record["name"],
            source=record["source"],
            golden_id=golden_id,
            database_="neo4j",
        )
    finally:
        driver.close()


def create_demo_business_objects(golden_entity):
    driver = get_driver()
    try:
        query = """
        MATCH (g:GoldenEntity {id: $golden_id})
        MERGE (i:Item {id: $item_id})
        SET i.name = $item_name
        MERGE (c:CaseRecord {id: $case_id})
        SET c.name = $case_name
        MERGE (g)-[:MANUFACTURES]->(i)
        MERGE (c)-[:CONCERNS]->(i)
        """

        suffix = golden_entity["golden_id"].split("-")[-1]
        driver.execute_query(
            query,
            golden_id=golden_entity["golden_id"],
            item_id=f"ITEM-{suffix}",
            item_name=f"Sample Item {suffix}",
            case_id=f"CASE-{suffix}0",
            case_name=f"Case {suffix}0",
            database_="neo4j",
        )
    finally:
        driver.close()


def load_golden_entities(golden_entities, records):
    record_map = {r["record_id"]: r for r in records}

    try:
        for entity in golden_entities:
            create_golden_entity(entity)

            for member in entity["members"]:
                create_source_record(record_map[member["record_id"]], entity["golden_id"])

            create_demo_business_objects(entity)
    except Exception as exc:
        raise RuntimeError(
            "Unable to load golden entities into Neo4j. Check your AuraDB URI/username/password in .env."
        ) from exc
