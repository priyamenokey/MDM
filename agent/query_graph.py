import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from graph.connection import get_driver
from er.normalize import normalize_company_name


def normalize_entity_name(name):
    """Normalize an entity name for comparison."""
    return normalize_company_name(name)


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def extract_entity_name(question):
    """Pull a likely entity name out of a natural-language question."""
    if question is None:
        return ""

    text = str(question).strip()
    if not text:
        return ""

    # Prefer direct matches for known entity names before falling back to generic parsing.
    known_names = [
        "Entity A",
        "Entity B",
        "Entity C",
    ]

    for name in known_names:
        if re.search(re.escape(name), text, flags=re.IGNORECASE):
            return name

    patterns = [
        r"(?:for|about|related to|regarding|on|from|with|of)\s+([A-Za-z0-9&.,()/-]+)",
        r"(?:entity|actor)\s+(?:named|called|is|for)?\s*([A-Za-z0-9&.,()/-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" ?.!:;,")
            if candidate:
                return candidate

    # Last resort: strip common question filler words from the start/end.
    cleaned = text
    cleaned = re.sub(r"^(?:what|show|tell me|give me|find|lookup|search|which|who|what's|what is|what are|does)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:records?|items?|data|entity|actor|related|me|have|does|are|is|to|of|for|about)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" ?.!:;,")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned and cleaned.lower() not in {"show", "what", "tell", "find", "lookup", "search", "me", "records", "items", "data", "entity", "actor"}:
        return cleaned

    return ""


def extract_item_reference(question):
    """Extract an item reference from a question such as 'Sample Item 001' or 'REC-0010'."""
    if question is None:
        return ""

    text = str(question).strip()
    if not text:
        return ""

    patterns = [
        r"\bSample Item\s*\d+\b",
        r"\bREC-\d+\b",
        r"\bRecord\s+\d+\b",
        r"\bItem\s+[A-Za-z0-9 -]+\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return ""


def query_entity_for_item(item_name):
    item_name = (item_name or "").strip()
    if not item_name:
        return []

    driver = get_driver()
    try:
        query = """
        MATCH (g:GoldenEntity)-[:PRODUCES]->(i:Item)
        WHERE toLower(i.name) = toLower($item_name)
           OR toLower(i.name) CONTAINS toLower($item_name)
           OR toLower(g.name) = toLower($item_name)
           OR toLower(g.name) CONTAINS toLower($item_name)
        RETURN DISTINCT g.name AS entity_name, i.name AS item_name
        ORDER BY entity_name, item_name
        """

        result = driver.execute_query(
            query,
            item_name=item_name,
            database_="neo4j",
        )

        if hasattr(result, "records"):
            records = result.records
        elif isinstance(result, list):
            records = result
        else:
            records = list(result)

        normalized = []
        for record in records:
            if hasattr(record, "data"):
                normalized.append(record.data())
            elif isinstance(record, dict):
                normalized.append(record)
            else:
                normalized.append(dict(record))

        return normalized
    finally:
        driver.close()


def query_records_for_entity(entity_name):
    entity_name = (entity_name or "").strip()
    if not entity_name:
        return []

    normalized_name = normalize_entity_name(entity_name)
    driver = get_driver()
    try:
        query = """
        MATCH (r:SourceRecord)-[:RESOLVES_TO]->(g:GoldenEntity)
        WHERE
            toLower(r.name) = toLower($entity_name)
            OR toLower(g.name) = toLower($entity_name)
            OR toLower(r.name) = toLower($normalized_name)
            OR toLower(g.name) = toLower($normalized_name)
            OR toLower(r.name) CONTAINS toLower($entity_name)
            OR toLower(g.name) CONTAINS toLower($entity_name)
            OR toLower(r.name) CONTAINS toLower($normalized_name)
            OR toLower(g.name) CONTAINS toLower($normalized_name)
        OPTIONAL MATCH (g)-[:PRODUCES]->(i:Item)<-[:CONCERNS]-(c:CaseRecord)
        RETURN DISTINCT g.name AS golden_name, i.name AS item_name, c.id AS record_id
        ORDER BY g.name, i.name, c.id
        """

        result = driver.execute_query(
            query,
            entity_name=entity_name,
            normalized_name=normalized_name,
            database_="neo4j",
        )

        if hasattr(result, "records"):
            records = result.records
        elif isinstance(result, list):
            records = result
        else:
            records = list(result)

        normalized = []
        for record in records:
            if hasattr(record, "data"):
                normalized.append(record.data())
            elif isinstance(record, dict):
                normalized.append(record)
            else:
                normalized.append(dict(record))

        return normalized
    finally:
        driver.close()


def _llm_plan_question(question):
    client = _get_openai_client()
    if client is None:
        return None

    system_prompt = """
    You are assisting with a knowledge-graph question. Return JSON with exactly these keys:
    - intent: one of [entity_records, item_entity, entity_lookup, list_entities]
    - entity: an entity or item string if detected; otherwise empty string
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        text = response.choices[0].message.content.strip()
        return __import__("json").loads(text)
    except Exception:
        return None


def answer_question(question):
    question_text = str(question or "").strip()
    if not question_text:
        return {
            "entity_name": None,
            "results": [],
            "answer": "I couldn't detect an entity name in your question. Please enter an entity name or try 'list all entities'.",
        }

    # Try the LLM first when configured so natural-language questions reach the LLM path.
    plan = _llm_plan_question(question_text)
    if plan:
        intent = str(plan.get("intent", "")).strip().lower()
        entity = str(plan.get("entity", "") or "").strip()
    else:
        intent = ""
        entity = ""

    if intent == "list_entities" or _looks_like_entity_list(question_text):
        rows = list_all_entities()
        return {
            "entity_name": None,
            "results": rows,
            "answer": (
                f"I found {len(rows)} entit{'ies' if len(rows) != 1 else 'y'}."
                if rows else "No entities were found in the graph."
            ),
        }

    item_ref = extract_item_reference(question_text)
    if (intent == "item_entity" or item_ref) and (entity or item_ref):
        target = entity or item_ref
        rows = query_entity_for_item(target)
        if rows:
            return {
                "entity_name": rows[0].get("entity_name"),
                "results": rows,
                "answer": f"{rows[0].get('entity_name')} produces {rows[0].get('item_name')}.",
            }

    entity_name = entity or extract_entity_name(question_text)
    if not entity_name:
        return {
            "entity_name": None,
            "results": [],
            "answer": "I couldn't detect an entity name in your question. Please try entering an entity name or 'list all entities'.",
        }

    rows = query_records_for_entity(entity_name)
    return {
        "entity_name": entity_name,
        "results": rows,
        "answer": (
            f"I found {len(rows)} record result(s) for {entity_name}."
            if rows else f"No record results were found for {entity_name}."
        ),
    }


def list_all_entities():
    driver = get_driver()
    try:
        query = """
        MATCH (g:GoldenEntity)-[:PRODUCES]->(:Item)
        RETURN DISTINCT g.name AS entity
        ORDER BY entity
        """

        result = driver.execute_query(
            query,
            database_="neo4j",
        )

        if hasattr(result, "records"):
            records = result.records
        elif isinstance(result, list):
            records = result
        else:
            records = list(result)

        normalized = []
        for record in records:
            if hasattr(record, "data"):
                normalized.append(record.data())
            elif isinstance(record, dict):
                normalized.append(record)
            else:
                normalized.append(dict(record))

        return normalized
    finally:
        driver.close()


def _looks_like_entity_list(question):
    text = str(question or "").lower().strip()
    if not text:
        return False

    patterns = [
        r"\blist all entit(ies|es)\b",
        r"\bshow all entit(ies|es)\b",
        r"\bwhat entit(ies|es)\b",
        r"\bwhich entit(ies|es)\b",
        r"\ball entit(ies|es)\b",
    ]

    return any(re.search(pattern, text) for pattern in patterns)
