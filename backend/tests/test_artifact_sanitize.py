from app.artifacts.sanitize import sanitize_html_artifact


def test_strips_script_tags_entirely():
    raw = "<div>Hello</div><script>alert('xss')</script>"
    clean = sanitize_html_artifact(raw)
    assert "<script" not in clean
    assert "alert" not in clean
    assert "<div>Hello</div>" in clean


def test_strips_inline_event_handlers():
    raw = '<button onclick="stealCookies()">Click me</button>'
    clean = sanitize_html_artifact(raw)
    assert "onclick" not in clean
    assert "stealCookies" not in clean


def test_strips_javascript_href():
    raw = '<a href="javascript:alert(1)">link</a>'
    clean = sanitize_html_artifact(raw)
    assert "javascript:" not in clean


def test_keeps_safe_structural_and_style_tags():
    raw = "<style>.card{color:red}</style><section class=\"card\"><h2>Title</h2><p>Body</p></section>"
    clean = sanitize_html_artifact(raw)
    assert "<style>" in clean
    assert "<h2>Title</h2>" in clean
    assert "<p>Body</p>" in clean
