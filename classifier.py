from __future__ import annotations

from typing import Iterable

AGE_SCORE = 0

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

AGE_BIGRAMS = { 
    ("how", "old"),
    ("years", "old"),
    ("year", "old"),

    ("age", "group"),
    ("age", "range"),
    ("your", "age")
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


def _has_age_context(tokens: Iterable[str]) -> bool:
    global AGE_SCORE
    token_list = list(tokens)
    if not token_list:
        return False
    if any(token in AGE_HINTS for token in token_list):
        AGE_SCORE += 5
        return True
    bigrams = {
        (token_list[i], token_list[i + 1])
        for i in range(len(token_list) - 1)
    }
    if any(bigram in AGE_BIGRAMS for bigram in bigrams):
        AGE_SCORE += 5
        return True
    return False


def classify_age_header(header: str) -> dict[str, str | bool]:
    global AGE_SCORE
    normalized = normalize_header_text(header)
    tokens = tokenize_text(normalized)
    if not tokens:
        AGE_SCORE = 0
        return {"label": "Not Age", "reason": "No meaningful tokens found"}

    token_set = set(tokens)

    if token_set.intersection(EXTERNAL_ENTITIES):
        AGE_SCORE -= 5
        # return {
        #     "label": "Not Age",
        #     "reason": "Refers to an external entity such as a patient, pet, customer, or product",
        # }

    if token_set.intersection(SELF_TERMS):
        AGE_SCORE += 5
        # return {"label": "Age", "reason": "Contains a self/owner reference"}

    if _has_age_context(tokens):
        # if token_set.intersection(AGE_MODIFIERS):
        #     AGE_SCORE += 5
            # return {"label": "Age", "reason": "Contains age-related wording with a common field modifier"}
        if AGE_SCORE >= 5:
            return {"label": "Age", "reason": "Contains enough age-related wording"}

    return {"label": "Not Age", "reason": "No enough age-related evidence found"}