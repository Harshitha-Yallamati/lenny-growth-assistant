"""Deterministic handling for simple conversational messages (greetings,
acknowledgements) that aren't product/growth questions.

Before this skill existed, "hey" was routed through the QA skill like any
other message: retrieval found nothing relevant, and the assistant returned
the generic "the knowledge base doesn't cover this" refusal -- technically
correct, but it reads as broken to a user who just said hello, and it spends
an Ollama generation on something with an obvious, deterministic answer.
This never touches retrieval or the LLM.
"""

import re

_TRAILING_PUNCTUATION_RE = re.compile(r"[!?.,;:]+$")

_GREETINGS = {
    "hi", "hey", "hello", "hiya", "howdy", "yo",
    "good morning", "good afternoon", "good evening", "good night",
}

_THANKS = {
    "thanks", "thank you", "thanks a lot", "thank you so much", "thx", "ty",
}

GREETING_RESPONSE = (
    "Hey! I'm the Lenny Growth Assistant. I can help with product management, growth, PMF, "
    "onboarding, pricing, retention, and growth loops. What are you working on?"
)
THANKS_RESPONSE = "You're welcome! Let me know if you have another product or growth question."


def _normalize(message: str) -> str:
    return _TRAILING_PUNCTUATION_RE.sub("", message.strip().lower()).strip()


def detect(message: str) -> str | None:
    """A canned response if `message` is nothing but a greeting/thanks, or
    None if it should be routed normally.

    Only matches when the *entire* message (after trimming trailing
    punctuation) is one of the known phrases, so "hey, what are retention
    curves" still reaches the QA skill -- this is for messages that carry no
    actual question at all.
    """
    normalized = _normalize(message)
    if normalized in _THANKS:
        return THANKS_RESPONSE
    if normalized in _GREETINGS:
        return GREETING_RESPONSE
    return None
