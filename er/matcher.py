from rapidfuzz.fuzz import ratio

from er.normalize import normalize_company_name


def similarity(record1, record2):
    name1 = normalize_company_name(record1["name"])
    name2 = normalize_company_name(record2["name"])

    name_score = ratio(name1, name2) / 100

    address1 = record1.get("address", "").lower()
    address2 = record2.get("address", "").lower()
    address_score = ratio(address1, address2) / 100

    country_score = 1.0 if record1.get("country") == record2.get("country") else 0

    final_score = name_score * 0.6 + address_score * 0.3 + country_score * 0.1

    return round(final_score, 3)
