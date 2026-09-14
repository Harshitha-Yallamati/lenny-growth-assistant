from app.agent.orchestrator import _detect_skill
from app.agent.skills.artifact_skill import detect_artifact_format
from app.agent.skills.ship30_skill import (
    MIN_WORD_COUNT,
    build_expansion_prompt,
    needs_expansion,
    word_count_within_tolerance,
)


def test_defaults_to_qa_skill():
    assert _detect_skill("What's the best way to price a B2B SaaS product?", None) == "qa"


def test_detects_ship30_intent_from_keywords():
    assert _detect_skill("Can you turn this into an essay for me?", None) == "ship30"
    assert _detect_skill("Ship 30 style piece on onboarding please", None) == "ship30"


def test_detects_artifact_intent_from_keywords():
    assert _detect_skill("Generate a markdown document summarizing this", None) == "artifact"
    assert _detect_skill("Render this as an HTML page", None) == "artifact"


def test_explicit_requested_skill_overrides_detection():
    assert _detect_skill("This looks like a normal question", "ship30") == "ship30"


def test_artifact_format_detection():
    assert detect_artifact_format("write this up as html") == "html"
    assert detect_artifact_format("create a document for me") == "markdown"
    assert detect_artifact_format("just answer my question") is None


def test_word_count_tolerance():
    short_text = "word " * 100
    on_target_text = "word " * 1250
    assert not word_count_within_tolerance(short_text)
    assert word_count_within_tolerance(on_target_text)


def test_short_draft_is_flagged_for_expansion():
    """llama3.1 returned a 546-word draft against a ~1,250-word target, so
    under-length output has to trigger the second pass, not just a log line."""
    assert needs_expansion("word " * 546)
    assert not needs_expansion("word " * 1200)


def test_expansion_prompt_carries_the_draft_and_the_requirements():
    draft = "A short draft about onboarding. (Source: Some Episode)"
    prompt = build_expansion_prompt(draft)
    assert draft in prompt, "the model needs the draft to expand rather than restart"
    assert str(MIN_WORD_COUNT) in prompt
    assert "## The Takeaway" in prompt
