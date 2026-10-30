#!/usr/bin/env python3
"""Search governance forums (Discourse) and dump threads as text.

The forums are the files in references/forums/: one <name>.md per forum, starting with
front matter (base_url, engine, optional curators). Add a file to add a forum; nothing here
changes.

  python3 -I forum_search.py --list-forums                  # names, URLs, curator handles

Search (each term is searched separately; results are merged and de-duplicated):
  python3 -I forum_search.py mTBILL "Midas"                 # all forums
  python3 -I forum_search.py USTB --forums <name>,<name>
  python3 -I forum_search.py OUSG Ondo --all-terms          # one query requiring all terms
  python3 -I forum_search.py JAAA --curators                # "JAAA @<handle>" per forum curator
  python3 -I forum_search.py JAAA --max-pages 3 --json

Read one thread (all posts, HTML converted to text):
  python3 -I forum_search.py --thread https://<forum host>/t/some-slug/25536
  python3 -I forum_search.py --thread 25536 --forum <name>

Exit code: 0 = success (including "0 results"), 1 = every forum failed / thread not
retrievable / a forum file is invalid, 2 = bad arguments. Standard library only; honours
HTTPS_PROXY.
"""

import argparse
import html
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORUMS_DIR = os.path.join(SKILL_DIR, "references", "forums")
FORUMS = {}    # name -> base URL, filled from FORUMS_DIR by use_forums()
CURATORS = {}  # name -> curator usernames to search with @<handle>
FRONT_KEYS = {"base_url", "engine", "curators"}
ENGINES = {"discourse"}
FRONT_RE = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.S)
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
HANDLE_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")
USER_AGENT = "tokenized-fund-research/1.0 (+governance forum reader)"
TIMEOUT = 20
RETRIES = 3            # retries for 5xx / timeouts / network errors
RATE_LIMIT_RETRIES = 6 # separate, larger budget for HTTP 429 (parallel collectors share a forum)
BACKOFF = 1.5          # seconds, doubled on each retry
MAX_RETRY_AFTER = 30   # cap for Retry-After headers
MIN_INTERVAL = 0.5     # minimum seconds between requests to the same forum
MIN_TERM_LEN = 3       # Discourse default min_search_term_length
POSTS_CHUNK = 20       # Discourse returns at most ~20 posts per request
MAX_BYTES = 20 * 1024 * 1024   # largest response read
# terminal escapes and other control characters, plus bidi overrides that can hide text
# (Trojan Source); forum posts are written by anyone, so they never reach the output
CONTROL_RE = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")

_sleep = time.sleep    # patched in tests
_last_request = {}     # host -> monotonic time of the last request


def load_forums(folder):
    """Read <folder>/<name>.md forum files. Returns (forums, curators); raises ValueError."""
    try:
        files = sorted(f for f in os.listdir(folder) if f.endswith(".md") and not f.startswith("."))
    except OSError as e:
        raise ValueError(f"cannot read the forum folder {folder}: {e}")
    if not files:
        raise ValueError(f"no forum files (<name>.md) in {folder}")
    forums, curators, hosts = {}, {}, {}
    for fname in files:
        name, label = fname[:-3], f"references/forums/{fname}"
        if not NAME_RE.match(name):
            raise ValueError(f"{label}: the file name must be lowercase letters, digits and dashes")
        try:
            with open(os.path.join(folder, fname), encoding="utf-8") as fh:
                text = fh.read().replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError) as e:
            raise ValueError(f"cannot read {label}: {e}")
        m = FRONT_RE.match(text)
        if not m:
            raise ValueError(f"{label}: no front matter (a '---' block) at the top")
        meta = {}
        for line in m.group(1).split("\n"):
            if not line.strip():
                continue
            key, sep, value = line.partition(":")
            key = key.strip()
            if not sep or key not in FRONT_KEYS:
                raise ValueError(f"{label}: unknown front-matter line '{line.strip()}' "
                                 f"(keys: {', '.join(sorted(FRONT_KEYS))})")
            if key in meta:
                raise ValueError(f"{label}: '{key}' is given twice")
            meta[key] = value.strip()
        base = (meta.get("base_url") or "").rstrip("/")
        url = urllib.parse.urlparse(base)
        if (url.scheme != "https" or not url.hostname or url.path or url.params or url.query
                or url.fragment or url.username or url.port):
            raise ValueError(f"{label}: base_url must be https://<host> with no path, e.g. "
                             "https://forum.example.org")
        engine = meta.get("engine", "")
        if engine not in ENGINES:
            raise ValueError(f"{label}: engine '{engine}' is not supported "
                             f"(supported: {', '.join(sorted(ENGINES))})")
        handles = [h.strip().lstrip("@") for h in meta.get("curators", "").split(",") if h.strip()]
        bad = [h for h in handles if not HANDLE_RE.match(h)]
        if bad:
            raise ValueError(f"{label}: curators must be forum usernames, got {bad}")
        host = _host(base)
        if host in hosts:
            raise ValueError(f"{label}: {host} is already the forum '{hosts[host]}'")
        hosts[host] = name
        forums[name] = f"https://{url.hostname}"
        curators[name] = list(dict.fromkeys(handles))
    return forums, curators


def use_forums(folder=None):
    """Load the forum files into FORUMS and CURATORS. Raises ValueError."""
    global FORUMS, CURATORS
    FORUMS, CURATORS = load_forums(folder or FORUMS_DIR)


def _host(url):
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


class FetchError(Exception):
    """A request failed. kind: http | blocked | timeout | network | bad_json | api."""

    def __init__(self, kind, message, status=None):
        super().__init__(message)
        self.kind = kind
        self.status = status


def _throttle(url):
    """Space out requests to the same forum host by MIN_INTERVAL."""
    host = urllib.parse.urlparse(url).netloc
    previous = _last_request.get(host)
    if previous is not None:
        wait = MIN_INTERVAL - (time.monotonic() - previous)
        if wait > 0:
            _sleep(wait)
    _last_request[host] = time.monotonic()


def fetch_json(url):
    """GET url and decode JSON, retrying on 429/5xx/timeouts. Raises FetchError."""
    delay = BACKOFF
    last = None
    errors = rate_limited = 0
    while True:
        _throttle(url)
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                ctype = resp.headers.get("Content-Type", "") or ""
                raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise FetchError("too_large", f"response from {url} is larger than {MAX_BYTES} bytes")
            return _decode_json(raw, ctype, url)
        except urllib.error.HTTPError as e:
            body = _safe_read(e)
            if e.code == 429 or 500 <= e.code < 600:
                last = FetchError("http", f"HTTP {e.code} from {url}"
                                  + (" (rate limited; retries exhausted)" if e.code == 429 else ""), e.code)
                if e.code == 429:
                    rate_limited += 1
                    exhausted = rate_limited > RATE_LIMIT_RETRIES
                else:
                    errors += 1
                    exhausted = errors > RETRIES
                if exhausted:
                    raise last
                _sleep(_retry_after(e, delay))
                delay = min(delay * 2, MAX_RETRY_AFTER)
                continue
            if e.code == 403 and _looks_like_html(body):
                raise FetchError("blocked", f"HTTP 403 (bot protection / challenge page) from {url}", 403)
            if body:
                # Discourse returns JSON errors with 4xx, e.g. invalid search parameters
                try:
                    data = json.loads(body.decode("utf-8", "replace"))
                    if isinstance(data, dict) and data.get("errors"):
                        raise FetchError("api", f"HTTP {e.code}: {'; '.join(map(str, data['errors']))}", e.code)
                except ValueError:
                    pass
            raise FetchError("http", f"HTTP {e.code} from {url}", e.code)
        except (socket.timeout, TimeoutError) as e:
            last = FetchError("timeout", f"timeout after {TIMEOUT}s: {url}")
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                last = FetchError("timeout", f"timeout after {TIMEOUT}s: {url}")
            else:
                last = FetchError("network", f"network error for {url}: {e.reason}")
        except (ConnectionError, OSError) as e:
            last = FetchError("network", f"network error for {url}: {e}")
        errors += 1
        if errors > RETRIES:
            raise last
        _sleep(delay)
        delay = min(delay * 2, MAX_RETRY_AFTER)


def _safe_read(err):
    try:
        return err.read() or b""
    except Exception:
        return b""


def _retry_after(err, default):
    value = err.headers.get("Retry-After") if err.headers else None
    try:
        return min(float(value), MAX_RETRY_AFTER) if value else default
    except ValueError:
        return default


def clean_text(text):
    """Drop control and bidi-override characters from text written by forum users."""
    return CONTROL_RE.sub("", text or "")


def _looks_like_html(raw):
    head = raw[:500].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<head" in head


def _decode_json(raw, ctype, url):
    if _looks_like_html(raw) or "text/html" in ctype.lower():
        hint = "challenge page" if re.search(rb"cloudflare|cf-chl|captcha|just a moment", raw[:4000], re.I) else "HTML page"
        raise FetchError("blocked", f"got {hint} instead of JSON from {url}")
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise FetchError("bad_json", f"response from {url} is not valid JSON")
    if isinstance(data, dict) and data.get("errors"):
        raise FetchError("api", f"{url}: {'; '.join(map(str, data['errors']))}")
    return data


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def build_query(terms, all_terms):
    """Return the list of Discourse query strings to run."""
    def fmt(term):
        term = re.sub(r"\s+", " ", term.replace('"', " ")).strip()
        return f'"{term}"' if " " in term else term
    cleaned = [fmt(t) for t in terms if t and t.strip()]
    return [" ".join(cleaned)] if all_terms else cleaned


def validate_terms(terms):
    """Return an error message for unusable terms, or None."""
    real = [t for t in terms if t and t.replace('"', "").strip()]
    if not real:
        return "no search terms given"
    short = [t for t in real if len(t.replace('"', "").strip()) < MIN_TERM_LEN]
    if short:
        return (f"search term(s) {short} shorter than {MIN_TERM_LEN} characters; Discourse "
                "rejects them — use the full ticker or issuer name")
    return None


def search_forum(name, query, max_pages):
    """Return list of topic dicts for one forum and query (all pages up to max_pages)."""
    base = FORUMS[name]
    topics, blurbs = {}, {}
    for page in range(1, max_pages + 1):
        params = {"q": query}
        if page > 1:
            params["page"] = page
        data = fetch_json(f"{base}/search.json?{urllib.parse.urlencode(params)}")
        if not isinstance(data, dict):
            break
        for post in data.get("posts") or []:
            if not isinstance(post, dict):
                continue
            tid = post.get("topic_id")
            if tid is not None and tid not in blurbs and post.get("blurb"):
                blurbs[tid] = post["blurb"]
        page_topics = [t for t in data.get("topics") or [] if isinstance(t, dict)]
        for t in page_topics:
            tid = t.get("id")
            if tid is None or tid in topics:
                continue
            slug = t.get("slug") or "topic"
            topics[tid] = {
                "forum": name,
                "topic_id": tid,
                "title": clean_text(html.unescape(t.get("title") or t.get("fancy_title") or "(untitled)")),
                "url": f"{base}/t/{slug}/{tid}",
                "created_at": (t.get("created_at") or "")[:10],
                "last_posted_at": (t.get("last_posted_at") or "")[:10],
                "posts_count": t.get("posts_count"),
            }
        more = (data.get("grouped_search_result") or {}).get("more_full_page_results")
        if not page_topics or not more:
            break
    for tid, t in topics.items():
        t["blurb"] = _clean_blurb(blurbs.get(tid, ""))
    return list(topics.values())


def _clean_blurb(text):
    return clean_text(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text or "")))).strip()[:240]


def forum_queries(terms, forum, all_terms, curators=False):
    """Queries for one forum; with curators, one "<terms> @<handle>" query per curator."""
    if curators:
        return [build_query(list(terms) + [f"@{h}"], True)[0] for h in CURATORS.get(forum, [])]
    return build_query(terms, all_terms)


def run_search(terms, forums, all_terms, max_pages, curators=False):
    """Return (results, errors, forum_ok). results de-duplicated by (forum, topic_id).
    With curators, a forum whose file lists no curator is not searched and not in forum_ok."""
    results, errors = {}, []
    plan = {f: forum_queries(terms, f, all_terms, curators) for f in forums}
    forum_ok = {f: False for f in forums if plan[f]}
    for forum in forum_ok:
        for q in plan[forum]:
            try:
                found = search_forum(forum, q, max_pages)
            except FetchError as e:
                errors.append({"forum": forum, "query": q, "kind": e.kind, "error": str(e)})
                continue
            forum_ok[forum] = True
            for t in found:
                key = (t["forum"], t["topic_id"])
                if key in results:
                    results[key]["matched"].append(q)
                else:
                    t["matched"] = [q]
                    results[key] = t
    # forums in the requested order; within a forum, topics matching more terms first, then newest
    ordered = sorted(results.values(), key=lambda t: t["last_posted_at"] or "", reverse=True)
    ordered.sort(key=lambda t: (forums.index(t["forum"]), -len(t["matched"])))
    return ordered, errors, forum_ok


# ---------------------------------------------------------------------------
# Thread
# ---------------------------------------------------------------------------

def parse_thread_ref(ref, forum=None):
    """Return (forum_name, topic_id) from a URL, a /t/... path or a bare id (+forum)."""
    ref = (ref or "").strip()
    if not ref:
        raise ValueError("empty thread reference")
    if re.fullmatch(r"\d+", ref):
        if not forum:
            raise ValueError("a bare topic id needs --forum")
        return _check_forum(forum), int(ref)
    parsed = urllib.parse.urlparse(ref if "://" in ref or ref.startswith("/") else "https://" + ref)
    if parsed.netloc:
        host = _host(parsed.geturl())
        matches = [n for n, b in FORUMS.items() if _host(b) == host]
        if not matches:
            raise ValueError(f"unknown forum host '{host}' (known: "
                             + ", ".join(_host(b) for b in FORUMS.values())
                             + "; add a file to references/forums/ to search another forum)")
        name = matches[0]
        if forum and _check_forum(forum) != name:
            raise ValueError(f"--forum {forum} contradicts the URL host {host}")
    else:
        if not forum:
            raise ValueError("a path without host needs --forum")
        name = _check_forum(forum)
    path = re.sub(r"\.json$", "", parsed.path.rstrip("/"))
    # /t/slug/123, /t/123, /t/slug/123/45
    m = re.match(r"^/t/(?:[^/]+/)?(\d+)(?:/\d+)?$", path)
    if not m:
        raise ValueError(f"not a Discourse topic URL: {ref}")
    return name, int(m.group(1))


def _check_forum(name):
    name = name.lower().strip()
    if name not in FORUMS:
        raise ValueError(f"unknown forum '{name}' (known: {', '.join(FORUMS)})")
    return name


def fetch_thread(forum, topic_id):
    base = FORUMS[forum]
    data = fetch_json(f"{base}/t/{topic_id}.json")
    if not isinstance(data, dict):
        raise FetchError("bad_json", "topic response is not an object")
    stream = (data.get("post_stream") or {})
    posts = {p.get("id"): p for p in stream.get("posts") or [] if isinstance(p, dict)}
    missing = [pid for pid in stream.get("stream") or [] if pid not in posts]
    for i in range(0, len(missing), POSTS_CHUNK):
        chunk = missing[i:i + POSTS_CHUNK]
        query = urllib.parse.urlencode([("post_ids[]", pid) for pid in chunk])
        extra = fetch_json(f"{base}/t/{topic_id}/posts.json?{query}")
        for p in ((extra or {}).get("post_stream") or {}).get("posts") or []:
            if isinstance(p, dict):
                posts[p.get("id")] = p
    slug = data.get("slug") or "topic"
    ordered = sorted(posts.values(), key=lambda p: p.get("post_number") or 0)
    kept, skipped = [], 0
    for p in ordered:
        if p.get("deleted_at") or p.get("hidden") or p.get("user_deleted") or not (p.get("cooked") or "").strip():
            skipped += 1
            continue
        text = html_to_text(p["cooked"], base)
        if not text.strip():
            skipped += 1
            continue
        kept.append({
            "post_number": p.get("post_number"),
            # cite this, not the topic URL: "<base>/t/<slug>/<id>/<post_number>"
            "url": f"{base}/t/{slug}/{topic_id}/{p.get('post_number') or 1}",
            "username": clean_text(p.get("username")) or "?",
            "created_at": (p.get("created_at") or "")[:10],
            "reply_to": p.get("reply_to_post_number"),
            "text": text,
        })
    return {
        "forum": forum,
        "topic_id": topic_id,
        "title": clean_text(html.unescape(data.get("title") or "(untitled)")),
        "url": f"{base}/t/{slug}/{topic_id}",
        "created_at": (data.get("created_at") or "")[:10],
        "posts_total": len(stream.get("stream") or ordered),
        "posts_skipped": skipped,
        "posts_unretrieved": len([pid for pid in stream.get("stream") or [] if pid not in posts]),
        "posts": kept,
    }


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
             "pre", "table", "tr", "aside", "details", "summary", "hr"}
    SKIP = {"script", "style", "svg"}
    VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr", "area", "col"}

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.lines = []
        self.cur = ""
        self.quote = 0
        self.skip = 0
        self.links = []      # stack of (href, text_start)
        self.cell = 0
        self.list_depth = 0
        self.li_pending = False  # an <li> marker was written but no text yet

    def _flush(self):
        if self.li_pending and re.fullmatch(r"\s*- ", self.cur):
            return  # keep a pending list marker so <li><p>text</p></li> stays on one line
        line = self.cur.rstrip()
        if line.strip():
            self.lines.append("> " * self.quote + line.strip())
        elif self.lines and self.lines[-1] != "":
            self.lines.append("")
        self.cur = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.skip or tag in self.SKIP or "meta" in (a.get("class") or "").split():
            # count nesting while inside a skipped element (lightbox metadata, svg, scripts)
            if tag not in self.VOID:
                self.skip += 1
            return
        if tag == "blockquote":
            self._flush()
            self.quote += 1
        elif tag in self.BLOCK:
            self._flush()
            if tag == "li":
                self.cur = "  " * max(self.list_depth - 1, 0) + "- "
                self.li_pending = True
            if tag in ("ul", "ol"):
                self.list_depth += 1
            if tag == "tr":
                self.cell = 0
        elif tag == "br":
            self._flush()
        elif tag in ("td", "th"):
            if self.cell:
                self.cur = self.cur.rstrip() + " | "
            self.cell += 1
        elif tag == "a":
            self.links.append((a.get("href") or "", len(self.cur)))
        elif tag == "img":
            alt = a.get("alt") or "image"
            self.cur += f"[{alt}]"

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in self.VOID:
                self.skip -= 1
            return
        if tag == "blockquote":
            self._flush()
            self.quote = max(self.quote - 1, 0)
        elif tag in self.BLOCK:
            if tag in ("ul", "ol"):
                self.list_depth = max(self.list_depth - 1, 0)
            self._flush()
        elif tag == "a" and self.links:
            href, start = self.links.pop()
            text = self.cur[start:].strip()
            if href and not href.startswith("#") and not href.startswith("mailto:"):
                url = urllib.parse.urljoin(self.base + "/", href)
                if text != url and text not in (href, url.rstrip("/")):
                    self.cur += f" ({url})"

    def handle_data(self, data):
        if self.skip:
            return
        text = re.sub(r"\s+", " ", data)
        if not self.cur or self.cur.endswith(" "):
            text = text.lstrip()
        if text:
            self.li_pending = False
        self.cur += text

    def text(self):
        self._flush()
        out = "\n".join(self.lines).strip()
        return re.sub(r"\n{3,}", "\n\n", out)


def html_to_text(fragment, base=""):
    parser = _TextExtractor(base)
    try:
        parser.feed(fragment or "")
        parser.close()
    except Exception:
        # malformed markup: fall back to tag stripping
        return clean_text(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip())
    return clean_text(parser.text())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_forums(value):
    names = [n.strip().lower() for n in (value or "").split(",") if n.strip()]
    if not names:
        raise ValueError("empty --forums list")
    bad = [n for n in names if n not in FORUMS]
    if bad:
        raise ValueError(f"unknown forum(s) {bad} (known: {', '.join(FORUMS)})")
    return list(dict.fromkeys(names))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Search the governance forums in references/forums/ or dump a thread.")
    ap.add_argument("terms", nargs="*", help="search terms (ticker, issuer, product name)")
    ap.add_argument("--forums", help="comma list of forum names (default: all)")
    ap.add_argument("--all-terms", action="store_true",
                    help="one query that must match all terms (default: one query per term)")
    ap.add_argument("--curators", action="store_true",
                    help="one query per curator in each forum's file: all terms plus @<curator>")
    ap.add_argument("--list-forums", action="store_true",
                    help="print the forums, their URLs and curator handles, then exit")
    ap.add_argument("--max-pages", type=int, default=2, help="result pages per query (default 2)")
    ap.add_argument("--thread", help="topic URL, /t/... path or numeric id (with --forum)")
    ap.add_argument("--forum", help="forum name for --thread with a bare id or path")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args(argv)
    try:
        use_forums()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.list_forums:
        if args.terms or args.thread:
            print("error: --list-forums takes no search terms or --thread", file=sys.stderr)
            return 2
        rows = [{"forum": n, "base_url": b, "curators": CURATORS[n]} for n, b in FORUMS.items()]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                print(f"{r['forum']} | {r['base_url']} | curators: {', '.join(r['curators']) or '-'}")
        return 0

    if args.thread:
        if args.terms:
            print("error: give either search terms or --thread, not both", file=sys.stderr)
            return 2
        try:
            forum, tid = parse_thread_ref(args.thread, args.forum)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        try:
            thread = fetch_thread(forum, tid)
        except FetchError as e:
            print(f"error: {forum}: {e}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(thread, indent=2, ensure_ascii=False))
        else:
            print_thread(thread)
        return 0

    if args.max_pages < 1:
        print("error: --max-pages must be >= 1", file=sys.stderr)
        return 2
    msg = validate_terms(args.terms)
    if msg:
        print(f"error: {msg}", file=sys.stderr)
        return 2
    try:
        forums = parse_forums(args.forums) if args.forums is not None else list(FORUMS)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    skipped = [f for f in forums if not forum_queries(args.terms, f, args.all_terms, args.curators)]
    if len(skipped) == len(forums):
        print("error: none of the selected forums lists a curator in its file", file=sys.stderr)
        return 2
    if skipped:
        print(f"note: no curators listed for {', '.join(skipped)}; not searched", file=sys.stderr)

    results, errors, forum_ok = run_search(args.terms, forums, args.all_terms, args.max_pages,
                                           args.curators)
    for e in errors:
        print(f"warning: {e['forum']} [{e['query']}]: {e['kind']}: {e['error']}", file=sys.stderr)
    all_failed = not any(forum_ok.values())

    if args.json:
        print(json.dumps({"results": results, "errors": errors,
                          "forums_ok": [f for f, ok in forum_ok.items() if ok],
                          "forums_failed": [f for f, ok in forum_ok.items() if not ok],
                          "forums_skipped": skipped},
                         indent=2, ensure_ascii=False))
    else:
        if all_failed:
            print("error: every forum failed; no results", file=sys.stderr)
        else:
            print_results(results, forum_ok)
    return 1 if all_failed else 0


def print_results(results, forum_ok):
    failed = [f for f, ok in forum_ok.items() if not ok]
    print(f"{len(results)} result(s)" + (f"  (failed: {', '.join(failed)})" if failed else ""))
    for t in results:
        print(f"{t['forum']:6} | {t['title']} | {t['url']} | created {t['created_at'] or '?'}"
              f" | last {t['last_posted_at'] or '?'} | {t['posts_count'] if t['posts_count'] is not None else '?'} posts"
              f" | matched: {', '.join(t['matched'])}")
        if t.get("blurb"):
            print(f"         {t['blurb']}")


def print_thread(thread):
    print(f"# {thread['title']}")
    print(f"{thread['url']}  ({thread['forum']}, created {thread['created_at'] or '?'})")
    note = f"{len(thread['posts'])} post(s) shown of {thread['posts_total']}"
    if thread["posts_skipped"]:
        note += f"; {thread['posts_skipped']} deleted/hidden/empty skipped"
    if thread["posts_unretrieved"]:
        note += f"; {thread['posts_unretrieved']} could not be retrieved"
    print(note)
    for p in thread["posts"]:
        reply = f" (reply to #{p['reply_to']})" if p["reply_to"] else ""
        print(f"\n--- #{p['post_number']} | {p['username']} | {p['created_at']}{reply} | {p['url']}")
        print(p["text"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # output piped into head/less that exited early
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
