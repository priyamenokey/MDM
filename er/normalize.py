import re

ALIASES = {
    "j&j": "johnson and johnson",
    "j and j": "johnson and johnson",
    "pfizer incorporated": "pfizer",
    "johnson and johnson inc": "johnson and johnson",
    "johnson and johnson inc.": "johnson and johnson",
}


def normalize_company_name(name):
    original = str(name).lower().strip()

    if original in ALIASES:
        return ALIASES[original]

    name = original
    name = name.replace("&", "and")

    name = re.sub(
        r"\b(incorporated|inc|corp|corporation|llc|ltd|limited)\b",
        "",
        name,
    )

    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip()
