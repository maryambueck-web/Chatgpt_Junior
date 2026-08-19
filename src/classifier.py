import re
from dataclasses import dataclass
from typing import List, Tuple

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

# Term phrases are matched loosely rather than as exact substrings: each word is
# matched as a stem (so "hurt myself" also catches "hurting myself"/"hurts myself"),
# and up to a few filler words are tolerated between the phrase's words (so "hide
# from my parents" also catches "hide dangerous instructions from my parents").
# This trades a little false-positive risk for fewer missed unsafe messages, which
# is the right tradeoff for a child-safety filter.
_MAX_GAP_WORDS = 3


def _term_pattern(term: str) -> re.Pattern:
    word_patterns = [r"\b" + re.escape(word) + r"\w*\b" for word in term.split()]
    if len(word_patterns) == 1:
        return re.compile(word_patterns[0])
    gap = r"(?:\s+\S+){0,%d}\s+" % _MAX_GAP_WORDS
    return re.compile(gap.join(word_patterns))


def _compile_terms(terms: List[str]) -> List[Tuple[str, re.Pattern]]:
    return [(term, _term_pattern(term)) for term in terms]


_BYPASS_PATTERNS = _compile_terms(BYPASS_TERMS)
_SELF_HARM_PATTERNS = _compile_terms(SELF_HARM_TERMS)
_EATING_PATTERNS = _compile_terms(EATING_TERMS)
_SEXUAL_PATTERNS = _compile_terms(SEXUAL_TERMS)
_DRUG_PATTERNS = _compile_terms(DRUG_TERMS)
_WEAPON_PATTERNS = _compile_terms(WEAPON_TERMS)
_VIOLENCE_PATTERNS = _compile_terms(VIOLENCE_TERMS)
_GAMBLING_PATTERNS = _compile_terms(GAMBLING_TERMS)


def _contains(text: str, compiled_terms: List[Tuple[str, re.Pattern]]) -> List[str]:
    low = text.lower()
    return [term for term, pattern in compiled_terms if pattern.search(low)]


def classify(text: str) -> Classification:
    low = text.lower()

    bypass = _contains(low, _BYPASS_PATTERNS)
    if bypass:
        return Classification("bypass", "high", [f"Bypass/jailbreak term: {t}" for t in bypass])

    checks = [
        ("self_harm", _SELF_HARM_PATTERNS),
        ("eating_disorder", _EATING_PATTERNS),
        ("sexual", _SEXUAL_PATTERNS),
        ("drugs", _DRUG_PATTERNS),
        ("weapons", _WEAPON_PATTERNS),
        ("violence", _VIOLENCE_PATTERNS),
        ("gambling", _GAMBLING_PATTERNS),
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
