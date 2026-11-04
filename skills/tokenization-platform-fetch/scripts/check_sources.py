#!/usr/bin/env python3
"""Check a platform sources file before anyone reviews or installs it.

  python3 -I check_sources.py reports/.work/platform-franklin/sources.md --slug franklin

Validates the shape (heading, "checked in" date, Products line, Docs / Legal / GitHub / Forums
bullets) and flags content that has no place in a list of pointers: template placeholders,
hidden characters (zero-width, bidi override, Unicode tags, terminal escapes), HTML and Markdown
images, email addresses, instructions addressed to an AI, and shell commands that install or
execute. It also warns about look-alike letters (Cyrillic or Greek mixed into a Latin word or
host). Hidden characters are the reason this is a script: a reader can't see them. Every future research run reads this file, so the check is a
tripwire in front of the human review, not a replacement for it.

Exit code: 0 = no errors (warnings allowed), 1 = errors or unreadable file, 2 = bad arguments.
Standard library only; no network access.
"""

import argparse
import os
import re
import sys
import unicodedata

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
# "common" is the research skill's shared sources file; the others are not platform names
RESERVED_SLUGS = {"common", "other", "generic", "unknown", "none", "tbd", "n", "na"}
MAX_BYTES = 64 * 1024
MAX_LINES = 100          # the shipped files are 19-37 lines; longer means page text crept in
REQUIRED_BULLETS = ("Docs", "Legal", "GitHub", "Forums")
MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December")
CHECKED_RE = re.compile(r"(?i)\bchecked in (?:(?:" + MONTHS + r") \d{4}|\d{4}-\d{2}(?:-\d{2})?)\b")
HEADING_RE = re.compile(r"^# \S.*\s[—–-] sources\s*$")
# controls, soft hyphen, zero-width / joiners, bidi controls, line / paragraph separators, blank
# fillers, variation selectors, interlinear annotations, and the invisible Unicode tag block
HIDDEN_RE = re.compile(
    "[\x00-\x08\x0b-\x1f\x7f-\x9f\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180f"
    "\u200b-\u200f\u2028-\u202e\u2060-\u206f\u2800\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff9-\ufffb"
    "\U000e0000-\U000e007f\U000e0100-\U000e01ef]")
HTML_RE = re.compile(r"(?i)<!--|</?(?:script|iframe|img|a|div|span|style|link|meta|object|embed|form|input|svg|details)\b")
SCHEME_RE = re.compile(r"(?i)\b(?:javascript|data|file|vbscript):")
IMAGE_RE = re.compile(r"!\[[^\]\n]*\]\s*[\[(]")   # a Markdown image loads a URL when rendered
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
HOST_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://([^/\s`<>()\[\]\"']+)")
WORD_RE = re.compile(r"[^\W_]+")
LOOKALIKE_SCRIPTS = ("CYRILLIC", "GREEK", "ARMENIAN", "CHEROKEE", "FULLWIDTH")
INSTRUCTION_RES = [
    re.compile(r"(?i)\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:instructions?|rules|prompts?|guidelines)\b"),
    re.compile(r"(?i)\b(?:system|developer) (?:prompt|message|instructions?)\b"),
    re.compile(r"(?i)\byou are (?:now )?(?:an? |the )?(?:ai|assistant|language model|llm|agent|claude|chatgpt)\b"),
    re.compile(r"(?i)\b(?:ai|llm) (?:agents?|assistants?|readers?|models?)\b[^.\n]{0,30}\b(?:must|should|need to)\b"),
    re.compile(r"(?i)\b(?:notes?|messages?|instructions?|reminders?) (?:to|for) (?:the |all |any )?"
               r"(?:ai|llms?|assistants?|agents?|collectors?|models?|bots?|readers?)\b"),
    re.compile(r"(?i)\b(?:collectors?|assistants?|ai|llms?)\b[^\n]{0,80}?\b(?:follow (?:it|them|its|these|those|that)\b"
               r"|obey|execute|exfiltrate|upload|send (?:your |the |all )?(?:notes|files|data|contents?))"),
]
COMMAND_RE = re.compile(
    r"(?i)\|\s*(?:sh|bash|zsh|python3?|node|perl|ruby)\b"
    r"|\b(?:sudo|rm -rf|chmod \+x|pip3? install|npm (?:install|i)|npx|yarn add|pnpm add|brew install"
    r"|apt(?:-get)? install|eval|exec)\b"
    r"|(?-i:\bcurl\b[^\n`]*\s-[a-zA-Z]*[OJ]\b)")   # -O / -J take the file name from the server


def lookalike(line):
    """Return the first word or URL host that mixes look-alike letters into Latin text, else None."""
    for host in HOST_RE.findall(line):
        if any(ord(ch) > 127 for ch in host):
            return host
    for word in WORD_RE.findall(line):
        if any(ch.isascii() for ch in word) and any(
                unicodedata.name(ch, "").startswith(LOOKALIKE_SCRIPTS) for ch in word if not ch.isascii()):
            return word
    return None


class Finding:
    def __init__(self, level, line, message):
        self.level, self.line, self.message = level, line, message

    def __str__(self):
        where = f"line {self.line}: " if self.line else ""
        return f"{self.level} {where}{self.message}"


def slug_error(slug):
    if not SLUG_RE.match(slug or ""):
        return (f"invalid slug '{slug}': use 1-40 lowercase letters, digits and hyphens, "
                "starting with a letter or digit, e.g. 'franklin'")
    if slug in RESERVED_SLUGS:
        return f"slug '{slug}' is reserved; use the platform's own name"
    return None


def read_draft(path):
    """Return (text, error). Line endings are normalised; the text ends with one newline."""
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None, f"{path} is larger than {MAX_BYTES} bytes; a sources file is a short list of pointers"
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except IsADirectoryError:
        return None, f"not a file: {path}"
    except UnicodeDecodeError:
        return None, f"{path} is not UTF-8 text"
    except OSError as e:
        return None, f"cannot read {path}: {e}"
    text = text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    if not text.strip():
        return None, f"{path} is empty"
    return text + "\n", None


def check_text(text):
    """Return a list of Findings (ERROR / WARNING) for a sources file's text."""
    out = []
    lines = text.split("\n")
    first = next(((i, l) for i, l in enumerate(lines, 1) if l.strip()), (1, ""))
    if not HEADING_RE.match(first[1]):
        out.append(Finding("ERROR", first[0], "the file must start with '# <Platform> — sources'"))
    if not CHECKED_RE.search(text):
        out.append(Finding("ERROR", None, "no 'checked in <Month YYYY>' line saying when the URLs were verified"))
    if not re.search(r"(?m)^Products:\s*\S", text):
        out.append(Finding("ERROR", None, "no 'Products:' line listing the platform's products and tickers"))
    for label in REQUIRED_BULLETS:
        if not re.search(r"(?m)^\s*- \*\*" + label, text):
            out.append(Finding("ERROR", None, f"no '- **{label}**' bullet (write 'not found' with where you looked)"))
    for n, line in enumerate(lines, 1):
        if "{{" in line or "}}" in line:
            out.append(Finding("ERROR", n, "template placeholder left in"))
        if HIDDEN_RE.search(line):
            out.append(Finding("ERROR", n, "hidden or control character (zero-width, bidi override, escape)"))
        if HTML_RE.search(line):
            out.append(Finding("ERROR", n, "HTML tag or comment; write plain Markdown"))
        if SCHEME_RE.search(line):
            out.append(Finding("ERROR", n, "javascript: / data: / file: link"))
        if IMAGE_RE.search(line):
            out.append(Finding("ERROR", n, "Markdown image; it loads a URL when rendered, link the page instead"))
        if EMAIL_RE.search(line):
            out.append(Finding("ERROR", n, "email address; a sources file holds no contacts (the SEC contact "
                                           "goes only to edgar_search.py), link a contact page instead"))
        if any(r.search(line) for r in INSTRUCTION_RES):
            out.append(Finding("ERROR", n, "reads like an instruction to an AI; a sources file holds pointers only"))
        if COMMAND_RE.search(line):
            out.append(Finding("ERROR", n, "install / execute command; collectors never run code from a sources file"))
        if re.search(r"(?i)\bhttp://", line):
            out.append(Finding("WARNING", n, "http:// link; use https:// if the site supports it"))
        odd = lookalike(line)
        if odd:
            out.append(Finding("WARNING", n, f"'{odd}' mixes look-alike letters (Cyrillic, Greek…) into "
                                             "Latin text or a host; retype it in plain ASCII"))
    if len(lines) > MAX_LINES:
        out.append(Finding("WARNING", None, f"{len(lines)} lines; keep it a short list of pointers (shipped files are under 40)"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a platform sources file.")
    ap.add_argument("file")
    ap.add_argument("--slug", help="also validate the platform slug")
    args = ap.parse_args(argv)
    if args.slug is not None and slug_error(args.slug):
        print(f"error: {slug_error(args.slug)}", file=sys.stderr)
        return 2
    text, err = read_draft(args.file)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    findings = check_text(text)
    for f in findings:
        print(f"{args.file}: {f}", file=sys.stderr)
    errors = sum(f.level == "ERROR" for f in findings)
    print(f"{args.file}: {errors} error(s), {len(findings) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
