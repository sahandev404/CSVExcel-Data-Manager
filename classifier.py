from __future__ import annotations
from typing import Iterable

AGE_HINTS = {
    "age",
    "years",
    "year",
    "old",
    "elder",
    "young",
    "aged",
}

SELF_TERMS = {
    "your",
    "you",
    "current",
    "my",
    "respondent",
    "participant",
    "subject",
    "owner",
    "self",
    "me",
}

EXTERNAL_ENTITIES = {
    "patient",
    "patients",
    "child",
    "children",
    "customer",
    "customers",
    "client",
    "clients",
    "employee",
    "employees",
    "staff",
    "student",
    "students",
    "member",
    "members",
    "family",
    "household",
    "parent",
    "parents",
    "spouse",
    "spouses",
    "partner",
    "partners",
    "dog",
    "dogs",
    "cat",
    "cats",
    "pet",
    "pets",
    "product",
    "products",
    "item",
    "items",
    "vehicle",
    "vehicles",
    "car",
    "cars",
    "house",
    "houses",
    "property",
    "properties",
}

AGE_MODIFIERS = {
    "group",
    "range",
    "limit",
    "bracket",
    "distribution",
    "category",
    "and",
    "or",
    "by",
    "to",
    "from",
    "in",

    "lived",
    "living",
    "live",
    "birthday",
    "birthdays",
    "duration",
    "born",
}

DIFFERENT_TIME_REFERENCES = {
    "recent",
    "when",
    "at",
    "by",
    "from"
}

AGE_BIGRAMS = { 
    ("how", "old"),
    ("years", "old"),
    ("year", "old"),

    ("age", "group"),
    ("age", "range"),
    ("your", "age"),
    ("current", "age")
}

EXTERNAL_BIGRAMS = {
    ("age", "of"),
    ("age", "in"),
    ("age", "at"),
    ("age", "for"),
    ("age", "by"),
    ("age", "from"),
    ("age", "to"),
    ("age", "and"),
    ("age", "or")
}


def tokenize_text(text: str) -> list[str]:
    if not text:
        return []
    tokens: list[str] = []
    current: list[str] = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


def normalize_header_text(text: str) -> str:
    return " ".join(tokenize_text(text))


def _score_age_context(tokens: Iterable[str]) -> tuple[int, list[str]]:
    token_list = list(tokens)
    if not token_list:
        return 0, []

    token_set = set(token_list)
    score = 0
    reasons: list[str] = []

    if token_set.intersection(DIFFERENT_TIME_REFERENCES):
        score -= 8
        reasons.append("time reference")

    if token_set.intersection(EXTERNAL_ENTITIES):
        score -= 8
        reasons.append("external entity")

    if token_set.intersection(SELF_TERMS):
        score += 3
        reasons.append("self reference")

    if any(token in AGE_HINTS for token in token_list):
        score += 4
        reasons.append("age-related wording")

    bigrams = {
        (token_list[i], token_list[i + 1])
        for i in range(len(token_list) - 1)
    }
    if any(bigram in AGE_BIGRAMS for bigram in bigrams):
        score += 8
        reasons.append("age phrase")
    
    if any(bigram in EXTERNAL_BIGRAMS for bigram in bigrams):
        score -= 8
        reasons.append("external age reference")

    return score, reasons


def classify_age_header(header: str) -> dict[str, str | bool]:
    normalized = normalize_header_text(header)
    tokens = tokenize_text(normalized)
    if not tokens:
        return {"label": "Not Age", "reason": "No meaningful tokens found"}

    score, reasons = _score_age_context(tokens)

    if score <= 0:
        if "external entity" in reasons:
            return {
                "label": "Not Age",
                "reason": "Contains an external entity reference rather than age information",
            }
        if "external age reference" in reasons:
            return {
                "label": "Not Age",
                "reason": "Contains an external age reference rather than age information",
            }
 
    if score < 8:
        return {
            "label": "Not Age",
            "reason": "Contains some age-related wording but not enough to classify as age",
        }

    if score >= 8:
        if "self reference" in reasons:
            return {
                "label": "Age",
                "reason": "Contains self/owner reference and age-related wording",
            }
        return {"label": "Age", "reason": "Contains enough age-related wording"}

    return {"label": "Not Age", "reason": "No enough age-related evidence found"}