from app.agent.orchestrator import _detect_skill, _retrieval_query
from app.agent.skills import smalltalk_skill
from app.agent.skills.artifact_skill import detect_artifact_format
from app.agent.skills.ship30_skill import (
    MIN_HEADINGS,
    MIN_WORD_COUNT,
    NOT_GROUNDED_PROMPT,
    build_expansion_prompt,
    build_system_prompt,
    count_h2_headings,
    draft_issues,
    has_bulleted_list,
    has_takeaway_heading,
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


def test_ship30_refuses_instead_of_writing_an_ungrounded_essay():
    """Regression: with no matching chunks, the skill used to hand the model
    a rubric to fill in anyway ("(No transcript excerpts matched this
    topic.)"), which a small model happily filled with fabricated statistics
    and a fake citation instead of refusing. No chunks must produce the same
    honest-refusal prompt the QA skill uses, not an essay-writing rubric."""
    prompt = build_system_prompt("a topic the corpus doesn't cover", [])
    assert prompt == NOT_GROUNDED_PROMPT
    assert "1,250" not in prompt
    assert "Hard requirements" not in prompt


def test_counts_only_h2_headings_not_h3():
    text = "## Real Heading\n\n### Not This One\n\n#### Or This\n\n## Another Real One"
    assert count_h2_headings(text) == 2


def test_detects_bulleted_and_numbered_lists():
    assert has_bulleted_list("Some text\n\n- a point\n- another point\n")
    assert has_bulleted_list("Some text\n\n1. a point\n2. another point\n")
    assert not has_bulleted_list("Just prose, no lists anywhere in this draft.")


def test_takeaway_heading_requires_exact_h2_level():
    assert has_takeaway_heading("## Intro\n\n## The Takeaway\n\nDo the thing.")
    assert not has_takeaway_heading("## Intro\n\n### The Takeaway\n\nDo the thing.")
    assert not has_takeaway_heading("## Intro\n\n## Conclusion\n\nDo the thing.")


def test_draft_issues_catches_structural_violations_word_count_alone_misses():
    """Regression: a live-generated 1,081-word essay (within tolerance) used
    zero `## ` headings and `### The Takeaway` instead of `## The Takeaway`.
    Word-count checking alone reported no problem; draft_issues must not."""
    padding = "Some prose to pad the length out and make this draft long enough. " * 150
    on_length_but_broken_structure = (
        f"**A Hook**\n\n### Problem\n\n{padding}\n\n### The Takeaway\n\nOne actionable idea."
    )
    assert len(on_length_but_broken_structure.split()) >= MIN_WORD_COUNT
    issues = draft_issues(on_length_but_broken_structure)
    assert any("headings" in issue for issue in issues)
    assert any("Takeaway" in issue for issue in issues)
    assert any("bulleted list" in issue for issue in issues)


def test_retrieval_query_strips_skill_boilerplate_but_keeps_the_topic():
    """Regression: the raw request "Write a Ship 30 essay on onboarding" was
    used verbatim as the retrieval query, and Postgres's ts_rank scored it at
    0.027 -- below the 0.03 relevance floor -- even though "onboarding" alone
    scores 0.083 on this corpus. The skill-invocation phrasing must not
    survive into the query; the topic must."""
    cleaned = _retrieval_query("Write a Ship 30 essay on onboarding")
    assert "onboarding" in cleaned
    assert "ship 30" not in cleaned
    assert "essay" not in cleaned
    assert "write" not in cleaned


def test_retrieval_query_strips_artifact_boilerplate():
    cleaned = _retrieval_query(
        "Generate an HTML page summarizing product-market fit signals"
    )
    assert "product-market fit signals" in cleaned
    assert "html page" not in cleaned
    assert "generate" not in cleaned


def test_retrieval_query_falls_back_to_original_if_stripping_empties_it():
    cleaned = _retrieval_query("Write an essay")
    assert cleaned == "Write an essay"


def test_draft_issues_empty_when_rubric_is_fully_satisfied():
    sections = "\n\n".join(
        f"## Section {i}\n\n" + ("Some prose to pad the length out. " * 60) for i in range(MIN_HEADINGS)
    )
    good_draft = (
        "**A Hook**\n\n"
        + sections
        + "\n\n- a bullet point\n- another bullet point"
        + "\n\n## The Takeaway\n\nOne actionable idea."
    )
    assert len(good_draft.split()) >= MIN_WORD_COUNT
    assert not draft_issues(good_draft)


def test_smalltalk_detects_bare_greetings():
    """Regression: "hey" used to be routed through QA, where retrieval found
    nothing and the assistant gave the generic "not covered" refusal --
    technically honest, but reads as broken for a plain hello."""
    assert smalltalk_skill.detect("hey") == smalltalk_skill.GREETING_RESPONSE
    assert smalltalk_skill.detect("Hi!") == smalltalk_skill.GREETING_RESPONSE
    assert smalltalk_skill.detect("  Good Morning.  ") == smalltalk_skill.GREETING_RESPONSE
    assert smalltalk_skill.detect("hello") == smalltalk_skill.GREETING_RESPONSE


def test_smalltalk_detects_thanks_separately_from_greetings():
    assert smalltalk_skill.detect("thanks") == smalltalk_skill.THANKS_RESPONSE
    assert smalltalk_skill.detect("Thank you!") == smalltalk_skill.THANKS_RESPONSE
    assert smalltalk_skill.THANKS_RESPONSE != smalltalk_skill.GREETING_RESPONSE


def test_smalltalk_does_not_swallow_a_real_question_with_a_greeting_prefix():
    """"hey, what are retention curves" must still reach the QA skill -- only
    a message that is *nothing but* a greeting/thanks should short-circuit."""
    assert smalltalk_skill.detect("hey, what are retention curves") is None
    assert smalltalk_skill.detect("hello, can you help with pricing") is None
    assert smalltalk_skill.detect("thanks, and also what is PMF") is None


def test_smalltalk_does_not_match_ordinary_questions():
    assert smalltalk_skill.detect("what are retention curves") is None
    assert smalltalk_skill.detect("how do I price a B2B product") is None
