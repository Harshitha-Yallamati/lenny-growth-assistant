"""Ship 30 for 30 content skill.

Encodes the Ship 30 for 30 "Atomic Essay" writing rules (researched from
https://www.ship30for30.com/post/how-to-write-an-atomic-essay-a-beginners-guide)
as a structured rubric, adapted from their native ~250-word format to the
brief's ~1,250-word target while keeping the same stylistic DNA: a
promise-matching headline, skimmable formatting, bolded key points, and a
single clear takeaway. This is intentionally a dedicated module with an
explicit rubric object -- not a one-off inline prompt string -- so the rules
are visible, testable, and reusable.
"""

from dataclasses import dataclass

from app.rag.retrieval import RetrievedChunk, format_context

TARGET_WORD_COUNT = 1250
WORD_COUNT_TOLERANCE = 250  # acceptable range: 1000-1500


@dataclass
class Ship30Rubric:
    hook_rules: str
    structure_rules: str
    formatting_rules: str
    takeaway_rules: str
    grounding_rule: str


RUBRIC = Ship30Rubric(
    hook_rules=(
        "Open with a headline-style hook (as its own bold first line) that names the audience, "
        "states the topic plainly, and promises a specific, concrete payoff -- the reader should "
        "know exactly what they'll get and why it matters within the first sentence."
    ),
    structure_rules=(
        "Deliver on the hook's exact promise -- if the hook implies N points or a specific claim, "
        "the body must match it exactly (a broken promise breaks reader trust). Use a clear "
        "narrative progression: problem -> insight -> supporting evidence -> implication. Vary "
        "paragraph length to control pacing (short punchy lines mixed with longer explanatory ones)."
    ),
    formatting_rules=(
        "Skimmable formatting: use Markdown headings to break the essay into sections, bullet "
        "lists for enumerable points, and selective **bold** on the single most important phrase "
        "per section (not whole sentences). A reader skimming only headings and bold text should "
        "still get the gist."
    ),
    takeaway_rules=(
        "End with a distinct, clearly-labeled takeaway: one specific, actionable idea the reader "
        "can apply immediately -- not a generic summary of what was already said."
    ),
    grounding_rule=(
        "Every non-obvious claim must trace back to the transcript excerpts provided and be cited "
        "inline as (Source: <episode title>). Do not invent statistics, quotes, or examples."
    ),
)


def build_system_prompt(topic: str, chunks: list[RetrievedChunk]) -> str:
    context = format_context(chunks)
    context_block = context if context else "(No transcript excerpts matched this topic.)"

    return f"""You are the Lenny Growth Assistant's writing skill, producing a Ship 30 for 30-style \
essay of approximately {TARGET_WORD_COUNT} words (acceptable range: \
{TARGET_WORD_COUNT - WORD_COUNT_TOLERANCE}-{TARGET_WORD_COUNT + WORD_COUNT_TOLERANCE} words) on: \
"{topic}"

Follow this rubric exactly:

1. HOOK: {RUBRIC.hook_rules}
2. STRUCTURE: {RUBRIC.structure_rules}
3. FORMATTING: {RUBRIC.formatting_rules}
4. TAKEAWAY: {RUBRIC.takeaway_rules}
5. GROUNDING: {RUBRIC.grounding_rule}

Output the essay as Markdown. Do not include meta-commentary about the rubric itself.

Transcript excerpts to ground the essay in:
{context_block}"""


def word_count_within_tolerance(text: str) -> bool:
    count = len(text.split())
    return (TARGET_WORD_COUNT - WORD_COUNT_TOLERANCE) <= count <= (TARGET_WORD_COUNT + WORD_COUNT_TOLERANCE)
