import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from graph.connection import get_driver
from er.normalize import normalize_company_name


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def extract_company_name(question):
    """Pull a likely company/facility name out of a natural-language question."""
    if question is None:
        return ""

    text = str(question).strip()
    if not text:
        return ""

    # Prefer direct matches for known brands and names before falling back to generic parsing.
    known_names = [
        "Johnson & Johnson",
        "Johnson and Johnson",
        "J&J",
        "Pfizer",
        "Moderna",
    ]

    for name in known_names:
        if re.search(re.escape(name), text, flags=re.IGNORECASE):
            return name

    patterns = [
        r"(?:for|about|related to|regarding|on|from|with|of)\s+([A-Za-z0-9&.,()/-]+)",
        r"(?:company|facility)\s+(?:named|called|is|for)?\s*([A-Za-z0-9&.,()/-]+)",
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
    cleaned = re.sub(r"\b(?:applications?|drugs?|records?|company|facility|related|me|have|does|are|is|to|of|for|about)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" ?.!:;,")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned and cleaned.lower() not in {"show", "what", "tell", "find", "lookup", "search", "me", "applications", "records", "drugs", "company", "facility"}:
        return cleaned

    return ""


def extract_product_reference(question):
    """Extract a drug/application reference from a question such as 'Sample Drug 001' or 'APP-0010'."""
    if question is None:
        return ""

    text = str(question).strip()
    if not text:
        return ""

    patterns = [
        r"\bSample Drug\s*\d+\b",
        r"\bAPP-\d+\b",
        r"\bApplication\s+\d+\b",
        r"\bDrug\s+[A-Za-z0-9 -]+\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return ""


def query_company_for_product(product_name):
    product_name = (product_name or "").strip()
    if not product_name:
        return []

    driver = get_driver()
    try:
        query = """
        MATCH (g:GoldenEntity)-[:MANUFACTURES]->(d:Drug)
        WHERE toLower(d.name) = toLower($product_name)
           OR toLower(d.name) CONTAINS toLower($product_name)
           OR toLower(g.name) = toLower($product_name)
           OR toLower(g.name) CONTAINS toLower($product_name)
        RETURN DISTINCT g.name AS company_name, d.name AS drug_name
        ORDER BY company_name, drug_name
        """

        result = driver.execute_query(
            query,
            product_name=product_name,
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


def query_fda_applications_for_company(company_name):
    company_name = (company_name or "").strip()
    if not company_name:
        return []

    normalized_name = normalize_company_name(company_name)
    driver = get_driver()
    try:
        query = """
        MATCH (r:SourceRecord)-[:RESOLVES_TO]->(g:GoldenEntity)
        WHERE
            toLower(r.name) = toLower($company_name)
            OR toLower(g.name) = toLower($company_name)
            OR toLower(r.name) = toLower($normalized_name)
            OR toLower(g.name) = toLower($normalized_name)
            OR toLower(r.name) CONTAINS toLower($company_name)
            OR toLower(g.name) CONTAINS toLower($company_name)
            OR toLower(r.name) CONTAINS toLower($normalized_name)
            OR toLower(g.name) CONTAINS toLower($normalized_name)
        OPTIONAL MATCH (g)-[:MANUFACTURES]->(d:Drug)<-[:CONCERNS]-(a:Application)
        RETURN DISTINCT g.name AS golden_name, d.name AS drug_name, a.id AS application_id
        ORDER BY g.name, d.name, a.id
        """

        result = driver.execute_query(
            query,
            company_name=company_name,
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
    - intent: one of [company_applications, product_company, company_lookup, list_manufacturers]
    - entity: a company or product string if detected; otherwise empty string
    """

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        text = response.output_text.strip()
        return __import__("json").loads(text)
    except Exception:
        return None


def answer_question(question):
    question_text = str(question or "").strip()
    if not question_text:
        return {
            "company_name": None,
            "results": [],
            "answer": "I couldn't detect a company or facility name in your question. Please enter a company name such as 'J&J' or 'Johnson & Johnson'.",
        }

    # Try the LLM first when configured so natural-language questions reach the LLM path.
    plan = _llm_plan_question(question_text)
    if plan:
        intent = str(plan.get("intent", "")).strip().lower()
        entity = str(plan.get("entity", "") or "").strip()
    else:
        intent = ""
        entity = ""

    if intent == "list_manufacturers" or _looks_like_manufacturer_list(question_text):
        rows = list_all_manufacturers()
        return {
            "company_name": None,
            "results": rows,
            "answer": (
                f"I found {len(rows)} manufacturer(s)."
                if rows else "No manufacturers were found in the graph."
            ),
        }

    product_ref = extract_product_reference(question_text)
    if (intent == "product_company" or product_ref) and (entity or product_ref):
        target = entity or product_ref
        rows = query_company_for_product(target)
        if rows:
            return {
                "company_name": rows[0].get("company_name"),
                "results": rows,
                "answer": f"{rows[0].get('company_name')} manufactures {rows[0].get('drug_name')}.",
            }

    company_name = entity or extract_company_name(question_text)
    if not company_name:
        return {
            "company_name": None,
            "results": [],
            "answer": "I couldn't detect a company or facility name in your question. Please enter a company name such as 'J&J' or 'Johnson & Johnson'.",
        }

    rows = query_fda_applications_for_company(company_name)
    return {
        "company_name": company_name,
        "results": rows,
        "answer": (
            f"I found {len(rows)} application result(s) for {company_name}."
            if rows else f"No application results were found for {company_name}."
        ),
    }


def list_all_manufacturers():
    driver = get_driver()
    try:
        query = """
        MATCH (g:GoldenEntity)-[:MANUFACTURES]->(:Drug)
        RETURN DISTINCT g.name AS manufacturer
        ORDER BY manufacturer
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


def _looks_like_manufacturer_list(question):
    text = str(question or "").lower().strip()
    if not text:
        return False

    patterns = [
        r"\blist all manufacturers\b",
        r"\bshow all manufacturers\b",
        r"\bwhat manufacturers\b",
        r"\bwhich manufacturers\b",
        r"\ball manufacturers\b",
    ]

    return any(re.search(pattern, text) for pattern in patterns)
