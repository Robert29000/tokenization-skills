#!/usr/bin/env python3
"""Validate tokenized-fund reports against the fixed template and diff their structure.

Usage:
  python3 -I check_report.py REPORT.md                 # validate one report
  python3 -I check_report.py A.md B.md [C.md ...]      # validate each + structural diff
  python3 -I check_report.py --template TEMPLATE.md    # validate the template skeleton itself
  python3 -I check_report.py --renumber REPORT.md      # renumber [n] by first appearance

Options:
  --json      machine-readable output
  --strict    treat warnings as errors

Exit code: 0 = all reports valid (and structurally identical when several are given),
1 = validation errors or structural differences, 2 = usage / file errors.
Standard library only; no network access.
"""

import argparse
import json
import re
import sys

# ---------------------------------------------------------------------------
# Canonical structure. references/report-template.md must mirror this exactly
# (tests/tokenized-fund-research/test_check_report.py at the repo root enforces that).
# ---------------------------------------------------------------------------

SECTIONS = [
    (2, "1. Intro"),
    (2, "2. Underlying Assets"),
    (3, "2.1 Mandate & Eligible Assets"),
    (3, "2.2 Portfolio Composition"),
    (3, "2.3 Leverage, Repo & Rehypothecation"),
    (3, "2.4 Liquidity of the Underlying"),
    (2, "3. Key Roles & Legal Entities"),
    (3, "3.1 Universal Roles"),
    (3, "3.2 Product-Specific Roles"),
    (3, "3.3 Entity Responsibilities"),
    (2, "4. Who Can Invest"),
    (3, "4.1 Primary Market Eligibility"),
    (3, "4.2 Secondary Market"),
    (2, "5. Investor Ownership & Rights"),
    (3, "5.1 What the Investor Owns"),
    (3, "5.2 Claim Chain"),
    (3, "5.3 Bankruptcy Remoteness & Recourse"),
    (3, "5.4 Investor Rights"),
    (3, "5.5 Issuer Powers Limiting Investor Rights"),
    (2, "6. Tokenized Fund's Obligations to Investors"),
    (3, "6.1 Governing Law & Jurisdiction"),
    (3, "6.2 Regulators & Supervisory Bodies"),
    (3, "6.3 Obligations by Investor Type"),
    (3, "6.4 Investor Remedies"),
    (2, "Appendix A. Open Questions & Conflicting Information"),
    (2, "Appendix B. Sources"),
]
SOURCES_SECTION = "Appendix B. Sources"

HEADER_FIELDS = ["Platform", "Ticker", "Token type", "Chains", "Report date", "Data freshness"]

UNIVERSAL_ROLES = [
    "Sponsor / Tokenization Platform",
    "Issuer",
    "Underlying Fund",
    "Investment Manager / Adviser",
    "Sub-Adviser",
    "Board / Directors / Trustee",
    "Fund Administrator / NAV Calculation Agent",
    "Transfer Agent / Registrar",
    "Custodian (Underlying Assets)",
    "Token Custody / Key Management",
    "Distributor / Placement Agent / Broker-Dealer",
    "Auditor",
    "Legal Counsel",
    "NAV Oracle / Pricing Provider",
    "KYC / AML Provider",
]

SECONDARY_ROWS = [
    "Transfer Restrictions",
    "Allowlist Enforcement",
    "Eligible Venues",
    "Lock-up / Holding Period",
    "Secondary Buyer Eligibility",
]

RIGHTS_ROWS = [
    "Voting",
    "Redemption",
    "Distributions / Income",
    "Information & Reporting",
    "Transfer",
    "Claim on Assets in Insolvency",
]

POWER_ROWS = [
    "Compulsory Redemption",
    "Suspension of Redemptions / NAV",
    "Gating / Redemption Limits",
    "Haircut / Write-down",
    "Token Freeze / Seizure / Burn",
    "Contract Upgrade / Pause",
    "Unilateral Amendment of Terms",
]

OBLIGATION_ROWS = [
    "Redemption & Settlement",
    "NAV Calculation & Publication",
    "Periodic Reporting",
    "Audited Financial Statements",
    "Disclosure of Material Changes",
    "Offering / Investor Protection Documents",
    "Complaints & Dispute Resolution",
]

# section title -> table spec
#   columns:      exact header cells
#   fixed_rows:   first-column values that must appear first, in this order
#   extras:       rows beyond fixed_rows allowed (product-specific)
#   min_rows:     minimum data rows when fixed_rows is None
#   optional:     the table may be replaced by "N/A – reason" for the whole section
#   note:         a "> **Note:**" blockquote must precede the table
TABLES = {
    "2.2 Portfolio Composition": dict(
        columns=["Asset Class", "Allocation (% of NAV)", "Notes", "Source"],
        fixed_rows=None, extras=True, min_rows=1, optional=True, note=False),
    "3.1 Universal Roles": dict(
        columns=["Role", "Entity", "Legal Form & Jurisdiction", "Regulator / Licence",
                 "Independence from Sponsor", "Source"],
        fixed_rows=UNIVERSAL_ROLES, extras=False, min_rows=0, optional=False, note=False),
    "3.2 Product-Specific Roles": dict(
        columns=["Role", "Entity", "Legal Form & Jurisdiction", "Regulator / Licence",
                 "Why This Role Exists", "Source"],
        fixed_rows=None, extras=True, min_rows=1, optional=True, note=True),
    "4.1 Primary Market Eligibility": dict(
        columns=["Investor Type", "Legal Qualification", "Jurisdiction (Allowed / Excluded)",
                 "Financial Requirements & Minimum", "Onboarding / KYC", "Source"],
        fixed_rows=None, extras=True, min_rows=1, optional=False, note=False),
    "4.2 Secondary Market": dict(
        columns=["Aspect", "Detail", "Source"],
        fixed_rows=SECONDARY_ROWS, extras=True, min_rows=0, optional=False, note=False),
    "5.4 Investor Rights": dict(
        columns=["Right", "Held by Investor?", "Detail", "Source"],
        fixed_rows=RIGHTS_ROWS, extras=True, min_rows=0, optional=False, note=False),
    "5.5 Issuer Powers Limiting Investor Rights": dict(
        columns=["Power", "Held By", "Detail", "Exercised to Date?", "Source"],
        fixed_rows=POWER_ROWS, extras=True, min_rows=0, optional=False, note=False),
    "6.1 Governing Law & Jurisdiction": dict(
        columns=["Document", "Governing Law", "Courts / Forum", "Source"],
        fixed_rows=None, extras=True, min_rows=1, optional=False, note=False),
    "6.2 Regulators & Supervisory Bodies": dict(
        columns=["Regulator / Body", "Jurisdiction", "Scope of Oversight",
                 "Relevance to Investor", "Source"],
        fixed_rows=None, extras=True, min_rows=1, optional=False, note=False),
    "6.3 Obligations by Investor Type": dict(
        columns=["Obligation", "Owed By", "Investor Type(s)", "Detail", "Source"],
        fixed_rows=OBLIGATION_ROWS, extras=True, min_rows=0, optional=False, note=False),
}

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NA_RE = re.compile(r"^N/A\s*[–—-]\s*\S")
BARE_NA_RE = re.compile(r"^(N/A|n/a|NA|-|–|—|TBD|\?)\.?$")
ALIGN_CELL_RE = re.compile(r"^:?-{3,}:?$")
PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")
# [3]  [3, 7]  [2-4]  [2–4, 9]  — but not markdown links [3](url) or task boxes
CITE_RE = re.compile(r"\[(\s*\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*\s*)\](?!\()")
SOURCE_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$")
DASH_CELLS = ("—", "-", "–")
EXERCISED_RE = re.compile(r"^(Yes|No|Partially|Unknown|N/A|Not disclosed)\b", re.I)
# sections whose Entity column must each get an H4 in 3.3
ENTITY_TABLES = ("3.1 Universal Roles", "3.2 Product-Specific Roles")
RESPONSIBILITIES_SECTION = "3.3 Entity Responsibilities"
# tables whose rows are legal claims (references/claim-check.md); a row backed only by [S]
# sources must say who says it
LEGAL_TABLES = ("3.1 Universal Roles", "3.2 Product-Specific Roles", "4.1 Primary Market Eligibility",
                "5.4 Investor Rights", "5.5 Issuer Powers Limiting Investor Rights",
                "6.1 Governing Law & Jurisdiction", "6.2 Regulators & Supervisory Bodies",
                "6.3 Obligations by Investor Type")
TIER_RE = re.compile(r"^\[(P|S)\]\s")
ATTRIBUTION_RE = re.compile(r"\b(per|according to|reported by|reports?|states?|stated|considers?|"
                            r"lists?|listed|claims?|says|describes?|described)\b", re.I)
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def norm(text):
    """Normalise a heading / cell for comparison: drop emphasis markers, collapse spaces."""
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def split_row(line):
    """Split a markdown table row on unescaped pipes, dropping the outer pipes."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def is_align_row(line):
    cells = split_row(line)
    return bool(cells) and all(ALIGN_CELL_RE.match(c.replace(" ", "")) for c in cells)


def strip_code(lines):
    """Return lines with fenced code blocks and inline code removed (for citation scans)."""
    out, fenced = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else re.sub(r"`[^`]*`", "", line))
    return out


class Section:
    def __init__(self, level, title, line_no):
        self.level = level
        self.title = title
        self.line_no = line_no
        self.lines = []  # body lines up to the next H1-H3 heading

    def body(self):
        return [l for l in self.lines if l.strip()]


def parse_sections(text):
    """Split the document into a preamble and H2/H3 sections (H4+ stays in the body)."""
    preamble, sections, fenced = [], [], False
    for no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else HEADING_RE.match(line)
        if m and len(m.group(1)) in (2, 3):
            sections.append(Section(len(m.group(1)), norm(m.group(2)), no))
            continue
        (sections[-1].lines if sections else preamble).append(line)
    return preamble, sections


def find_tables(lines):
    """Yield (header, rows, start_index) for each markdown table in lines."""
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        if "|" in line and is_align_row(lines[i + 1]) and not is_align_row(line):
            header = split_row(line)
            rows, j = [], i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                rows.append(split_row(lines[j]))
                j += 1
            yield header, rows, i
            i = j
        else:
            i += 1


def _is_year(n):
    return 1900 <= n <= 2100


def parse_citations(text):
    """Return cited source numbers. Bracketed years like [2026] or [2020-2024] are not citations."""
    nums = set()
    for m in CITE_RE.finditer(text):
        for part in m.group(1).split(","):
            part = part.strip()
            if re.search(r"[-–]", part):
                a, b = (int(x) for x in re.split(r"\s*[-–]\s*", part))
                if _is_year(a) and _is_year(b):
                    continue
                if a > b:
                    raise ValueError(f"reversed citation range [{part}]")
                if b - a > 50:
                    raise ValueError(f"implausibly wide citation range [{part}]")
                nums.update(range(a, b + 1))
            else:
                n = int(part)
                if len(part) == 4 and _is_year(n):
                    continue
                nums.add(n)
    return nums


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class Result:
    def __init__(self, path):
        self.path = path
        self.errors = []
        self.warnings = []
        self.signature = {}
        self.entities = []   # Entity cells from 3.1 / 3.2
        self.legal_rows = [] # (table, row label, cited numbers, row text without Source, N/A row?)

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def section_is_na(section):
    body = section.body()
    return bool(body) and NA_RE.match(norm(body[0]))


def check_table(res, section, spec):
    title = section.title
    tables = list(find_tables(section.lines))
    if not tables:
        if spec["optional"] and section_is_na(section):
            res.signature.setdefault("tables", {})[title] = None
            return
        res.err(f"[{title}] required table is missing"
                + (" (or replace the whole section with 'N/A – reason')" if spec["optional"] else ""))
        return
    if len(tables) > 1:
        res.warn(f"[{title}] {len(tables)} tables found; only the first is checked")
    header, rows, start = tables[0]
    header_n = [norm(c) for c in header]
    res.signature.setdefault("tables", {})[title] = header_n
    if header_n != spec["columns"]:
        res.err(f"[{title}] table columns {header_n} != expected {spec['columns']}")

    if spec["note"]:
        before = [norm(l) for l in section.lines[:start] if l.strip()]
        if not any(l.startswith("> Note:") for l in before):
            res.err(f"[{title}] table must be preceded by a '> **Note:**' line explaining "
                    "why these roles exist for this product")

    first_col = []
    for r_no, row in enumerate(rows, 1):
        if len(row) != len(header):
            res.err(f"[{title}] row {r_no} has {len(row)} cells, header has {len(header)}")
            continue
        first_col.append(norm(row[0]))
        if title in LEGAL_TABLES and "Source" in header_n:
            src_idx = header_n.index("Source")
            try:
                cited_here = parse_citations(norm(row[src_idx]))
            except ValueError:
                cited_here = set()
            text = " ".join(norm(c) for i, c in enumerate(row) if i != src_idx)
            row_na = len(row) > 1 and bool(NA_RE.match(norm(row[1])))
            res.legal_rows.append((title, norm(row[0]), cited_here, text, row_na))
        # an "N/A row": its first data cell gives the reason, so the other cells may be "—"
        na_row = len(row) > 1 and bool(NA_RE.match(norm(row[1])))
        # rows that are N/A, or whose facts are "Not disclosed", have nothing to cite
        has_na = any(NA_RE.match(norm(c)) or norm(c).lower().startswith("not disclosed")
                     for c in row[1:])
        for col, cell in zip(header_n, row):
            cell_n = norm(cell)
            if col == "Source":
                if PLACEHOLDER_RE.search(cell_n):
                    continue
                if cell_n in DASH_CELLS:
                    if not has_na:
                        res.warn(f"[{title}] row '{norm(row[0])}': Source is '—' but the row is "
                                 "not N/A — cite a source")
                    continue
                if not cell_n:
                    res.err(f"[{title}] row '{norm(row[0])}': empty Source cell (use [n] or —)")
                elif not CITE_RE.search(cell_n):
                    res.warn(f"[{title}] row '{norm(row[0])}': Source cell has no [n] citation")
                continue
            if na_row and cell_n in DASH_CELLS:
                continue
            if col == "Exercised to Date?" and cell_n and not PLACEHOLDER_RE.search(cell_n) \
                    and not EXERCISED_RE.match(cell_n):
                res.warn(f"[{title}] row '{norm(row[0])}': 'Exercised to Date?' should start with "
                         "Yes / No / Partially / Unknown / N/A")
            if not cell_n:
                res.err(f"[{title}] row '{norm(row[0])}': empty '{col}' cell")
            elif BARE_NA_RE.match(cell_n):
                res.err(f"[{title}] row '{norm(row[0])}': '{col}' is '{cell_n}' — write "
                        "'N/A – reason' or 'Not disclosed in public documents'")
            elif PLACEHOLDER_RE.search(cell_n):
                pass  # reported once globally

    fixed = spec["fixed_rows"]
    if fixed is not None:
        head = first_col[:len(fixed)]
        if head != fixed:
            missing = [r for r in fixed if r not in first_col]
            if missing:
                res.err(f"[{title}] missing fixed rows: {missing}")
            else:
                res.err(f"[{title}] fixed rows out of order: got {head}, expected {fixed}")
        extras = first_col[len(fixed):]
        if extras and not spec["extras"]:
            res.err(f"[{title}] rows not allowed in this table: {extras} "
                    "(product-specific roles go in 3.2)")
        res.signature.setdefault("fixed_rows", {})[title] = head
        res.signature.setdefault("extra_rows", {})[title] = extras
    else:
        if len(first_col) < spec["min_rows"]:
            res.err(f"[{title}] table needs at least {spec['min_rows']} data row(s)")
        res.signature.setdefault("extra_rows", {})[title] = first_col
    if title in ENTITY_TABLES and "Entity" in header_n:
        idx = header_n.index("Entity")
        res.entities.extend(norm(r[idx]) for r in rows if len(r) == len(header))


# legal-form suffixes and filler words ignored when matching entity names to 3.3 headings
GENERIC_WORDS = {"the", "and", "inc", "llc", "llp", "ltd", "limited", "plc", "gmbh", "corp",
                 "corporation", "company", "sarl", "s.a", "n.a", "group"}


def entity_names(cell):
    """Split an Entity cell into entity names (skip N/A, not disclosed, prose and placeholders)."""
    if not cell or NA_RE.match(cell) or cell.lower().startswith("not disclosed") or cell in DASH_CELLS:
        return []
    text = re.sub(r"\[[\d,\s\-–]+\]", "", cell)              # drop citations
    text = re.sub(r"\b0x[0-9a-fA-F]{6,}\b", "", text)         # drop addresses
    prev = None
    while prev != text:                                       # drop (nested) parentheticals
        prev, text = text, re.sub(r"\([^()]*\)", "", text)
    names = []
    for part in re.split(r";|<br>", text):
        part = re.split(r'\s+(?:and|via)\s+|"', part)[0]       # "X via Y", 'X "feed"'
        part = re.sub(r"\s+", " ", part).strip(" .,")
        if len(part) >= 3 and part[0].isupper():               # lowercase start = prose
            names.append(part)
    return names


def _key_words(name):
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z&'.-]*[A-Za-z]", name)]
    return [w for w in words if w not in GENERIC_WORDS and len(w) >= 3] or words


def check_responsibilities(res, sections):
    """Every entity named in 3.1 / 3.2 needs an H4 in 3.3 (a warning: names may be abbreviated)."""
    sec = next((s for s in sections if s.title == RESPONSIBILITIES_SECTION), None)
    if sec is None:
        return
    # full H4 text ("<entity> — <roles>"); entity names may themselves contain dashes
    h4s = [norm(m.group(2)).lower() for l in sec.lines
           for m in [HEADING_RE.match(l)] if m and len(m.group(1)) == 4]
    if not h4s and not section_is_na(sec):
        res.err(f"[{RESPONSIBILITIES_SECTION}] no H4 per entity found")
        return
    missing = []
    for cell in dict.fromkeys(res.entities):
        for name in entity_names(cell):
            keys = _key_words(name)
            covered = any(name.lower() in h or (keys and all(re.search(r"\b" + re.escape(k) + r"\b", h)
                                                               for k in keys)) for h in h4s)
            if not covered and name not in missing:
                missing.append(name)
    for name in missing:
        res.warn(f"[{RESPONSIBILITIES_SECTION}] no '#### {name} — …' heading for an entity named "
                 "in 3.1/3.2")


def validate(path, text, is_template=False):
    res = Result(path)
    preamble, sections = parse_sections(text)

    # --- header
    if not any(HEADING_RE.match(l) and l.startswith("# ") for l in preamble):
        res.err("missing H1 title before the first section")
    header_text = "\n".join(preamble)
    for field in HEADER_FIELDS:
        if not re.search(r"\*\*" + re.escape(field) + r":\*\*\s*\S", header_text):
            res.err(f"header field '**{field}:**' missing or empty")
    if not is_template:
        m = re.search(r"\*\*Report date:\*\*\s*(\S+)", header_text)
        if m and not DATE_RE.fullmatch(m.group(1)):
            res.err(f"Report date '{m.group(1)}' is not YYYY-MM-DD")

    # --- headings: exact set, exact order
    expected = [(lvl, t) for lvl, t in SECTIONS]
    actual = [(s.level, s.title) for s in sections]
    res.signature["headings"] = [f"{'#' * l} {t}" for l, t in actual]
    exp_titles = {t for _, t in expected}
    for s in sections:
        if (s.level, s.title) in expected:
            continue
        near = [t for t in exp_titles if s.title.startswith(t) or t.startswith(s.title)]
        if s.title in exp_titles:
            res.err(f"line {s.line_no}: heading '{s.title}' has wrong level H{s.level}")
        elif near:
            res.err(f"line {s.line_no}: heading '{s.title}' does not match fixed heading "
                    f"'{near[0]}' exactly (no renaming or extra text; use H4 for sub-topics)")
        else:
            res.err(f"line {s.line_no}: unexpected H{s.level} heading '{s.title}' "
                    "(product-specific sub-topics must use H4)")
    present = [a for a in actual if a in expected]
    for e in expected:
        if e not in actual:
            res.err(f"missing section: {'#' * e[0]} {e[1]}")
    seen = set()
    for a in present:
        if a in seen:
            res.err(f"duplicate section: {a[1]}")
        seen.add(a)
    order = [e for e in expected if e in present]
    if [a for a in dict.fromkeys(present)] != order:
        res.err("sections are out of order; expected order: "
                + " → ".join(t.split(" ")[0] for _, t in expected))

    # --- section bodies
    by_title = {}
    for i, s in enumerate(sections):
        by_title.setdefault(s.title, s)
        has_children = i + 1 < len(sections) and sections[i + 1].level > s.level
        body = s.body()
        if not body and not has_children:
            res.err(f"[{s.title}] section is empty (write content or 'N/A – reason')")
        elif body and BARE_NA_RE.match(norm(body[0])) and len(body) == 1:
            res.err(f"[{s.title}] bare '{norm(body[0])}' — write 'N/A – reason'")

    for title, spec in TABLES.items():
        if title in by_title:
            check_table(res, by_title[title], spec)

    if is_template:
        return res

    check_responsibilities(res, sections)

    # --- placeholders
    for no, line in enumerate(text.splitlines(), 1):
        if PLACEHOLDER_RE.search(line):
            res.err(f"line {no}: unfilled placeholder {PLACEHOLDER_RE.search(line).group(0)}")

    # --- citations vs sources
    src = by_title.get(SOURCES_SECTION)
    sources = {}
    if src:
        for line in src.lines:
            m = SOURCE_ITEM_RE.match(line)
            if not m:
                continue
            n = int(m.group(1))
            if n in sources:
                res.err(f"[Sources] duplicate source number {n}")
            sources[n] = m.group(2)
            if not DATE_RE.search(m.group(2)):
                res.warn(f"[Sources] entry {n} has no access date (YYYY-MM-DD)")
            if not TIER_RE.match(m.group(2)):
                res.warn(f"[Sources] entry {n} has no [P] / [S] tier tag (references/claim-check.md)")
        if not sources:
            res.err("[Sources] no numbered source entries found")

    body_lines = []
    for s in sections:
        if s.title != SOURCES_SECTION:
            body_lines.extend(s.lines)
    cited = set()
    for no_line in strip_code(body_lines):
        try:
            cited |= parse_citations(no_line)
        except ValueError as e:
            res.err(f"citation error: {e}")
    if not cited:
        res.err("no [n] citations found in the report body")
    for n in sorted(cited - set(sources)):
        res.err(f"citation [{n}] has no matching entry in {SOURCES_SECTION}")
    for n in sorted(set(sources) - cited):
        res.warn(f"[Sources] entry {n} is never cited")

    # --- legal claims backed only by secondary sources must be attributed
    tiers = {n: (TIER_RE.match(t).group(1) if TIER_RE.match(t) else None) for n, t in sources.items()}
    for title, label, nums, text, na_row in res.legal_rows:
        known = [tiers.get(n) for n in nums if n in tiers]
        if na_row or not known:
            continue
        if all(t == "S" for t in known) and not ATTRIBUTION_RE.search(text):
            res.warn(f"[{title}] row '{label}': legal claim backed only by [S] sources — say who "
                     "says it (\"per …\", \"according to …\") or cite a [P] source")
    return res


def extract_skeleton(text):
    """Return the part of the template between the SKELETON markers (whole text if absent)."""
    m = re.search(r"<!-- BEGIN SKELETON -->\n(.*?)<!-- END SKELETON -->", text, re.S)
    return m.group(1) if m else text


# ---------------------------------------------------------------------------
# Structural diff across reports
# ---------------------------------------------------------------------------

def structural_diff(results):
    """Compare common structural elements. Returns (rows, n_differences)."""
    rows, diffs = [], 0

    def compare(label, values, informational=False):
        nonlocal diffs
        same = all(v == values[0] for v in values)
        if not same and not informational:
            diffs += 1
        rows.append((label, same, informational, values))

    sigs = [r.signature for r in results]
    compare("Section headings", [tuple(s.get("headings", [])) for s in sigs])
    for title in TABLES:
        compare(f"{title}: columns",
                [tuple(s.get("tables", {}).get(title) or ()) for s in sigs],
                informational=TABLES[title]["optional"])
        if TABLES[title]["fixed_rows"] is not None:
            compare(f"{title}: fixed rows",
                    [tuple(s.get("fixed_rows", {}).get(title, ())) for s in sigs])
        compare(f"{title}: product-specific rows",
                [tuple(s.get("extra_rows", {}).get(title, ())) for s in sigs],
                informational=True)
    return rows, diffs


def short(values, width=60):
    text = "; ".join(values) if values else "(none)"
    return text if len(text) <= width else text[: width - 1] + "…"


# ---------------------------------------------------------------------------
# Renumbering
# ---------------------------------------------------------------------------

def _expand(group):
    """Numbers in one citation group, or None if the group is only years ([2026])."""
    nums, real = [], False
    for part in group.split(","):
        part = part.strip()
        if re.search(r"[-–]", part):
            a, b = (int(x) for x in re.split(r"\s*[-–]\s*", part))
            if _is_year(a) and _is_year(b):
                continue
            if a > b:
                raise ValueError(f"reversed citation range [{part}]")
            nums.extend(range(a, b + 1))
        else:
            n = int(part)
            if len(part) == 4 and _is_year(n):
                continue
            nums.append(n)
        real = True
    return nums if real else None


def _collapse(nums):
    """[1, 2, 3, 5] -> "1-3, 5" (runs of 3+ become ranges)."""
    nums, out, i = sorted(set(nums)), [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append(f"{nums[i]}-{nums[j]}")
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return ", ".join(out)


def _map_line(line, fn):
    """Apply fn to every citation group outside inline code; fn(match) -> replacement."""
    parts = re.split(r"(`[^`]*`)", line)
    return "".join(p if p.startswith("`") else CITE_RE.sub(fn, p) for p in parts)


def renumber(text):
    """Renumber citations by first appearance in the body and reorder Appendix B.

    Returns (new_text, mapping old->new). Raises ValueError on citations without a source.
    """
    lines = text.splitlines(keepends=True)
    src_start = next((i for i, l in enumerate(lines)
                      if (m := HEADING_RE.match(l.rstrip("\n"))) and len(m.group(1)) == 2
                      and norm(m.group(2)) == SOURCES_SECTION), None)
    if src_start is None:
        raise ValueError(f"no '## {SOURCES_SECTION}' section")
    src_end = next((i for i in range(src_start + 1, len(lines))
                    if (m := HEADING_RE.match(lines[i].rstrip("\n"))) and len(m.group(1)) <= 2),
                   len(lines))

    # sources: numbered items, with indented continuation lines attached
    entries, preamble, current = {}, [], None
    for l in lines[src_start + 1:src_end]:
        m = SOURCE_ITEM_RE.match(l.rstrip("\n"))
        if m:
            current = int(m.group(1))
            if current in entries:
                raise ValueError(f"duplicate source number {current}")
            entries[current] = [m.group(2)]
        elif current is not None and l.strip():
            entries[current].append(l.rstrip("\n"))
        elif current is None:
            preamble.append(l)

    body_idx = [i for i in range(len(lines)) if not src_start <= i < src_end]
    order, fenced = [], False
    for i in body_idx:
        if lines[i].lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for part in re.split(r"`[^`]*`", lines[i]):
            for m in CITE_RE.finditer(part):
                for n in _expand(m.group(1)) or []:
                    if n not in order:
                        order.append(n)
    missing = [n for n in order if n not in entries]
    if missing:
        raise ValueError(f"citations without a source entry: {missing}")
    mapping = {old: new for new, old in enumerate(order, 1)}
    for old in sorted(entries):              # uncited sources keep their relative order at the end
        if old not in mapping:
            mapping[old] = len(mapping) + 1

    def sub(m):
        nums = _expand(m.group(1))
        return m.group(0) if nums is None else f"[{_collapse(mapping[n] for n in nums)}]"

    out, fenced = list(lines), False
    for i in body_idx:
        if lines[i].lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out[i] = _map_line(lines[i], sub)
    new_src = [lines[src_start]] + preamble
    for old in sorted(entries, key=lambda o: mapping[o]):
        first, *rest = entries[old]
        new_src.append(f"{mapping[old]}. {first}\n")
        new_src.extend(r + "\n" for r in rest)
    if src_end < len(lines):
        new_src.append("\n")
    return "".join(out[:src_start] + new_src + out[src_end:]), mapping


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("reports", nargs="*", help="report markdown files")
    ap.add_argument("--template", help="validate the template skeleton instead of a report")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--renumber", action="store_true",
                    help="rewrite ONE report in place (backup: <file>.bak) so citations are numbered "
                         "by first appearance and Appendix B follows that order; then validate")
    args = ap.parse_args(argv)

    if args.renumber:
        if len(args.reports) != 1 or args.template:
            ap.error("--renumber takes exactly one report")
        path = args.reports[0]
        try:
            with open(path, encoding="utf-8") as fh:
                original = fh.read()
            new_text, mapping = renumber(original)
        except (OSError, UnicodeDecodeError) as e:
            print(f"error: cannot read {path}: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"error: cannot renumber {path}: {e}", file=sys.stderr)
            return 1
        changed = {o: n for o, n in mapping.items() if o != n}
        if new_text != original:
            with open(path + ".bak", "w", encoding="utf-8") as fh:
                fh.write(original)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new_text)
        if new_text == original:
            note = "; no change"
        elif not changed:
            note = f"; only citation groups sorted / merged; backup at {path}.bak"
        else:
            note = f"; backup at {path}.bak"
        print(f"renumbered {len(changed)} of {len(mapping)} source(s){note}")
        for o, n in sorted(changed.items(), key=lambda kv: kv[1]):
            print(f"  [{o}] -> [{n}]")

    targets = [(p, False) for p in args.reports] + ([(args.template, True)] if args.template else [])
    if not targets:
        ap.error("give at least one report (or --template)")

    results = []
    for path, is_tpl in targets:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"error: cannot read {path}: {e}", file=sys.stderr)
            return 2
        if is_tpl:
            text = extract_skeleton(text)
        results.append(validate(path, text, is_template=is_tpl))

    diff_rows, n_diffs = ([], 0)
    report_results = [r for r, (_, tpl) in zip(results, targets) if not tpl]
    if len(report_results) > 1:
        diff_rows, n_diffs = structural_diff(report_results)

    failed = any(r.errors or (args.strict and r.warnings) for r in results) or n_diffs > 0

    if args.json:
        print(json.dumps({
            "ok": not failed,
            "reports": [{"path": r.path, "errors": r.errors, "warnings": r.warnings}
                        for r in results],
            "diff": [{"element": l, "same": s, "informational": i, "values": [list(v) for v in vals]}
                     for l, s, i, vals in diff_rows],
            "structural_differences": n_diffs,
        }, indent=2))
        return 1 if failed else 0

    for r in results:
        status = "FAIL" if (r.errors or (args.strict and r.warnings)) else "OK"
        print(f"== {r.path}: {status} ({len(r.errors)} errors, {len(r.warnings)} warnings)")
        for e in r.errors:
            print(f"  ERROR   {e}")
        for w in r.warnings:
            print(f"  warning {w}")
    if diff_rows:
        print("\n== Structural comparison: " + " vs ".join(r.path for r in report_results))
        for label, same, info, values in diff_rows:
            mark = "same" if same else ("info" if info else "DIFF")
            print(f"  [{mark:4}] {label}")
            if not same:
                for r, v in zip(report_results, values):
                    print(f"           {r.path}: {short(list(v))}")
        print(f"\n{n_diffs} structural difference(s) in common elements")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
