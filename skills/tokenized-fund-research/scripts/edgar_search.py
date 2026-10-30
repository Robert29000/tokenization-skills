#!/usr/bin/env python3
"""Search SEC EDGAR full-text search for filings by a fund / issuer name.

  export SEC_USER_AGENT="Your Name your.email@example.com"   # required by the SEC
  python3 -I edgar_search.py "BlackRock USD Institutional Digital Liquidity Fund"
  python3 -I edgar_search.py "Superstate Asset Trust" --user-agent-file reports/.work/x/.sec-user-agent
  python3 -I edgar_search.py "Superstate Asset Trust" --forms D,N-1A   # D includes D/A
  python3 -I edgar_search.py "Apollo Diversified Credit" --raw --max-results 50 --json
  python3 -I edgar_search.py "Superstate Asset Trust" --forms D --details   # parse Form D XML

The name is searched as an exact phrase (use --raw to pass your own query syntax).
Results are grouped by CIK. For Form D filings the claimed exemptions are decoded
(e.g. 506(c), 3(c)(7)) because they tell you who may invest. --details also downloads the
latest Form D of each matching issuer and prints related persons (managers, directors,
promoters), minimum investment, amount sold, investor count and sales-compensation
recipients (placement agents / broker-dealers).

The User-Agent comes from SEC_USER_AGENT, or, when that is unset, from the one-line file given
with --user-agent-file (so the contact never has to appear in a shell command).

Exit code: 0 = success (including "0 results"), 1 = request failed, 2 = bad arguments /
missing or invalid SEC_USER_AGENT. Standard library only; honours HTTPS_PROXY.
"""

import argparse
import datetime
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ENDPOINT = "https://efts.sec.gov/LATEST/search-index"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data"
PAGE_SIZE = 100          # efts returns 100 hits per page
TIMEOUT = 30
RETRIES = 3
BACKOFF = 2.0
MIN_INTERVAL = 0.12      # SEC fair-access limit is 10 requests/second
FORM_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-/]{0,15}$")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
EARLIEST_DATE = "2001-01-01"   # efts full-text search coverage starts in 2001
MAX_DETAILS = 5                 # Form D XML downloads per run
MAX_BYTES = 20 * 1024 * 1024    # largest response read; search pages and Form D XML are far smaller
MAX_UA_FILE = 1024              # --user-agent-file holds one short line
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

# Form D "items": federal exemptions claimed (Form D, Item 6). Codes as returned by efts;
# "3C.<n>" codes are decoded generically, unknown codes are shown raw.
FORM_D_ITEMS = {
    "06": "Rule 506 (paragraph not given)",
    "06B": "Rule 506(b) — no general solicitation; up to 35 non-accredited",
    "06C": "Rule 506(c) — general solicitation; accredited investors only, verified",
    "3C": "Investment Company Act §3(c) exclusion",
    "3C.1": "ICA §3(c)(1) — ≤100 beneficial owners",
    "3C.7": "ICA §3(c)(7) — qualified purchasers only",
}
# EDGAR state/country codes most relevant to tokenized funds (others shown raw).
STATE_CODES = {"D8": "British Virgin Islands", "E9": "Cayman Islands", "DE": "Delaware"}

_sleep = time.sleep      # patched in tests
_last_request = [0.0]


class FetchError(Exception):
    def __init__(self, kind, message, status=None):
        super().__init__(message)
        self.kind = kind
        self.status = status


def user_agent(path=None):
    """Return (ua, warning). ua is None when neither SEC_USER_AGENT nor the file gives one.

    The environment wins over the file. Raises ValueError for an unreadable or malformed file
    and for control characters, which would let the value inject extra HTTP headers.
    """
    ua = (os.environ.get("SEC_USER_AGENT") or "").strip()
    if not ua and path:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read(MAX_UA_FILE + 1)
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError(f"cannot read --user-agent-file {path}: {e}")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(text) > MAX_UA_FILE or len(lines) > 1:
            raise ValueError(f"--user-agent-file {path} must hold one line: 'Name email@domain'")
        if not lines:
            raise ValueError(f"--user-agent-file {path} is empty")
        ua = lines[0]
    if not ua:
        return None, None
    if CONTROL_RE.search(ua):
        raise ValueError("the SEC User-Agent contains control characters")
    if not EMAIL_RE.search(ua):
        return ua, ("SEC_USER_AGENT has no email address; the SEC may block requests "
                    "(expected 'Name email@domain')")
    return ua, None


def parse_forms(value):
    if value is None:
        return []
    forms = [f.strip().upper() for f in value.split(",") if f.strip()]
    if not forms:
        raise ValueError("empty --forms list")
    bad = [f for f in forms if not FORM_RE.match(f)]
    if bad:
        raise ValueError(f"invalid form type(s) {bad} (examples: D, D/A, N-1A, 10-K, 13F-HR)")
    forms = list(dict.fromkeys(forms))
    # efts quirk: "D" already matches D/A amendments, but listing "D/A" next to "D" narrows
    # the whole result to amendments only — so drop X/A when X is present.
    return [f for f in forms if not (f.endswith("/A") and f[:-2] in forms)]


def build_query(name, raw=False):
    """Phrase-quote the entity name. Embedded double quotes cannot be escaped in efts."""
    name = re.sub(r"\s+", " ", (name or "")).strip()
    if raw:
        return name
    name = name.replace('"', " ").strip()
    name = re.sub(r"\s+", " ", name)
    return f'"{name}"' if name else ""


def _throttle():
    wait = MIN_INTERVAL - (time.monotonic() - _last_request[0])
    if wait > 0:
        _sleep(wait)
    _last_request[0] = time.monotonic()


def fetch_json(url, ua):
    raw = fetch_bytes(url, ua, "application/json")
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        head = raw[:200].lstrip().lower()
        kind = "blocked" if head.startswith(b"<") else "bad_json"
        raise FetchError(kind, f"non-JSON response from {url}")


def fetch_bytes(url, ua, accept="*/*"):
    delay = BACKOFF
    last = None
    for attempt in range(RETRIES + 1):
        _throttle()
        req = urllib.request.Request(url, headers={
            "User-Agent": ua, "Accept": accept, "Accept-Encoding": "identity"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise FetchError("too_large", f"response from {url} is larger than {MAX_BYTES} bytes")
            return raw
        except urllib.error.HTTPError as e:
            # SEC answers 403 both for missing UA and for rate limiting; 429 for rate limiting
            if e.code in (403, 429) or 500 <= e.code < 600:
                last = FetchError("http", f"HTTP {e.code} from SEC"
                                  + (" (check SEC_USER_AGENT / rate limit)" if e.code == 403 else ""),
                                  e.code)
            else:
                raise FetchError("http", f"HTTP {e.code} from SEC for {url}", e.code)
        except (socket.timeout, TimeoutError):
            last = FetchError("timeout", f"timeout after {TIMEOUT}s")
        except urllib.error.URLError as e:
            last = FetchError("network", f"network error: {e.reason}")
        except (ConnectionError, OSError) as e:
            last = FetchError("network", f"network error: {e}")
        if attempt < RETRIES:
            _sleep(delay)
            delay *= 2
    raise last


def search(name, forms, ua, max_results, raw=False, date_from=None, date_to=None):
    """Return (filings, total_reported)."""
    q = build_query(name, raw)
    filings, seen, start, total = [], set(), 0, 0
    while start < max_results:
        params = {"q": q}
        if forms:
            params["forms"] = ",".join(forms)
        if date_from or date_to:
            # efts silently ignores a one-sided range, so always send both ends
            params["dateRange"] = "custom"
            params["startdt"] = date_from or EARLIEST_DATE
            params["enddt"] = date_to or datetime.date.today().isoformat()
        if start:
            params["from"] = start
        data = fetch_json(f"{ENDPOINT}?{urllib.parse.urlencode(params)}", ua)
        hits_obj = (data or {}).get("hits") if isinstance(data, dict) else None
        if not isinstance(hits_obj, dict):
            break
        total_obj = hits_obj.get("total")
        total = total_obj.get("value", 0) if isinstance(total_obj, dict) else (total_obj or 0)
        hits = hits_obj.get("hits") or []
        for h in hits:
            f = normalise_hit(h)
            if f and f["key"] not in seen:
                seen.add(f["key"])
                filings.append(f)
        start += len(hits)
        if not hits or start >= total:
            break
    return filings[:max_results], total


def normalise_hit(hit):
    if not isinstance(hit, dict):
        return None
    src = hit.get("_source") or {}
    hid = hit.get("_id") or ""
    adsh, _, filename = hid.partition(":")
    adsh = src.get("adsh") or adsh
    ciks = [c for c in (src.get("ciks") or []) if c] or ["?"]
    names = src.get("display_names") or []
    items = src.get("items") or []
    url = None
    if adsh and ciks[0] != "?":
        try:
            url = f"{ARCHIVE}/{int(ciks[0])}/{adsh.replace('-', '')}/{filename or ''}".rstrip("/")
        except ValueError:
            url = None
    return {
        "key": (adsh, filename),
        "adsh": adsh or "?",
        "form": src.get("form") or src.get("file_type") or "?",
        "file_date": src.get("file_date") or "?",
        "ciks": ciks,
        "names": [re.sub(r"\s+", " ", n).strip() for n in names],
        "inc_states": list(dict.fromkeys(STATE_CODES.get(s, s) for s in (src.get("inc_states") or []) if s)),
        "biz_locations": list(dict.fromkeys(src.get("biz_locations") or [])),
        "items": items,
        # Form D items are claimed exemptions; other forms (8-K…) use items for event codes
        "exemptions": decode_items(items) if is_form_d(src) else [],
        "url": url,
    }


def is_form_d(src):
    forms = [src.get("form"), src.get("file_type")] + list(src.get("root_forms") or [])
    return any(f in ("D", "D/A") for f in forms if f)


def name_for_cik(cik, names):
    """Pick the display name that mentions this CIK; display_names order is not guaranteed."""
    for n in names:
        if cik in n:
            return clean_name(n)
    return clean_name(names[0]) if names else "?"


def clean_name(name):
    return re.sub(r"\s*\(CIK \d+\)\s*$", "", name).strip() or name


def decode_item(code):
    code = str(code).strip().upper()   # efts says "06C", the Form D XML says "06c"
    if code in FORM_D_ITEMS:
        return FORM_D_ITEMS[code]
    m = re.fullmatch(r"3C\.(\d+)", code)
    if m:
        return f"ICA §3(c)({m.group(1)})"
    return f"item {code}"


def decode_items(items):
    """Decode a list of Form D items; the bare "3C" is dropped when a 3C.<n> is present."""
    codes = [str(i).strip().upper() for i in items if str(i).strip()]
    if any(re.fullmatch(r"3C\.\d+", c) for c in codes):
        codes = [c for c in codes if c != "3C"]
    return [decode_item(c) for c in dict.fromkeys(codes)]


def _text(node, path):
    if node is None:
        return None
    found = node.find(path)
    value = (found.text or "").strip() if found is not None else ""
    return value or None


def parse_form_d(raw):
    """Parse a Form D primary_doc.xml into the fields that matter for investor eligibility."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise FetchError("bad_xml", f"Form D XML could not be parsed: {e}")
    # some filings use a default namespace; strip it so plain tag paths work
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    issuer = root.find("primaryIssuer")
    offering = root.find("offeringData")
    persons = []
    for p in root.iterfind("relatedPersonsList/relatedPersonInfo"):
        first = _text(p, "relatedPersonName/firstName")
        last = _text(p, "relatedPersonName/lastName")
        name = " ".join(x for x in (first, last) if x and x.upper() not in ("N/A", "NA", "-"))
        persons.append({
            "name": name or "?",
            "relationships": [r.text.strip() for r in p.iterfind("relatedPersonRelationshipList/relationship") if r.text],
            "clarification": _text(p, "relationshipClarification"),
        })
    recipients = []
    for r in root.iterfind("offeringData/salesCompensationList/recipient"):
        # states appear as <value>, <state> or an empty <allStates/> depending on the filing
        sol = r.find("statesOfSolicitationList")
        states = [c.text.strip() for c in (sol if sol is not None else []) if c.text and c.text.strip()]
        if sol is not None and sol.find("allStates") is not None and not states:
            states = ["All States"]
        recipients.append({
            "name": _text(r, "recipientName") or "?",
            "crd": _text(r, "recipientCRDNumber"),
            "broker_dealer": _text(r, "associatedBDName"),
            "states": states,
            "foreign_solicitation": _text(r, "foreignSolicitation"),
        })
    items = [i.text for i in root.iterfind("offeringData/federalExemptionsExclusions/item") if i.text]
    return {
        "submission_type": _text(root, "submissionType"),
        "issuer": _text(issuer, "entityName"),
        "jurisdiction": _text(issuer, "jurisdictionOfInc"),
        "entity_type": _text(issuer, "entityTypeOtherDesc") or _text(issuer, "entityType"),
        "previous_names": [n.text.strip() for n in root.iterfind("primaryIssuer/edgarPreviousNameList/previousName") if n.text],
        "related_persons": persons,
        "fund_type": _text(offering, "industryGroup/investmentFundInfo/investmentFundType"),
        "is_40_act": _text(offering, "industryGroup/investmentFundInfo/is40Act"),
        "exemptions": decode_items(items),
        "first_sale": _text(offering, "typeOfFiling/dateOfFirstSale/value"),
        "minimum_investment": _text(offering, "minimumInvestmentAccepted"),
        "total_offering": _text(offering, "offeringSalesAmounts/totalOfferingAmount"),
        "total_sold": _text(offering, "offeringSalesAmounts/totalAmountSold"),
        "non_accredited_investors": _text(offering, "investors/hasNonAccreditedInvestors"),
        "investors": _text(offering, "investors/totalNumberAlreadyInvested"),
        "sales_compensation": recipients,
        "signer": " — ".join(x for x in (_text(root, ".//signatureBlock/signature/nameOfSigner"),
                                          _text(root, ".//signatureBlock/signature/signatureTitle")) if x) or None,
        "signature_date": _text(root, ".//signatureBlock/signature/signatureDate"),
    }


def form_d_details(groups, ua):
    """Download and parse the latest Form D of each name-matched entity (or of all, if none)."""
    targets = [g for g in groups if g["name_match"]] or groups
    out = []
    for g in targets[:MAX_DETAILS]:
        latest = next((f for f in g["filings"] if f["form"] in ("D", "D/A") and f["url"]), None)
        if latest is None:
            continue
        entry = {"cik": g["cik"], "url": latest["url"], "file_date": latest["file_date"]}
        try:
            entry.update(parse_form_d(fetch_bytes(latest["url"], ua, "application/xml")))
        except FetchError as e:
            entry["error"] = str(e)
        out.append(entry)
    return out


def print_details(d):
    print(f"\n  Form D details ({d['file_date']}, {d.get('submission_type') or '?'}): {d['url']}")
    if d.get("error"):
        print(f"    error: {d['error']}")
        return
    rows = [
        ("Issuer", f"{d['issuer'] or '?'} — {d['entity_type'] or '?'}, {d['jurisdiction'] or '?'}"),
        ("Previous names", "; ".join(d["previous_names"])),
        ("Fund type", f"{d['fund_type'] or '?'} (1940 Act registered: {d['is_40_act'] or '?'})"),
        ("Exemptions", "; ".join(d["exemptions"])),
        ("First sale", d["first_sale"]),
        ("Minimum investment", d["minimum_investment"]),
        ("Offering / sold", f"{d['total_offering'] or '?'} / {d['total_sold'] or '?'}"),
        ("Investors", f"{d['investors'] or '?'} (non-accredited: {d['non_accredited_investors'] or '?'})"),
        ("Signed by", f"{d['signer'] or '?'} on {d['signature_date'] or '?'}"),
    ]
    for label, value in rows:
        if value:
            print(f"    {label + ':':<20} {value}")
    for p in d["related_persons"]:
        rel = ", ".join(p["relationships"]) or "?"
        print(f"    Related person:      {p['name']} [{rel}]" + (f" — {p['clarification']}" if p["clarification"] else ""))
    if not d["sales_compensation"]:
        print("    Sales compensation:  none listed")
    for r in d["sales_compensation"]:
        bd = f", BD {r['broker_dealer']}" if r["broker_dealer"] and r["broker_dealer"].upper() not in ("NONE", "N/A") else ""
        crd = f", CRD {r['crd']}" if r["crd"] and r["crd"].upper() not in ("NONE", "N/A") else ""
        foreign = f"; foreign solicitation: {r['foreign_solicitation']}" if r["foreign_solicitation"] else ""
        print(f"    Sales compensation:  {r['name']}{crd}{bd} — states: {', '.join(r['states']) or '?'}{foreign}")


def group_by_cik(filings, phrase=""):
    """Group filings by CIK. Entities whose name contains the searched phrase come first."""
    groups = {}
    for f in filings:
        for cik in f["ciks"]:
            name = name_for_cik(cik, f["names"])
            g = groups.setdefault(cik, {"cik": cik, "names": [], "filings": []})
            if name not in g["names"]:
                g["names"].append(name)
            g["filings"].append(f)
    phrase = re.sub(r"\s+", " ", phrase.replace('"', " ")).strip().lower()
    for g in groups.values():
        g["filings"].sort(key=lambda f: f["file_date"], reverse=True)
        g["name_match"] = bool(phrase) and any(phrase in n.lower() for n in g["names"])
    return sorted(groups.values(), key=lambda g: (not g["name_match"], -len(g["filings"])))


def main(argv=None):
    ap = argparse.ArgumentParser(description="SEC EDGAR full-text search grouped by CIK.")
    ap.add_argument("name", help="entity / fund name (searched as an exact phrase)")
    ap.add_argument("--forms", help="comma list of form types, e.g. D,N-1A (default: all)")
    ap.add_argument("--raw", action="store_true", help="send the query as-is (no phrase quoting)")
    ap.add_argument("--from-date", help="YYYY-MM-DD")
    ap.add_argument("--to-date", help="YYYY-MM-DD")
    ap.add_argument("--max-results", type=int, default=100)
    ap.add_argument("--details", action="store_true",
                    help=f"parse the latest Form D XML of up to {MAX_DETAILS} matching issuers")
    ap.add_argument("--user-agent-file",
                    help="file holding the SEC User-Agent ('Name email'), used when SEC_USER_AGENT is unset")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        ua, warning = user_agent(args.user_agent_file)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if ua is None:
        print("error: set SEC_USER_AGENT or pass --user-agent-file first, e.g.\n"
              '  export SEC_USER_AGENT="Your Name your.email@example.com"\n'
              "The SEC rejects requests without a descriptive User-Agent.", file=sys.stderr)
        return 2
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    try:
        forms = parse_forms(args.forms)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not build_query(args.name, args.raw).strip('" '):
        print("error: empty entity name", file=sys.stderr)
        return 2
    for d in (args.from_date, args.to_date):
        if d is None:
            continue
        try:
            datetime.date.fromisoformat(d) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else int("x")
        except ValueError:
            print(f"error: date '{d}' is not a valid YYYY-MM-DD date", file=sys.stderr)
            return 2
    if args.from_date and args.to_date and args.from_date > args.to_date:
        print("error: --from-date is after --to-date", file=sys.stderr)
        return 2
    if args.max_results < 1:
        print("error: --max-results must be >= 1", file=sys.stderr)
        return 2

    try:
        filings, total = search(args.name, forms, ua, args.max_results, args.raw,
                                args.from_date, args.to_date)
    except FetchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    groups = group_by_cik(filings, "" if args.raw else args.name)
    details = form_d_details(groups, ua) if args.details else []

    if args.json:
        out = [{"cik": g["cik"], "names": g["names"], "name_match": g["name_match"],
                "filings": [{k: v for k, v in f.items() if k != "key"} for f in g["filings"]]}
               for g in groups]
        print(json.dumps({"query": build_query(args.name, args.raw), "total": total,
                          "shown": len(filings), "entities": out, "form_d_details": details},
                         indent=2, ensure_ascii=False))
        return 0

    q = build_query(args.name, args.raw)
    if not filings:
        print(f"0 results for {q}" + (f" (forms: {','.join(forms)})" if forms else ""))
        return 0
    print(f"{len(filings)} filing(s) shown of {total} for {q}, {len(groups)} entit(y/ies)")
    if len(groups) > 1:
        print("note: several CIKs matched — entities whose name contains the phrase are listed "
              "first (marked *); the others only mention it in a filing")
    for g in groups:
        star = "*" if g["name_match"] else " "
        print(f"\n{star}CIK {g['cik']} — {' / '.join(g['names'])}")
        for f in g["filings"]:
            extra = []
            if f["inc_states"]:
                extra.append("inc: " + ", ".join(f["inc_states"]))
            if f["exemptions"]:
                extra.append("exemptions: " + "; ".join(f["exemptions"]))
            elif f["items"]:
                extra.append("items: " + ", ".join(map(str, f["items"])))
            print(f"  {f['file_date']}  {f['form']:<8} {f['url'] or f['adsh']}")
            if extra:
                print(f"            {' | '.join(extra)}")
        for d in details:
            if d["cik"] == g["cik"]:
                print_details(d)
    if args.details and not details:
        print("\nnote: --details found no Form D filing to parse (try --forms D)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
