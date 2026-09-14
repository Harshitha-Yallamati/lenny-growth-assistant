"""Artifact generation skill: turns the current conversation into a standalone
Markdown document or an HTML/CSS snippet, rendered client-side in the
Artifact Viewer instead of dumped as a raw code block in the chat."""

import re

from app.rag.retrieval import RetrievedChunk, format_context

HTML_TRIGGERS = ["as html", "as an html", "html page", "html snippet", "html/css", "render this as html"]
MARKDOWN_TRIGGERS = [
    "as markdown",
    "as a markdown",
    "markdown document",
    "one-pager",
    "generate a doc",
    "create a document",
    "write this up as a doc",
]

_CODE_BLOCK_RE = re.compile(r"```(?:markdown|html)?\n(.*?)```", re.DOTALL)


def detect_artifact_format(message: str) -> str | None:
    lowered = message.lower()
    if any(trigger in lowered for trigger in HTML_TRIGGERS):
        return "html"
    if any(trigger in lowered for trigger in MARKDOWN_TRIGGERS):
        return "markdown"
    return None


def build_system_prompt(fmt: str, chunks: list[RetrievedChunk]) -> str:
    context = format_context(chunks)
    context_block = f"\n\nRelevant transcript excerpts:\n{context}" if context else ""

    if fmt == "html":
        format_rules = (
            "Output a single self-contained HTML snippet: inline <style> only, no <script> tags, "
            "no external resource loads (no <link>, no remote images/fonts), no event-handler "
            "attributes (onclick, onload, etc.), no <iframe>, no <form> that submits anywhere. "
            "Assume it will be rendered in a sandboxed iframe with scripts disabled."
        )
    else:
        format_rules = "Output clean, well-structured Markdown (headings, bullets, bold where useful)."

    return f"""You are the Lenny Growth Assistant's artifact skill. Based on the conversation so far, \
produce a standalone {fmt.upper()} artifact that captures the requested content.

{format_rules}

Respond with ONLY a single fenced code block containing the artifact, tagged ```{fmt}, and nothing \
else outside the code block.{context_block}"""


def extract_artifact_content(raw_text: str) -> str:
    match = _CODE_BLOCK_RE.search(raw_text)
    if match:
        return match.group(1).strip()
    return raw_text.strip()
