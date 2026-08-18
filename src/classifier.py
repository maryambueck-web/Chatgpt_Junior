from dataclasses import dataclass
from typing import List

@dataclass
class Classification:
    category: str
    severity: str
    reasons: List[str]

BYPASS_TERMS = [
    "ignore previous", "ignore the rules", "disable parental", "turn off parental",
    "pretend i am 18", "pretend i am 21", "jailbreak", "developer mode",
    "hide from my parents", "bypass", "uncensored", "encode your answer"
]

SELF_HARM_TERMS = ["kill myself", "suicide", "self harm", "hurt myself", "end my life"]
EATING_TERMS = ["starve", "purge", "lose weight fast", "not eating", "thinspo"]
SEXUAL_TERMS = ["porn", "explicit sex", "nudes", "sexting"]
DRUG_TERMS = ["drugs", "drug", "cocaine", "heroin", "weed", "meth", "get high", "make drugs"]
WEAPON_TERMS = ["make a bomb", "build a gun", "knife attack", "weapon instructions"]
VIOLENCE_TERMS = ["torture", "graphic violence", "how to hurt", "how to fight"]
GAMBLING_TERMS = ["online casino", "sports betting", "gambling trick"]

EDUCATIONAL_HINTS = ["homework", "school", "assignment", "learn", "explain", "what is", "why", "history"]
INSTRUCTIONAL_HINTS = ["how to make", "steps to", "instructions", "recipe", "hide", "avoid getting caught"]


def _contains(text: str, terms: List[str]) -> List[str]:
    low = text.lower()
    return [term for term in terms if term in low]


def classify(text: str) -> Classification:
    low = text.lower()

    bypass = _contains(low, BYPASS_TERMS)
    if bypass:
        return Classification("bypass", "high", [f"Bypass/jailbreak term: {t}" for t in bypass])

    checks = [
        ("self_harm", SELF_HARM_TERMS),
        ("eating_disorder", EATING_TERMS),
        ("sexual", SEXUAL_TERMS),
        ("drugs", DRUG_TERMS),
        ("weapons", WEAPON_TERMS),
        ("violence", VIOLENCE_TERMS),
        ("gambling", GAMBLING_TERMS),
    ]

    for category, terms in checks:
        hits = _contains(low, terms)
        if hits:
            educational = any(h in low for h in EDUCATIONAL_HINTS)
            instructional = any(h in low for h in INSTRUCTIONAL_HINTS)
            if category in {"self_harm", "weapons"} or instructional:
                return Classification(category, "high", [f"High-risk term: {t}" for t in hits])
            if educational:
                return Classification(category, "medium", [f"Sensitive educational topic: {t}" for t in hits])
            return Classification(category, "medium", [f"Sensitive term: {t}" for t in hits])

    return Classification("general", "low", ["No restricted category detected"])
