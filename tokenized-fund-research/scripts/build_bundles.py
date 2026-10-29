#!/usr/bin/env python3
"""Build the collector bundles and prompts for one research run.

  python3 -I build_bundles.py reports/.work/midas-mTBILL
  python3 -I build_bundles.py reports/.work/midas-mTBILL --collectors B,D
  python3 -I build_bundles.py reports/.work/midas-mTBILL --status   # are the collectors' notes complete?

Reads <work dir>/product.md. Its "Platform:" line selects the platform sources:
references/sources/<platform>.md when the skill has one, otherwise the draft that the
tokenization-platform-fetch skill writes next to the work dir, at
reports/.work/platform-<platform>/sources.md. With neither, nothing is built.
The SEC contact lives in <work dir>/.sec-user-agent, never in product.md (which is copied into
every bundle): an email on the SEC_USER_AGENT line is an error.
For each collector it writes:
  <work dir>/bundle-<L>.md   product.md + task + rules + sources (+ extra references), joined verbatim
  <work dir>/prompt-<L>.md   references/collectors/prompt.md with its placeholders filled in

The same inputs always give byte-identical outputs. The orchestrator passes prompt-<L>.md to the
collector unchanged. The resume paragraph is added automatically when <work dir>/<L>/ or
notes-<L>.md already holds content from an earlier attempt.

--status builds nothing. It reports, per collector, whether notes-<L>.md exists, how many sourced
facts (src: lines) it holds, and whether it ends with the closing Gaps / Conflicts / Leads lists
that references/collectors/rules.md requires. A collector is "complete" only with all three.

Exit code: 0 = built (or, with --status, all selected collectors complete), 1 = a required input
is missing or invalid (or a collector is not complete), 2 = bad arguments.
Standard library only; no network access.
"""

import argparse
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# letter -> (role, extra reference files appended after the sources)
COLLECTORS = {
    "A": ("Issuer docs & data", []),
    "B": ("Legal & regulatory", ["references/investor-frameworks.md", "references/roles.md"]),
    "C": ("GitHub & on-chain", []),
    "D": ("Governance forums & curators", ["references/forums.md"]),
}
TEMPLATE = "references/collectors/prompt.md"
RULES = "references/collectors/rules.md"
COMMON_SOURCES = "references/sources/common.md"
PLACEHOLDERS = {"LETTER", "ROLE", "BUNDLE", "LINES", "WORK_DIR", "SKILL_DIR", "RESUME"}
REQUIRED_PLACEHOLDERS = {"LETTER", "BUNDLE", "LINES", "WORK_DIR", "RESUME"}
RESUME_TEXT = (
    "This is a resumed run. An earlier attempt left files in {WORK_DIR}/{LETTER}/ and possibly "
    "notes in {WORK_DIR}/notes-{LETTER}.md. Read both before fetching anything. Keep the existing "
    "notes and append to them. Do not fetch a source again when its raw file is already there."
)
# product.md fields the collectors rely on; missing ones are warned about, not fatal
PRODUCT_FIELDS = ["Platform", "SEC_USER_AGENT", "PDF tooling", "Collector models"]
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
# not platform names ("n" = "n/a"); "common" is the shared sources file
PLATFORM_PLACEHOLDERS = {"other", "generic", "unknown", "none", "tbd", "n", "na", "common"}
DRAFT = os.path.join("platform-{platform}", "sources.md")   # tokenization-platform-fetch output, beside the work dir
UA_FILE = ".sec-user-agent"   # the SEC contact; edgar_search.py --user-agent-file reads it
CLOSING_LISTS = ("Gaps", "Conflicts", "Leads")   # rules.md: notes end with these three lists


class BuildError(Exception):
    pass


def read_text(path, label=None):
    """Read a UTF-8 file, normalise line endings, end with exactly one newline."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        raise BuildError(f"missing file: {label or path}")
    except (OSError, UnicodeDecodeError) as e:
        raise BuildError(f"cannot read {label or path}: {e}")
    text = text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return text + "\n" if text else ""


def field(product, name):
    """Value of a "Name: value" line in product.md (list bullets and bold markers allowed)."""
    m = re.search(r"(?mi)^\s*(?:[-*]\s+)?\**" + re.escape(name) + r"\**\s*:\s*\**\s*(.*?)\s*$", product)
    return m.group(1).strip("*` ") if m else None


def platform_slug(value):
    m = re.match(r"[a-z0-9][a-z0-9-]*", (value or "").strip().strip("*`").lower())
    return m.group(0) if m else None


def known_platforms():
    folder = os.path.join(SKILL_DIR, "references", "sources")
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return sorted(n[:-3] for n in names if n.endswith(".md") and n != "common.md")


def has_content(path):
    """True when a notes file has text, or a folder holds any non-hidden entry."""
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return bool(fh.read().strip())
        except OSError:
            return False
    if os.path.isdir(path):
        for _root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            if any(not f.startswith(".") for f in files):
                return True
    return False


def load_template():
    text = read_text(os.path.join(SKILL_DIR, TEMPLATE), TEMPLATE)
    found = set(PLACEHOLDER_RE.findall(text))
    unknown = found - PLACEHOLDERS
    if unknown:
        raise BuildError(f"{TEMPLATE}: unknown placeholder(s) {sorted(unknown)} "
                         f"(allowed: {sorted(PLACEHOLDERS)})")
    missing = REQUIRED_PLACEHOLDERS - found
    if missing:
        raise BuildError(f"{TEMPLATE}: required placeholder(s) missing {sorted(missing)}")
    if not re.search(r"(?m)^\{RESUME\}$", text):
        raise BuildError(f"{TEMPLATE}: {{RESUME}} must stand alone on its own line")
    return text


def fill(template, values):
    return PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template)


def build_bundle(letter, product_text, platform_part):
    """platform_part: (label, path) of the platform sources file."""
    role, extras = COLLECTORS[letter]
    parts = [("product.md", None, product_text),
             (f"references/collectors/{letter}.md", None, None),
             (RULES, None, None),
             (COMMON_SOURCES, None, None),
             (platform_part[0], platform_part[1], None)]
    parts.extend((e, None, None) for e in extras)
    loaded = []
    for label, path, text in parts:
        if text is None:
            text = read_text(path or os.path.join(SKILL_DIR, label), label)
            if not text:
                raise BuildError(f"empty reference file: {label}")
        loaded.append((label, text))
    header = (f"# Collector {letter} bundle — {role}\n\n"
              "Built by scripts/build_bundles.py. Do not edit this file; rebuild it.\n\n"
              "Parts, in order:\n" + "".join(f"- {label}\n" for label, _ in loaded))
    body = "".join(f"\n<!-- bundle part: {label} -->\n\n{text}" for label, text in loaded)
    return header + body


def platform_sources(work_dir, platform):
    """Return ((label, path), warnings) for the platform part of the bundles."""
    built_in = f"references/sources/{platform}.md"
    draft = os.path.join(os.path.dirname(os.path.abspath(work_dir)), DRAFT.format(platform=platform))
    draft_label = f"reports/.work/{DRAFT.format(platform=platform)} (draft by tokenization-platform-fetch)"
    if platform in known_platforms():
        warnings = []
        if os.path.isfile(draft):
            warnings.append(f"a draft exists at {draft}, but the bundles use {built_in}; install the "
                            "draft with tokenization-platform-fetch if it is the newer one")
        return (built_in, None), warnings
    if os.path.isfile(draft):
        return (draft_label, draft), []
    raise BuildError(f"no sources for platform '{platform}': no {built_in} (known: "
                     f"{', '.join(known_platforms())}) and no draft at {draft}; "
                     "run the tokenization-platform-fetch skill for it first")


def build(work_dir, collectors, platform_arg=None):
    """Build bundles and prompts. Returns (rows, warnings)."""
    warnings = []
    if not os.path.isdir(work_dir):
        raise BuildError(f"work dir not found: {work_dir} (create it and write product.md first)")
    product = read_text(os.path.join(work_dir, "product.md"), "product.md")
    if not product.strip():
        raise BuildError("product.md is empty")
    for name in PRODUCT_FIELDS:
        if not field(product, name):
            warnings.append(f"product.md has no '{name}:' line")
    if not re.search(r"(?mi)^#+\s*Focus notes\s*$", product):
        warnings.append("product.md has no '## Focus notes' section")
    sec = (field(product, "SEC_USER_AGENT") or "").lower()
    if "@" in sec:
        raise BuildError(f"product.md SEC_USER_AGENT holds the contact itself; move it to "
                         f"<work dir>/{UA_FILE} and write 'SEC_USER_AGENT: set' (bundles copy product.md)")
    if re.match(r"set\b", sec) and not has_content(os.path.join(work_dir, UA_FILE)):
        warnings.append(f"SEC_USER_AGENT is 'set' but <work dir>/{UA_FILE} is missing or empty; "
                        "collector B cannot query EDGAR")

    from_file = platform_slug(field(product, "Platform"))
    from_arg = platform_slug(platform_arg) if platform_arg else None
    if platform_arg and not from_arg:
        raise BuildError(f"invalid --platform '{platform_arg}'")
    if from_arg and from_file and from_arg != from_file:
        raise BuildError(f"--platform {from_arg} contradicts product.md Platform: {from_file}")
    platform = from_arg or from_file
    if not platform:
        raise BuildError("no platform: add a 'Platform:' line to product.md or pass --platform")
    if platform in PLATFORM_PLACEHOLDERS:
        raise BuildError(f"Platform: '{platform}' is not a platform name; write the platform's own "
                         "name in lowercase (it names the report file), e.g. 'franklin'")
    platform_part, more = platform_sources(work_dir, platform)
    warnings.extend(more)

    template = load_template()
    # absolute, so a collector finds its files whatever directory its session starts in
    work_label = os.path.abspath(work_dir)
    rows = []
    for letter in collectors:
        bundle = build_bundle(letter, product, platform_part)
        bundle_path = os.path.join(work_label, f"bundle-{letter}.md")
        resumed = (has_content(os.path.join(work_dir, letter))
                   or has_content(os.path.join(work_dir, f"notes-{letter}.md")))
        values = {
            "LETTER": letter,
            "ROLE": COLLECTORS[letter][0],
            "BUNDLE": bundle_path,
            "LINES": str(bundle.count("\n")),
            "WORK_DIR": work_label,
            "SKILL_DIR": SKILL_DIR,
        }
        values["RESUME"] = fill(RESUME_TEXT, values) if resumed else ""
        prompt = fill(template, values)
        prompt = re.sub(r"\n{3,}", "\n\n", prompt)   # an empty {RESUME} line leaves a gap
        for path, text in ((bundle_path, bundle), (os.path.join(work_label, f"prompt-{letter}.md"), prompt)):
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
            except OSError as e:
                raise BuildError(f"cannot write {path}: {e}")
        rows.append({"letter": letter, "role": COLLECTORS[letter][0], "bundle": bundle_path,
                     "lines": bundle.count("\n"),
                     "prompt": os.path.join(work_label, f"prompt-{letter}.md"), "resumed": resumed})
    return rows, warnings


def count_files(path):
    total = 0
    for _root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        total += sum(1 for f in files if not f.startswith("."))
    return total


def notes_status(work_dir, letter):
    """State of one collector's notes: missing / incomplete / complete."""
    path = os.path.join(work_dir, f"notes-{letter}.md")
    raw = count_files(os.path.join(work_dir, letter))
    if not os.path.isfile(path):
        return {"letter": letter, "state": "missing", "facts": 0, "lists": [], "raw": raw}
    text = read_text(path, f"notes-{letter}.md")
    facts = len(re.findall(r"(?m)^\s*src:", text))
    # a list heading may be "## Gaps", "**Gaps**", "Gaps:", "1. Gaps", "- Leads for B"
    lists = [name for name in CLOSING_LISTS
             if re.search(r"(?mi)^\s*(?:#+\s*|\d+\.\s*|[-*]\s+)?\**\s*" + name + r"\b", text)]
    state = "complete" if len(lists) == len(CLOSING_LISTS) else "incomplete"
    return {"letter": letter, "state": state, "facts": facts, "lists": lists, "raw": raw}


def status(work_dir, collectors):
    if not os.path.isdir(work_dir):
        raise BuildError(f"work dir not found: {work_dir}")
    return [notes_status(work_dir, letter) for letter in collectors]


def parse_collectors(value):
    letters = [c.strip().upper() for c in (value or "").split(",") if c.strip()]
    if not letters:
        raise ValueError("empty --collectors list")
    bad = [c for c in letters if c not in COLLECTORS]
    if bad:
        raise ValueError(f"unknown collector(s) {bad} (known: {', '.join(COLLECTORS)})")
    return [c for c in COLLECTORS if c in letters]   # canonical order, de-duplicated


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build collector bundles and prompts for one run.")
    ap.add_argument("work_dir", help="the run's work dir, e.g. reports/.work/midas-mTBILL")
    ap.add_argument("--collectors", default=",".join(COLLECTORS), help="comma list (default: A,B,C,D)")
    ap.add_argument("--platform", help="override / confirm product.md's Platform line")
    ap.add_argument("--status", action="store_true",
                    help="build nothing; report whether each collector's notes are complete")
    args = ap.parse_args(argv)
    try:
        collectors = parse_collectors(args.collectors)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.status:
        try:
            rows = status(args.work_dir, collectors)
        except BuildError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        for r in rows:
            missing = [n for n in CLOSING_LISTS if n not in r["lists"]]
            detail = f"  missing lists: {', '.join(missing)}" if r["state"] == "incomplete" else ""
            print(f"{r['letter']}  {COLLECTORS[r['letter']][0]:<30} {r['state']:<10} "
                  f"{r['facts']:>4} facts  {r['raw']:>4} raw files{detail}")
        done = sum(r["state"] == "complete" for r in rows)
        print(f"{done}/{len(rows)} complete")
        return 0 if done == len(rows) else 1
    try:
        rows, warnings = build(args.work_dir, collectors, args.platform)
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for r in rows:
        print(f"{r['letter']}  {r['role']:<30} {r['bundle']} ({r['lines']} lines)  "
              f"{r['prompt']}{'  [resume]' if r['resumed'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
