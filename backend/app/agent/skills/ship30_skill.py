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

import re
from dataclasses import dataclass

from app.rag.retrieval import RetrievedChunk, format_context

TARGET_WORD_COUNT = 1250
WORD_COUNT_TOLERANCE = 250  # acceptable range: 1000-1500
MIN_WORD_COUNT = TARGET_WORD_COUNT - WORD_COUNT_TOLERANCE
MIN_HEADINGS = 4

# What the expansion pass asks for when length is the (or a) problem -- not
# the bare MIN_WORD_COUNT floor itself. Live-verified: a retry asked for "at
# least 1,000 words" landed at 995, five words short of its own stated
# target. A model that treats a stated minimum as a loose target rather than
# a hard line tends to stop just under it, so asking for a number well above
# the true floor gives room for that undershoot without changing what
# actually counts as passing. Stays within the rubric's own upper tolerance
# (1,500) so hitting it exactly is still a valid essay, not an overshoot.
EXPANSION_TARGET_WORD_COUNT = TARGET_WORD_COUNT + 100

# `##\s` alone would also match `### Heading` (its first two characters are
# also `##`) -- the `\s` only rejects that because the third character of an
# H3 line is a literal `#`, not whitespace, so this correctly counts H2-only.
_H2_HEADING_RE = re.compile(r"(?m)^##[ \t]+\S")
_BULLET_RE = re.compile(r"(?m)^[ \t]*(?:[-*][ \t]+\S|\d+\.[ \t]+\S)")
_TAKEAWAY_HEADING_RE = re.compile(r"(?mi)^##[ \t]+the takeaway[ \t]*$")


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


NOT_GROUNDED_PROMPT = """You are the Lenny Growth Assistant's writing skill. No relevant excerpts were \
found in the Lenny's Podcast transcript knowledge base for this essay topic. Tell the user plainly and \
briefly that you can't write a grounded Ship 30 essay on this topic because the knowledge base doesn't \
cover it. Do not write the essay, do not invent statistics, examples, or sources to fill the gap. Suggest \
they try a topic the transcripts do cover (product-market fit, growth loops, activation, onboarding, \
pricing, retention, PLG vs. sales, growth teams, positioning, prioritization)."""


def build_system_prompt(topic: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return NOT_GROUNDED_PROMPT

    context = format_context(chunks)
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

Hard requirements -- an essay that misses any of these is incomplete:
- At least {MIN_WORD_COUNT} words. This is a long-form essay, not a summary. Do not stop early.
- At least {MIN_HEADINGS} Markdown section headings written as `## Heading`.
- At least one bulleted list.
- A final section headed `## The Takeaway`.

Output the essay as Markdown. Do not include meta-commentary about the rubric itself.

Transcript excerpts to ground the essay in:
{context}"""


def build_expansion_prompt(draft: str, issues: list[str] | None = None) -> str:
    """Second-pass prompt used when a draft violates one of the rubric's hard
    requirements -- under length, too few headings, no bulleted list, or a
    missing/wrong-level takeaway heading.

    Small local models reliably under-write a ~1,250-word target -- llama3.1
    returned 546 words with no headings on the first pass -- and separately,
    a draft can hit the word count while still using zero `## ` headings or
    an `### The Takeaway` instead of the required `## `. Detecting either and
    only logging it (the original behavior) still shipped an essay that
    missed the brief, so this pass names the actual problem and asks the
    model to fix it rather than assuming "too short" is always the issue.
    """
    words = len(draft.split())
    if issues is None:
        issues = draft_issues(draft)
    issues_text = "; ".join(issues) if issues else "not clearly meeting the rubric's hard requirements"

    # Only ask for more length when length is actually one of the unmet
    # requirements -- a draft being revised solely for e.g. a missing
    # bulleted list shouldn't be pushed to pad further just because it's
    # already being touched.
    if needs_expansion(draft):
        length_requirement = (
            f"at least {EXPANSION_TARGET_WORD_COUNT} words -- do not stop at exactly "
            f"{MIN_WORD_COUNT}; treat that as a line you must clear with room to spare, not a "
            f"target to land on, since stopping right at it risks falling just short"
        )
    else:
        length_requirement = f"at least {MIN_WORD_COUNT} words (already satisfied -- do not shorten it)"

    return f"""The draft below is {words} words. It does not yet satisfy the required rubric: {issues_text}.

Revise it to fully satisfy the rubric. Keep the existing hook, argument, structure, and all \
(Source: ...) citations intact -- do not restate or summarize the draft, and do not invent claims \
that aren't supported by it. Deepen it by developing the existing points with more explanation, \
concrete implications, and worked examples drawn from the material already cited.

The finished piece must have: {length_requirement}, at least {MIN_HEADINGS} `## ` section \
headings (exactly two hash marks, not three), at least one bulleted list, and a final section headed \
exactly `## The Takeaway` (not `### The Takeaway` or any other level).

Return ONLY the finished, revised essay in Markdown -- no preamble, no commentary.

DRAFT:
{draft}"""


def word_count_within_tolerance(text: str) -> bool:
    count = len(text.split())
    return (TARGET_WORD_COUNT - WORD_COUNT_TOLERANCE) <= count <= (TARGET_WORD_COUNT + WORD_COUNT_TOLERANCE)


def needs_expansion(text: str) -> bool:
    return len(text.split()) < MIN_WORD_COUNT


def count_h2_headings(text: str) -> int:
    return len(_H2_HEADING_RE.findall(text))


def has_bulleted_list(text: str) -> bool:
    return bool(_BULLET_RE.search(text))


def has_takeaway_heading(text: str) -> bool:
    return bool(_TAKEAWAY_HEADING_RE.search(text))


def draft_issues(text: str) -> list[str]:
    """Which of the rubric's hard requirements this draft is currently missing.

    Word count was previously the only requirement checked in code -- the
    "at least 4 `## ` headings" / "a bulleted list" / "`## The Takeaway`"
    rules existed only as prompt instructions, so a model could violate them
    (e.g. write `### The Takeaway` instead of `## The Takeaway`, or use zero
    H2 headings) without it ever being detected. Reproduced live: a
    1,081-word essay with the right length passed the only check that
    existed, despite using zero `## ` headings and an H3 takeaway.
    """
    issues = []
    words = len(text.split())
    if words < MIN_WORD_COUNT:
        issues.append(f"under {MIN_WORD_COUNT} words ({words})")
    if count_h2_headings(text) < MIN_HEADINGS:
        issues.append(f"fewer than {MIN_HEADINGS} `## ` headings ({count_h2_headings(text)})")
    if not has_bulleted_list(text):
        issues.append("no bulleted list")
    if not has_takeaway_heading(text):
        issues.append("missing a `## The Takeaway` heading")
    return issues
