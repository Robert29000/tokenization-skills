import contextlib
import io
import json
import os
import socket
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

from helpers import (FakeOpener, FakeResponse, fixture_path, http_error, json_response,
                     load_script, read_fixture)

fs = load_script("forum_search")
# the tests use their own forum files, so adding or removing a real forum never breaks them
FIXTURE_FORUMS = fixture_path("forums")


def topic(tid, title="T", last="2026-01-01T00:00:00Z", slug=None):
    return {"id": tid, "title": title, "slug": slug or f"topic-{tid}", "posts_count": 3,
            "created_at": "2025-12-01T00:00:00Z", "last_posted_at": last}


def search_page(topics, more=False, posts=None):
    return {"topics": topics, "posts": posts or [],
            "grouped_search_result": {"more_full_page_results": more}}


def host_of(name):
    return urllib.parse.urlparse(fs.FORUMS[name]).netloc


def on(name, needle=""):
    return lambda url: host_of(name) in url and needle in url


class Base(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        forums, curators = fs.load_forums(FIXTURE_FORUMS)
        for attr, value in (("_sleep", self.sleeps.append), ("_throttle", lambda url: None),
                            ("FORUMS_DIR", FIXTURE_FORUMS), ("FORUMS", forums),
                            ("CURATORS", curators)):
            p = mock.patch.object(fs, attr, value)
            p.start()
            self.addCleanup(p.stop)

    def use(self, opener):
        p = mock.patch.object(fs.urllib.request, "urlopen", opener)
        p.start()
        self.addCleanup(p.stop)
        return opener

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fs.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class QueryTests(Base):
    def test_special_characters_are_kept_and_phrases_quoted(self):
        self.assertEqual(fs.build_query(["mF-ONE", "sBUIDL"], False), ["mF-ONE", "sBUIDL"])
        self.assertEqual(fs.build_query(['Janus  "Henderson" AAA'], False), ['"Janus Henderson AAA"'])
        self.assertEqual(fs.build_query(["OUSG", "Ondo Finance"], True), ['OUSG "Ondo Finance"'])
        self.assertEqual(fs.build_query(["", "  ", "USDY"], False), ["USDY"])

    def test_short_and_empty_terms_rejected(self):
        self.assertIn("shorter than", fs.validate_terms(["mT"]))
        self.assertIn("no search terms", fs.validate_terms([]))
        self.assertIn("no search terms", fs.validate_terms(['""', " "]))
        self.assertIsNone(fs.validate_terms(["USTB", "Société Générale"]))

    def test_short_term_exit_code_2(self):
        code, _, err = self.run_main("ab")
        self.assertEqual(code, 2)
        self.assertIn("shorter than", err)

    def test_unknown_forum_rejected(self):
        code, _, err = self.run_main("USTB", "--forums", "aave,compound")
        self.assertEqual(code, 2)
        self.assertIn("compound", err)
        code, _, _ = self.run_main("USTB", "--forums", " , ")
        self.assertEqual(code, 2)

    def test_terms_and_thread_are_exclusive(self):
        code, _, err = self.run_main("USTB", "--thread", "123", "--forum", "aave")
        self.assertEqual(code, 2)

    def test_url_encoding_of_unicode_and_symbols(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(search_page([])))]))
        fs.run_search(["mF-ONE", "Ondo – USDY & co"], ["aave"], False, 1)
        urls = opener.urls()
        self.assertEqual(len(urls), 2)
        for u in urls:
            self.assertNotIn(" ", u)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(urls[1]).query)["q"][0]
        self.assertEqual(q, '"Ondo – USDY & co"')


class SearchTests(Base):
    def test_pagination_follows_more_results_and_dedupes(self):
        opener = self.use(FakeOpener([
            (on("aave", "page=2"), json_response(search_page([topic(2), topic(3)], more=True))),
            (on("aave", "page=3"), json_response(search_page([topic(4)], more=True))),
            (on("aave"), json_response(search_page([topic(1), topic(2)], more=True))),
        ]))
        topics = fs.search_forum("aave", "USTB", max_pages=2)
        self.assertEqual(sorted(t["topic_id"] for t in topics), [1, 2, 3])
        self.assertEqual(len(opener.calls), 2)  # page 3 never requested

    def test_pagination_stops_when_no_more(self):
        opener = self.use(FakeOpener([(on("aave"), json_response(search_page([topic(1)], more=False)))]))
        fs.search_forum("aave", "USTB", max_pages=5)
        self.assertEqual(len(opener.calls), 1)

    def test_dedupe_across_terms_and_ranking(self):
        self.use(FakeOpener([
            (on("aave", "q=USTB"), json_response(search_page([topic(1, last="2026-01-01"), topic(2, last="2026-05-01")]))),
            (on("aave", "q=Superstate"), json_response(search_page([topic(1, last="2026-01-01")]))),
            (on("morpho"), json_response(search_page([topic(1, title="Morpho one")]))),
        ]))
        results, errors, ok = fs.run_search(["USTB", "Superstate"], ["aave", "morpho"], False, 1)
        self.assertEqual(errors, [])
        keys = [(r["forum"], r["topic_id"]) for r in results]
        # same id on two forums is two different threads; topic 1 on aave matched both terms -> first
        self.assertEqual(keys, [("aave", 1), ("aave", 2), ("morpho", 1)])
        self.assertEqual(results[0]["matched"], ["USTB", "Superstate"])

    def test_one_forum_down_others_continue(self):
        self.use(FakeOpener([
            (on("aave"), json_response(search_page([topic(1)]))),
            (on("morpho"), http_error("u", 503)),
            (on("euler"), socket.timeout("timed out")),
            (on("fluid"), json_response(search_page([]))),
        ]))
        code, out, err = self.run_main("USTB")
        self.assertEqual(code, 0)
        self.assertIn("1 result(s)", out)
        self.assertIn("failed: euler, morpho", out)   # forums in file-name order
        self.assertIn("morpho", err)
        self.assertIn("timeout", err)
        self.assertEqual(len(self.sleeps), 2 * fs.RETRIES)  # retried 5xx and timeout

    def test_all_forums_fail_exit_1(self):
        self.use(FakeOpener([(lambda u: True, http_error("u", 500))]))
        code, out, err = self.run_main("USTB", "--json")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["forums_ok"], [])
        self.assertEqual(len(data["forums_failed"]), 4)

    def test_zero_results_is_success(self):
        self.use(FakeOpener([(lambda u: True, json_response({}))]))  # missing keys entirely
        code, out, _ = self.run_main("NOTHINGHERE")
        self.assertEqual(code, 0)
        self.assertIn("0 result(s)", out)

    def test_null_and_garbage_entries_tolerated(self):
        self.use(FakeOpener([(lambda u: True, json_response(
            {"topics": [None and {}, {"title": "no id"}, topic(7)], "posts": None,
             "grouped_search_result": None}))]))
        topics = fs.search_forum("aave", "USTB", 2)
        self.assertEqual([t["topic_id"] for t in topics], [7])

    def test_blurb_attached_and_cleaned(self):
        self.use(FakeOpener([(lambda u: True, json_response(search_page(
            [topic(5)], posts=[{"topic_id": 5, "blurb": "<span class='x'>LlamaRisk</span> &amp; more\n text"}])))]))
        t = fs.search_forum("aave", "USTB", 1)[0]
        self.assertEqual(t["blurb"], "LlamaRisk & more text")


class HttpTests(Base):
    def test_429_retry_after_respected_and_capped(self):
        opener = self.use(FakeOpener([(lambda u: True, [
            http_error("u", 429, headers={"Retry-After": "5"}),
            http_error("u", 429, headers={"Retry-After": "9999"}),
            json_response({"ok": 1})])]))
        self.assertEqual(fs.fetch_json("https://x/search.json"), {"ok": 1})
        self.assertEqual(self.sleeps, [5.0, fs.MAX_RETRY_AFTER])
        self.assertEqual(len(opener.calls), 3)

    def test_429_has_larger_retry_budget_than_5xx(self):
        n = fs.RATE_LIMIT_RETRIES
        opener = self.use(FakeOpener([(lambda u: True, [http_error("u", 429)] * n + [json_response({"ok": 1})])]))
        self.assertEqual(fs.fetch_json("https://x"), {"ok": 1})
        self.assertEqual(len(opener.calls), n + 1)
        self.assertTrue(all(s <= fs.MAX_RETRY_AFTER for s in self.sleeps))
        opener = self.use(FakeOpener([(lambda u: True, http_error("u", 429))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertIn("rate limited", str(cm.exception))
        self.assertEqual(len(opener.calls), n + 1)

    def test_mixed_errors_use_separate_budgets(self):
        seq = [http_error("u", 503)] * fs.RETRIES + [http_error("u", 429)] * 2 + [json_response({"ok": 2})]
        self.use(FakeOpener([(lambda u: True, seq)]))
        self.assertEqual(fs.fetch_json("https://x"), {"ok": 2})

    def test_html_challenge_with_200_is_blocked(self):
        page = read_fixture("forum", "challenge.html")
        self.use(FakeOpener([(lambda u: True, FakeResponse(page, "text/html"))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x/search.json")
        self.assertEqual(cm.exception.kind, "blocked")
        self.assertIn("challenge", str(cm.exception))
        self.assertEqual(self.sleeps, [])  # no pointless retries

    def test_403_html_is_blocked_not_retried(self):
        self.use(FakeOpener([(lambda u: True, http_error("u", 403, b"<!DOCTYPE html><html>no</html>"))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "blocked")
        self.assertEqual(self.sleeps, [])

    def test_oversized_response_rejected_not_retried(self):
        opener = self.use(FakeOpener([(lambda u: True, FakeResponse(b"x" * 11))]))
        with mock.patch.object(fs, "MAX_BYTES", 10):
            with self.assertRaises(fs.FetchError) as cm:
                fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "too_large")
        self.assertEqual(len(opener.calls), 1)
        self.use(FakeOpener([(lambda u: True, FakeResponse(b"[1]"))]))
        with mock.patch.object(fs, "MAX_BYTES", 3):
            self.assertEqual(fs.fetch_json("https://x"), [1])     # exactly at the limit is fine

    def test_malformed_json(self):
        self.use(FakeOpener([(lambda u: True, FakeResponse(b'{"topics": [', "application/json"))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "bad_json")

    def test_discourse_error_payload(self):
        body = json.dumps({"errors": ["You supplied invalid parameters to the request: q"]}).encode()
        self.use(FakeOpener([(lambda u: True, http_error("u", 400, body))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "api")
        self.assertIn("invalid parameters", str(cm.exception))

    def test_error_payload_with_200(self):
        self.use(FakeOpener([(lambda u: True, json_response({"errors": ["rate limited"]}))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "api")

    def test_network_error_retried_then_raised(self):
        opener = self.use(FakeOpener([(lambda u: True, urllib.error.URLError("dns failure"))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "network")
        self.assertEqual(len(opener.calls), fs.RETRIES + 1)

    def test_timeout_wrapped_in_urlerror(self):
        self.use(FakeOpener([(lambda u: True, urllib.error.URLError(socket.timeout("t")))]))
        with self.assertRaises(fs.FetchError) as cm:
            fs.fetch_json("https://x")
        self.assertEqual(cm.exception.kind, "timeout")

    def test_404_not_retried(self):
        opener = self.use(FakeOpener([(lambda u: True, http_error("u", 404, b""))]))
        with self.assertRaises(fs.FetchError):
            fs.fetch_json("https://x")
        self.assertEqual(len(opener.calls), 1)


class ThreadRefTests(Base):
    def test_accepted_forms(self):
        cases = {
            "https://governance.aave.com/t/arfc-onboard-mwin/25536": ("aave", 25536),
            "https://governance.aave.com/t/25536": ("aave", 25536),
            "https://governance.aave.com/t/arfc-onboard-mwin/25536/8": ("aave", 25536),
            "https://governance.aave.com/t/arfc-onboard-mwin/25536.json": ("aave", 25536),
            "https://governance.aave.com/t/25536.json?print=true#post_3": ("aave", 25536),
            "https://www.forum.morpho.org/t/some-vault/375/": ("morpho", 375),
            "forum.euler.finance/t/x/1467": ("euler", 1467),
            "HTTPS://GOV.FLUID.IO/t/x/12": ("fluid", 12),
        }
        for ref, expected in cases.items():
            self.assertEqual(fs.parse_thread_ref(ref), expected, ref)
        self.assertEqual(fs.parse_thread_ref("25536", "Aave"), ("aave", 25536))
        self.assertEqual(fs.parse_thread_ref("/t/slug/77", "euler"), ("euler", 77))

    def test_rejected_forms(self):
        bad = [
            ("25536", None),                                  # bare id without forum
            ("/t/slug/77", None),                             # path without forum
            ("https://forum.example.com/t/x/1", None),        # unknown host
            ("https://governance.aave.com/c/risk/12", None),  # category, not topic
            ("https://governance.aave.com/t/slug", None),     # no id
            ("", None),
            ("123", "compound"),                              # unknown forum
            ("https://governance.aave.com/t/x/1", "morpho"),  # contradiction
        ]
        for ref, forum in bad:
            with self.assertRaises(ValueError, msg=ref):
                fs.parse_thread_ref(ref, forum)


class ThreadTests(Base):
    def test_long_thread_fetches_missing_posts_and_skips_deleted(self):
        topic_json = json.loads(read_fixture("forum", "topic_long.json"))
        extra_json = json.loads(read_fixture("forum", "topic_long_posts.json"))
        opener = self.use(FakeOpener([
            (on("aave", "/posts.json"), json_response(extra_json)),
            (on("aave", "/t/900.json"), json_response(topic_json)),
        ]))
        thread = fs.fetch_thread("aave", 900)
        posts_url = [u for u in opener.urls() if "posts.json" in u][0]
        ids = urllib.parse.parse_qs(urllib.parse.urlparse(posts_url).query)["post_ids[]"]
        self.assertEqual(ids, ["1021", "1022", "1023", "1024"])
        numbers = [p["post_number"] for p in thread["posts"]]
        self.assertEqual(numbers, sorted(numbers))
        self.assertNotIn(2, numbers)    # deleted
        self.assertNotIn(3, numbers)    # hidden
        self.assertNotIn(4, numbers)    # empty cooked
        self.assertIn(23, numbers)      # fetched via posts.json
        self.assertEqual(thread["posts_skipped"], 3)
        self.assertEqual(thread["posts_unretrieved"], 1)  # id 1024 never returned
        self.assertEqual(thread["posts_total"], 24)
        p5 = next(p for p in thread["posts"] if p["post_number"] == 5)
        self.assertNotRegex(json.dumps(thread), r"\\u001b")
        self.assertEqual(p5["url"], "https://governance.aave.com/t/arfc-onboard-extb/900/5")

    def test_many_missing_posts_are_chunked(self):
        stream = list(range(1, 46))
        loaded = [{"id": i, "post_number": i, "cooked": f"<p>p{i}</p>", "username": "u"} for i in range(1, 21)]
        topic_json = {"title": "Big", "slug": "big", "post_stream": {"posts": loaded, "stream": stream}}

        def posts_for(url):
            ids = [int(x) for x in urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["post_ids[]"]]
            return json_response({"post_stream": {"posts": [
                {"id": i, "post_number": i, "cooked": f"<p>p{i}</p>", "username": "u"} for i in ids]}})

        class Opener(FakeOpener):
            def __call__(self, req, timeout=None):
                url = req.full_url
                self.calls.append((url, {}))
                return posts_for(url) if "posts.json" in url else json_response(topic_json)

        opener = self.use(Opener([]))
        thread = fs.fetch_thread("aave", 5)
        self.assertEqual(len([u for u in opener.urls() if "posts.json" in u]), 2)  # 25 ids -> 20 + 5
        self.assertEqual(len(thread["posts"]), 45)

    def test_thread_title_and_username_cleaned(self):
        post = {"id": 1, "post_number": 1, "username": "eve\x1b[8m", "cooked": "<p>hi</p>",
                "created_at": "2026-01-01T00:00:00Z"}
        self.use(FakeOpener([(on("aave", "/t/7.json"), json_response(
            {"title": "ARFC \u202eLISTING\x07", "slug": "s", "post_stream": {"posts": [post], "stream": [1]}}))]))
        thread = fs.fetch_thread("aave", 7)
        self.assertEqual(thread["title"], "ARFC LISTING")
        self.assertEqual(thread["posts"][0]["username"], "eve[8m")
        self.use(FakeOpener([(on("aave", "search.json"), json_response(search_page([topic(5, title="Bad\x1b]0;x\x07")])))]))
        results, _, _ = fs.run_search(["mTBILL"], ["aave"], False, 1)
        self.assertEqual(results[0]["title"], "Bad]0;x")

    def test_thread_cli_text_and_failure(self):
        self.use(FakeOpener([(on("aave"), json_response(json.loads(read_fixture("forum", "topic_long.json")))),
                             ]))
        with mock.patch.object(fs, "fetch_thread", side_effect=fs.FetchError("http", "HTTP 404", 404)):
            code, _, err = self.run_main("--thread", "1", "--forum", "aave")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 404", err)
        code, _, err = self.run_main("--thread", "https://evil.example/t/x/1")
        self.assertEqual(code, 2)

    def test_topic_missing_post_stream(self):
        self.use(FakeOpener([(lambda u: True, json_response({"title": "Empty"}))]))
        thread = fs.fetch_thread("aave", 1)
        self.assertEqual(thread["posts"], [])
        self.assertEqual(thread["posts_total"], 0)


class HtmlToTextTests(unittest.TestCase):
    BASE = "https://governance.aave.com"

    def test_links_quotes_tables_lists(self):
        cooked = read_fixture("forum", "cooked_post.html")
        text = fs.html_to_text(cooked, self.BASE)
        self.assertIn("Final Terms (https://example.com/final-terms.pdf)", text)
        self.assertIn("earlier post (https://governance.aave.com/t/x/1/3)", text)
        self.assertIn("https://etherscan.io/address/0xabc", text)      # bare link text == url: not doubled
        self.assertNotIn("https://etherscan.io/address/0xabc (https://etherscan.io/address/0xabc)", text)
        self.assertIn("> The notes rank subordinate", text)
        self.assertIn("Parameter | Value", text)
        self.assertIn("LTV | 67%", text)
        self.assertIn("- Institutional manager: Wellington", text)
        self.assertNotIn("1920×1080", text)                            # lightbox meta skipped
        self.assertNotIn("alert(", text)

    def test_control_and_bidi_characters_stripped(self):
        cooked = "<p>LTV \x1b[2J\x1b]0;title\x07is 67%\u202e evil\u2066</p><p>caf\u00e9 \u00a0ok\tend</p>"
        text = fs.html_to_text(cooked, self.BASE)
        self.assertNotRegex(text, "[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")
        self.assertIn("LTV [2J]0;titleis 67% evil", text)   # escape bytes gone, visible text kept
        self.assertIn("caf\u00e9", text)                          # ordinary non-ASCII kept
        self.assertIn("\n", fs.html_to_text("<p>a</p><p>b</p>"))  # newlines survive
        self.assertEqual(fs.html_to_text("<p>a\x1b[31m<b>", self.BASE), "a[31m")   # malformed path too
        self.assertEqual(fs.clean_text(None), "")

    def test_malformed_and_empty(self):
        self.assertEqual(fs.html_to_text("", self.BASE), "")
        text = fs.html_to_text("<p>Unclosed <b>bold <a href='/t/1'>link", self.BASE)
        self.assertIn("Unclosed bold link", text)
        self.assertEqual(fs.html_to_text("<p>&amp; &lt;tag&gt; &#8364;</p>"), "& <tag> €")


def front(base_url="https://forum.example.org", engine="discourse", extra=""):
    return f"---\nbase_url: {base_url}\nengine: {engine}\n{extra}---\n\n# Forum\n"


class ForumFileTests(Base):
    def write_forums(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = tmp.name
        for name, text in files.items():
            with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        return folder

    def test_real_forum_files_load(self):
        forums, curators = fs.load_forums(os.path.join(fs.SKILL_DIR, "references", "forums"))
        self.assertTrue(forums)
        self.assertEqual(set(forums), set(curators))
        for name, base in forums.items():
            self.assertRegex(base, r"^https://[a-z0-9.-]+$", name)

    def test_fixture_forums_load(self):
        forums, curators = fs.load_forums(FIXTURE_FORUMS)
        self.assertEqual(list(forums), ["aave", "euler", "fluid", "morpho"])
        self.assertEqual(forums["aave"], "https://governance.aave.com")
        self.assertEqual(curators["morpho"], ["LlamaRisk", "steakhouse"])
        self.assertEqual(curators["euler"], [])

    def test_base_url_and_curators_normalised(self):
        folder = self.write_forums({"x.md": front("https://Forum.Example.org/",
                                                  extra="curators: @Alice, bob.k , Alice\n"),
                                    "README.txt": "not a forum file"})
        forums, curators = fs.load_forums(folder)
        self.assertEqual(forums, {"x": "https://forum.example.org"})
        self.assertEqual(curators, {"x": ["Alice", "bob.k"]})

    def test_invalid_forum_files_rejected(self):
        cases = {
            "no front matter": ({"x.md": "# Forum\n"}, "no front matter"),
            "unknown key": ({"x.md": front(extra="default: true\n")}, "unknown front-matter line"),
            "repeated key": ({"x.md": front(extra="engine: discourse\n")}, "given twice"),
            "http": ({"x.md": front("http://forum.example.org")}, "base_url"),
            "path": ({"x.md": front("https://example.org/forum")}, "base_url"),
            "port": ({"x.md": front("https://forum.example.org:8443")}, "base_url"),
            "no base_url": ({"x.md": "---\nengine: discourse\n---\n"}, "base_url"),
            "engine": ({"x.md": front(engine="flarum")}, "not supported"),
            "no engine": ({"x.md": "---\nbase_url: https://f.example.org\n---\n"}, "not supported"),
            "curator": ({"x.md": front(extra="curators: Llama Risk\n")}, "usernames"),
            "file name": ({"Bad_Name.md": front()}, "file name"),
            "same host": ({"a.md": front("https://forum.example.org"),
                           "b.md": front("https://www.forum.example.org")}, "already the forum 'a'"),
            "empty": ({}, "no forum files"),
        }
        for label, (files, needle) in cases.items():
            with self.subTest(label), self.assertRaises(ValueError) as ctx:
                fs.load_forums(self.write_forums(files))
            self.assertIn(needle, str(ctx.exception), label)

    def test_invalid_forum_files_exit_1(self):
        folder = self.write_forums({"x.md": front(engine="flarum")})
        with mock.patch.object(fs, "FORUMS_DIR", folder):
            code, _, err = self.run_main("USTB")
        self.assertEqual(code, 1)
        self.assertIn("references/forums/x.md", err)

    def test_new_forum_file_is_searched_and_threads_resolve(self):
        folder = self.write_forums({"newdao.md": front("https://gov.newdao.example")})
        opener = self.use(FakeOpener([(lambda u: True, json_response(search_page([topic(1)])))]))
        with mock.patch.object(fs, "FORUMS_DIR", folder):
            code, out, _ = self.run_main("USTB")
        self.assertEqual(code, 0)
        self.assertTrue(opener.urls()[0].startswith("https://gov.newdao.example/search.json"))
        self.assertIn("https://gov.newdao.example/t/topic-1/1", out)
        self.assertEqual(fs.parse_thread_ref("https://www.gov.newdao.example/t/x/5"), ("newdao", 5))

    def test_list_forums(self):
        code, out, _ = self.run_main("--list-forums")
        self.assertEqual(code, 0)
        self.assertIn("aave | https://governance.aave.com | curators: LlamaRisk", out)
        self.assertIn("euler | https://forum.euler.finance | curators: -", out)
        code, out, _ = self.run_main("--list-forums", "--json")
        self.assertEqual([r["forum"] for r in json.loads(out)], ["aave", "euler", "fluid", "morpho"])
        code, _, _ = self.run_main("--list-forums", "USTB")
        self.assertEqual(code, 2)


class CuratorTests(Base):
    def test_one_query_per_curator_and_forums_without_curators_skipped(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(search_page([])))]))
        code, out, err = self.run_main("JAAA", "--curators", "--json")
        self.assertEqual(code, 0, err)
        queries = sorted((urllib.parse.urlparse(u).netloc,
                          urllib.parse.parse_qs(urllib.parse.urlparse(u).query)["q"][0])
                         for u in opener.urls())
        self.assertEqual(queries, [("forum.morpho.org", "JAAA @LlamaRisk"),
                                   ("forum.morpho.org", "JAAA @steakhouse"),
                                   ("governance.aave.com", "JAAA @LlamaRisk")])
        data = json.loads(out)
        self.assertEqual(data["forums_skipped"], ["euler", "fluid"])
        self.assertEqual(data["forums_failed"], [])
        self.assertIn("no curators listed for euler, fluid", err)

    def test_no_curators_in_selected_forums_exit_2(self):
        code, _, err = self.run_main("JAAA", "--curators", "--forums", "euler,fluid")
        self.assertEqual(code, 2)
        self.assertIn("lists a curator", err)

    def test_curators_with_several_terms(self):
        self.assertEqual(fs.forum_queries(["JAAA", "Janus Henderson"], "aave", False, True),
                         ['JAAA "Janus Henderson" @LlamaRisk'])
        self.assertEqual(fs.forum_queries(["JAAA"], "euler", False, True), [])


if __name__ == "__main__":
    unittest.main()


class ThrottleTests(unittest.TestCase):
    def test_spacing_is_per_host(self):
        sleeps = []
        with mock.patch.object(fs, "_sleep", sleeps.append), \
                mock.patch.object(fs, "_last_request", {}), \
                mock.patch.object(fs.time, "monotonic", side_effect=[10.0, 10.0, 10.2, 10.2]):
            fs._throttle("https://governance.aave.com/search.json?q=a")   # first aave: no wait
            fs._throttle("https://forum.morpho.org/search.json?q=a")      # first morpho: no wait
            fs._throttle("https://governance.aave.com/search.json?q=b")   # 0.2 s after aave -> wait
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], fs.MIN_INTERVAL - 0.2)
