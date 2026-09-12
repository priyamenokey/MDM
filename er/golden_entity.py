def create_golden_entities(clusters, records):
    record_map = {r["record_id"]: r for r in records}
    golden_entities = []

    for index, cluster in enumerate(clusters, start=1):
        members = [record_map[id] for id in cluster]
        canonical = members[0]
        golden_id = f"GE-{index:03}"

        golden_entities.append(
            {
                "golden_id": golden_id,
                "name": canonical["name"],
                "country": canonical["country"],
                "members": members,
            }
        )

    return golden_entities
