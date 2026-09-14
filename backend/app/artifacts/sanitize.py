"""Server-side HTML sanitization for artifacts.

This is defense-in-depth, not the only line of defense: the frontend also
renders HTML artifacts inside a fully sandboxed <iframe sandbox=""> (see
design.md / architecture.md) which blocks script execution at the browser
level regardless of what slips through here. Together: no <script> tags
survive sanitization, and even if one did, the iframe sandbox refuses to
execute it and has no access to the parent page, cookies, or storage.
"""

import re

import bleach

# bleach.clean() removes disallowed tags but, by design since bleach 2.x,
# leaves their text content behind (so a stripped <script> tag would leave
# its JS source sitting in the page as plain text). Strip script blocks
# entirely, content included, before handing off to bleach for everything
# else (event-handler attributes, javascript: URLs, disallowed tags).
_SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*/?>", re.IGNORECASE)

ALLOWED_TAGS = [
    "div", "span", "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "td", "th",
    "strong", "em", "b", "i", "u", "s", "small", "mark",
    "a", "img", "blockquote", "code", "pre", "style",
    "section", "article", "header", "footer", "nav", "main", "figure", "figcaption",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "style"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
}

ALLOWED_PROTOCOLS = ["http", "https", "data"]


def sanitize_html_artifact(raw_html: str) -> str:
    without_scripts = _SCRIPT_BLOCK_RE.sub("", raw_html)
    without_scripts = _SCRIPT_TAG_RE.sub("", without_scripts)  # unclosed <script> tags
    return bleach.clean(
        without_scripts,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
