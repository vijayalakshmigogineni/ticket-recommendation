"""Text preprocessing shared by both pipeline halves:
- Offline: "Interaction Preprocessing" (clean HTML, remove signatures &
  disclaimers, normalize text, extract metadata) before embedding.
- Online: "Email Preprocessing" (clean HTML, remove signatures, extract
  subject & body, normalize text) on the incoming email before embedding it.

Also strips quoted reply chains / forwarded-message history (plain `>`
quoting, "On ... wrote:" preambles, Outlook original-message/forwarded
banners, pasted From/Sent/To/Subject header blocks, HTML blockquotes) so a
broken-threading email's *new* content isn't diluted by old thread text it
still happens to carry visually.

Deliberately dependency-light (stdlib only) -- this is a correctness
prototype, not a production-grade email parser. In particular, the HTML
skip-stack in _HTMLTextExtractor assumes reasonably well-formed markup;
unbalanced tags in a malformed email can leave stale skip state for the
rest of the document.
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_SIGNATURE_LINE_PATTERNS = [
    r"^--\s*$",
    r"^best regards[, ]*$",
    r"^regards[, ]*$",
    r"^sincerely[, ]*$",
    r"^thanks[, ]*$",
    r"^thank you[, ]*$",
    r"^many thanks[, ]*$",
    r"^cheers[, ]*$",
    r"^sent from my (iphone|ipad|android|mobile device)\s*$",
    r"^get outlook for (ios|android)\s*$",
]
_SIGNATURE_LINE_RE = re.compile(
    "|".join(f"(?:{p})" for p in _SIGNATURE_LINE_PATTERNS), re.IGNORECASE
)

_DISCLAIMER_MARKERS = [
    "this email and any files transmitted with it are confidential",
    "this message contains confidential information",
    "please consider the environment before printing",
]

_MIN_CHARS_BEFORE_SIGNATURE_CUT = 40

# --- Quoted reply chain / forwarded message detection -------------------
# Broken-threading emails (the exact case the AI retrieval path exists for --
# thread detection already failed to auto-attach them) very often still
# visually carry the prior message below the new content. Left in, that old
# text pollutes the embedding/keyword-search signal for the *new* message.
# We cut everything from the start of the quoted block onward (classic
# top-posting: new content first, old thread trails it).

_QUOTE_MARKER_LINE_PATTERNS = [
    r"^-{2,}\s*original message\s*-{2,}$",
    r"^-{2,}\s*forwarded message\s*-{2,}$",
    r"^_{5,}$",  # Outlook plain-text separator line above a pasted header block
    r"^on\s.{1,120}\swrote:$",  # Gmail/Apple Mail "On <date>, <name> wrote:" preamble
]
_QUOTE_MARKER_RE = re.compile(
    "|".join(f"(?:{p})" for p in _QUOTE_MARKER_LINE_PATTERNS), re.IGNORECASE
)

_FORWARD_FROM_LINE_RE = re.compile(r"^from:\s*.+$", re.IGNORECASE)
_FORWARD_SENT_OR_DATE_RE = re.compile(r"^(sent|date):", re.IGNORECASE)
_FORWARD_TO_RE = re.compile(r"^to:", re.IGNORECASE)
_FORWARD_SUBJECT_RE = re.compile(r"^subject:", re.IGNORECASE)

_MIN_CHARS_BEFORE_QUOTE_CUT = 40


def _find_quote_block_start(lines: list[str]) -> int | None:
    """First line that starts a `>`-quoted block or matches a known
    quote/forward banner pattern."""
    cursor = 0
    for idx, line in enumerate(lines):
        line_start = cursor
        cursor += len(line) + 1
        if line_start < _MIN_CHARS_BEFORE_QUOTE_CUT:
            continue
        stripped = line.strip()
        if stripped.startswith(">") or _QUOTE_MARKER_RE.match(stripped):
            return idx
    return None


def _find_pasted_header_block_start(lines: list[str]) -> int | None:
    """Outlook-style pasted reply/forward: a `From:` line followed within a
    few lines by `Sent:`/`Date:`, `To:`, and `Subject:` lines."""
    cursor = 0
    for idx, line in enumerate(lines):
        line_start = cursor
        cursor += len(line) + 1
        stripped = line.strip()
        if line_start < _MIN_CHARS_BEFORE_QUOTE_CUT:
            continue
        if not _FORWARD_FROM_LINE_RE.match(stripped):
            continue
        window = [w.strip() for w in lines[idx + 1 : idx + 5]]
        has_sent_or_date = any(_FORWARD_SENT_OR_DATE_RE.match(w) for w in window)
        has_to = any(_FORWARD_TO_RE.match(w) for w in window)
        has_subject = any(_FORWARD_SUBJECT_RE.match(w) for w in window)
        if has_sent_or_date and has_to and has_subject:
            return idx
    return None


def strip_quoted_history(text: str) -> str:
    """Cuts everything from the start of a quoted reply chain / forwarded
    message onward. No-op if no such marker is found."""
    lines = text.split("\n")
    candidates = [
        idx
        for idx in (_find_quote_block_start(lines), _find_pasted_header_block_start(lines))
        if idx is not None
    ]
    if not candidates:
        return text
    return "\n".join(lines[: min(candidates)])


_VOID_TAGS = {
    "br", "hr", "img", "meta", "input", "link", "area", "base", "col",
    "embed", "source", "track", "wbr",
}
# Tags whose entire content is old quoted history, not the new message --
# skipped entirely, same treatment as script/style.
_SKIP_TAGS = {"script", "style", "blockquote"}
_QUOTE_CLASS_MARKERS = ("gmail_quote", "gmail_extra", "yahoo_quoted", "moz-cite-prefix")
_BLOCK_SEPARATOR_TAGS = {
    "br", "p", "div", "tr", "li", "td", "th",
    "h1", "h2", "h3", "h4", "h5", "h6",
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_stack: list[bool] = []

    def _is_quote_marker(self, attrs: list[tuple[str, str | None]]) -> bool:
        for name, value in attrs:
            if name == "class" and value:
                lowered = value.lower()
                if any(marker in lowered for marker in _QUOTE_CLASS_MARKERS):
                    return True
        return False

    @property
    def _currently_skipping(self) -> bool:
        return bool(self._skip_stack) and self._skip_stack[-1]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_SEPARATOR_TAGS:
            self._chunks.append("\n")
        if tag in _VOID_TAGS:
            return
        should_skip = tag in _SKIP_TAGS or self._is_quote_marker(attrs)
        self._skip_stack.append(should_skip or self._currently_skipping)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_TAGS:
            return
        if self._skip_stack:
            self._skip_stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._currently_skipping:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def strip_html(text: str) -> str:
    """No-op on plain text; strips tags/scripts/styles/blockquoted history
    and decodes entities when the content looks like HTML."""
    if "<" not in text or ">" not in text:
        return text
    parser = _HTMLTextExtractor()
    parser.feed(text)
    return unescape(parser.get_text())


def remove_signature_and_disclaimers(text: str) -> str:
    lines = text.split("\n")
    cursor = 0
    cut_at: int | None = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        line_start = cursor
        cursor += len(line) + 1
        if line_start < _MIN_CHARS_BEFORE_SIGNATURE_CUT:
            continue
        if _SIGNATURE_LINE_RE.match(stripped):
            cut_at = idx
            break
    if cut_at is not None:
        lines = lines[:cut_at]

    result = "\n".join(lines)
    lowered = result.lower()
    for marker in _DISCLAIMER_MARKERS:
        pos = lowered.find(marker)
        if pos != -1:
            result = result[:pos]
            lowered = result.lower()
    return result


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(raw: str) -> str:
    """Full pipeline: strip_html -> strip_quoted_history -> remove
    signature/disclaimers -> normalize. Used for both offline Interaction
    content and the online incoming email body.
    """
    text = strip_html(raw)
    text = strip_quoted_history(text)
    text = remove_signature_and_disclaimers(text)
    text = normalize_whitespace(text)
    return text


class PreprocessedEmail:
    def __init__(self, subject: str, clean_body: str, sender_email: str):
        self.subject = subject
        self.clean_body = clean_body
        self.sender_email = sender_email

    @property
    def embedding_text(self) -> str:
        """What actually gets embedded: subject + cleaned body. Subject is
        included because short follow-ups ("any update?") carry almost no
        signal on their own -- the subject line is often the only place the
        topic is still named."""
        subject = self.subject.strip()
        if not subject:
            return self.clean_body
        return f"{subject}\n\n{self.clean_body}"


def preprocess_incoming_email(
    subject: str, body: str, sender_email: str
) -> PreprocessedEmail:
    return PreprocessedEmail(
        subject=subject.strip(),
        clean_body=clean_text(body),
        sender_email=sender_email.strip().lower(),
    )
