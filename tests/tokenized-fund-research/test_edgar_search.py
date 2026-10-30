import contextlib
import io
import json
import os
import shutil
import socket
import tempfile
import unittest
import urllib.parse
from unittest import mock

from helpers import FakeOpener, FakeResponse, http_error, json_response, load_script, read_fixture

ed = load_script("edgar_search")
UA = "Jane Analyst jane@example.com"


def fixture(name):
    return json.loads(read_fixture("edgar", name))


class Base(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        for target, value in ((ed, {"_sleep": self.sleeps.append}),):
            for attr, v in value.items():
                p = mock.patch.object(target, attr, v)
                p.start()
                self.addCleanup(p.stop)
        env = mock.patch.dict(os.environ, {"SEC_USER_AGENT": UA})
        env.start()
        self.addCleanup(env.stop)

    def use(self, opener):
        p = mock.patch.object(ed.urllib.request, "urlopen", opener)
        p.start()
        self.addCleanup(p.stop)
        return opener

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ed.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class UserAgentTests(Base):
    def test_missing_user_agent_exits_2_without_request(self):
        opener = self.use(FakeOpener([]))
        for value in (None, "", "   "):
            with mock.patch.dict(os.environ, {}, clear=True):
                if value is not None:
                    os.environ["SEC_USER_AGENT"] = value
                code, _, err = self.run_main("BlackRock")
            self.assertEqual(code, 2)
            self.assertIn("SEC_USER_AGENT", err)
        self.assertEqual(opener.calls, [])

    def test_user_agent_without_email_warns_and_is_sent(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(fixture("empty.json")))]))
        with mock.patch.dict(os.environ, {"SEC_USER_AGENT": "Jane Analyst"}):
            code, _, err = self.run_main("BlackRock")
        self.assertEqual(code, 0)
        self.assertIn("no email", err)
        self.assertEqual(opener.calls[0][1].get("User-agent"), "Jane Analyst")


    def write_ua(self, text, mode="w"):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, ".sec-user-agent")
        with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
            fh.write(text)
        return path

    def test_user_agent_file_used_when_env_unset(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(fixture("empty.json")))]))
        path = self.write_ua("\n  Jane Analyst jane@example.com  \r\n\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            code, _, err = self.run_main("BlackRock", "--user-agent-file", path)
        self.assertEqual(code, 0, err)
        self.assertEqual(opener.calls[0][1].get("User-agent"), UA)

    def test_env_wins_over_file(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(fixture("empty.json")))]))
        path = self.write_ua("File Person file@example.com")
        code, _, _ = self.run_main("BlackRock", "--user-agent-file", path)
        self.assertEqual((code, opener.calls[0][1].get("User-agent")), (0, UA))

    def test_bad_user_agent_file_exits_2_without_request(self):
        opener = self.use(FakeOpener([]))
        cases = {
            "missing": os.path.join(tempfile.gettempdir(), "no-such-dir-xyz", ".sec-user-agent"),
            "empty": self.write_ua(""),
            "blank": self.write_ua(" \n\t\n"),
            "two lines": self.write_ua("Jane jane@example.com\nX-Evil: 1\n"),
            "too long": self.write_ua("J" * 2000 + " j@example.com"),
            "control": self.write_ua("Jane\x00 jane@example.com"),
            "not utf-8": self.write_ua(b"\xff\xfe Jane", "wb"),
        }
        cases["directory"] = os.path.dirname(cases["empty"])
        with mock.patch.dict(os.environ, {}, clear=True):
            for label, path in cases.items():
                code, _, err = self.run_main("BlackRock", "--user-agent-file", path)
                self.assertEqual(code, 2, label)
                self.assertIn("error:", err, label)
        self.assertEqual(opener.calls, [])

    def test_control_characters_in_env_rejected(self):
        opener = self.use(FakeOpener([]))
        for value in ("Jane jane@example.com\r\nX-Evil: 1", "Jane\x1b jane@example.com"):
            with mock.patch.dict(os.environ, {"SEC_USER_AGENT": value}):
                code, _, err = self.run_main("BlackRock")
            self.assertEqual((code, "control characters" in err), (2, True), repr(value))
        self.assertEqual(opener.calls, [])

    def test_oversized_response_rejected_not_retried(self):
        opener = self.use(FakeOpener([(lambda u: True, FakeResponse(b"x" * 11))]))
        with mock.patch.object(ed, "MAX_BYTES", 10):
            code, _, err = self.run_main("BlackRock")
        self.assertEqual((code, "larger than 10 bytes" in err, len(opener.calls)), (1, True, 1))


class ArgumentTests(Base):
    def test_parse_forms(self):
        self.assertEqual(ed.parse_forms("d, n-1a ,D"), ["D", "N-1A"])
        self.assertEqual(ed.parse_forms("D,D/A"), ["D"])          # efts quirk handled
        self.assertEqual(ed.parse_forms("D/A"), ["D/A"])          # alone is fine
        self.assertEqual(ed.parse_forms("13F-HR,10-K"), ["13F-HR", "10-K"])
        self.assertEqual(ed.parse_forms(None), [])
        for bad in (",", "D;DROP", "D A", "-D", "X" * 30):
            with self.assertRaises(ValueError, msg=bad):
                ed.parse_forms(bad)

    def test_bad_arguments_exit_2(self):
        self.use(FakeOpener([]))
        for argv in (["X", "--forms", "D;x"], ['""'], ["  "], ["X", "--from-date", "2024/01/01"],
                     ["X", "--max-results", "0"]):
            code, _, _ = self.run_main(*argv)
            self.assertEqual(code, 2, argv)

    def test_build_query_escaping(self):
        self.assertEqual(ed.build_query('Ondo "USDY"  LLC'), '"Ondo USDY LLC"')
        self.assertEqual(ed.build_query("Smith & Co., Ltd."), '"Smith & Co., Ltd."')
        self.assertEqual(ed.build_query('"already quoted"'), '"already quoted"')
        self.assertEqual(ed.build_query('a OR "b c"', raw=True), 'a OR "b c"')

    def test_request_is_url_encoded(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(fixture("empty.json")))]))
        self.run_main("Smith & Co., Ltd.", "--forms", "D,N-1A", "--from-date", "2024-01-01")
        url = opener.urls()[0]
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(qs["q"], ['"Smith & Co., Ltd."'])
        self.assertEqual(qs["forms"], ["D,N-1A"])
        self.assertEqual(qs["dateRange"], ["custom"])
        self.assertEqual(qs["startdt"], ["2024-01-01"])
        # efts ignores one-sided ranges, so the missing end is filled with today
        self.assertEqual(qs["enddt"], [ed.datetime.date.today().isoformat()])

    def test_only_end_date_fills_start(self):
        opener = self.use(FakeOpener([(lambda u: True, json_response(fixture("empty.json")))]))
        self.run_main("X", "--to-date", "2023-12-31")
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(opener.urls()[0]).query)
        self.assertEqual((qs["startdt"], qs["enddt"]), ([ed.EARLIEST_DATE], ["2023-12-31"]))

    def test_invalid_dates_rejected(self):
        self.use(FakeOpener([]))
        for argv in (["X", "--from-date", "2024-02-30"], ["X", "--to-date", "2024-13-01"],
                     ["X", "--from-date", "2025-01-01", "--to-date", "2024-01-01"]):
            code, _, _ = self.run_main(*argv)
            self.assertEqual(code, 2, argv)


class ResponseTests(Base):
    def test_no_hits(self):
        self.use(FakeOpener([(lambda u: True, json_response(fixture("empty.json")))]))
        code, out, _ = self.run_main("Nonexistent Fund", "--forms", "D")
        self.assertEqual(code, 0)
        self.assertIn('0 results for "Nonexistent Fund" (forms: D)', out)

    def test_grouping_name_match_first_and_multi_cik_names(self):
        self.use(FakeOpener([(lambda u: True, json_response(fixture("hits.json")))]))
        code, out, _ = self.run_main("BlackRock USD Institutional Digital Liquidity Fund", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        ents = data["entities"]
        self.assertEqual(ents[0]["cik"], "0002013810")
        self.assertTrue(ents[0]["name_match"])
        self.assertEqual(ents[0]["names"], ["BlackRock USD Institutional Digital Liquidity Fund Ltd."])
        self.assertEqual([f["file_date"] for f in ents[0]["filings"]], ["2026-07-27", "2024-03-18"])
        by_cik = {e["cik"]: e for e in ents}
        # names mapped by the CIK they contain, not by position
        self.assertEqual(by_cik["0001762096"]["names"], ["Securitize, Inc."])
        self.assertEqual(by_cik["0002094496"]["names"], ["Securitize Holdings, Inc."])
        self.assertTrue(all(not e["name_match"] for e in ents[1:]))

    def test_exemptions_only_for_form_d(self):
        self.use(FakeOpener([(lambda u: True, json_response(fixture("hits.json")))]))
        _, out, _ = self.run_main("x", "--json")
        filings = {f["adsh"]: f for e in json.loads(out)["entities"] for f in e["filings"]}
        bl = filings["0002014390-24-000001"]
        self.assertTrue(any("506(c)" in x for x in bl["exemptions"]))
        self.assertTrue(any("3(c)(7)" in x for x in bl["exemptions"]))
        self.assertEqual(bl["inc_states"], ["British Virgin Islands"])
        self.assertEqual(filings["0001213900-26-076444"]["exemptions"], [])     # 8-K items
        self.assertEqual(filings["0001213900-26-042685"]["inc_states"], ["Delaware"])  # deduped
        weird = filings["0000000000-25-000009"]
        self.assertIn("ICA §3(c)(5)", weird["exemptions"])
        self.assertIn("item ZZ", weird["exemptions"])
        self.assertEqual(weird["inc_states"], ["Cayman Islands"])

    def test_filing_url(self):
        f = ed.normalise_hit(fixture("hits.json")["hits"]["hits"][0])
        self.assertEqual(f["url"], "https://www.sec.gov/Archives/edgar/data/2013810/"
                                   "000201439024000001/primary_doc.xml")

    def test_text_output_marks_items_for_non_form_d(self):
        self.use(FakeOpener([(lambda u: True, json_response(fixture("hits.json")))]))
        _, out, _ = self.run_main("BlackRock USD Institutional Digital Liquidity Fund")
        self.assertIn("*CIK 0002013810", out)
        self.assertIn("items: 1.01, 9.01", out)
        self.assertIn("several CIKs matched", out)

    def test_missing_fields_do_not_crash(self):
        self.use(FakeOpener([(lambda u: True, json_response(fixture("missing_fields.json")))]))
        code, out, _ = self.run_main("x")
        self.assertEqual(code, 0)
        self.assertIn("CIK ?", out)
        self.assertIn("CIK notanumber", out)

    def test_unexpected_top_level_shapes(self):
        for payload in ({}, {"hits": None}, {"hits": []}, [], {"hits": {"hits": None}}):
            self.use(FakeOpener([(lambda u: True, json_response(payload))]))
            code, out, _ = self.run_main("x")
            self.assertEqual(code, 0, payload)
            self.assertIn("0 results", out)

    def test_pagination(self):
        def page(start, n, total):
            return {"hits": {"total": {"value": total}, "hits": [
                {"_id": f"0000000001-24-{i:06d}:d.xml",
                 "_source": {"ciks": ["0000000001"], "display_names": ["F (CIK 0000000001)"],
                             "form": "D", "file_date": "2024-01-01", "adsh": f"0000000001-24-{i:06d}"}}
                for i in range(start, start + n)]}}
        opener = self.use(FakeOpener([
            (lambda u: "from=100" in u, json_response(page(100, 50, 150))),
            (lambda u: True, json_response(page(0, 100, 150))),
        ]))
        filings, total = ed.search("F", [], UA, max_results=500)
        self.assertEqual((len(filings), total), (150, 150))
        self.assertEqual(len(opener.calls), 2)
        # max_results caps both fetching and output
        opener = self.use(FakeOpener([(lambda u: True, json_response(page(0, 100, 150)))]))
        filings, _ = ed.search("F", [], UA, max_results=30)
        self.assertEqual(len(filings), 30)
        self.assertEqual(len(opener.calls), 1)


class FormDTests(Base):
    def test_parse_form_d(self):
        d = ed.parse_form_d(read_fixture("edgar", "form_d.xml", mode="rb"))
        self.assertEqual(d["issuer"], "Example Liquidity Fund Ltd.")
        self.assertEqual(d["jurisdiction"], "VIRGIN ISLANDS, BRITISH")
        self.assertEqual(d["previous_names"], ["Old Name Fund Ltd."])
        # lowercase "06c" from XML decoded; bare 3C dropped because 3C.7 is present
        self.assertEqual(len(d["exemptions"]), 2)
        self.assertIn("506(c)", d["exemptions"][0])
        self.assertIn("3(c)(7)", d["exemptions"][1])
        self.assertEqual(d["minimum_investment"], "100000")
        self.assertEqual((d["total_sold"], d["investors"]), ("5135523412", "28"))
        self.assertEqual(d["related_persons"][0]["relationships"], ["Director", "Promoter"])
        self.assertEqual(d["related_persons"][1]["name"], "Example Advisers, LLC")   # "N/A" first name dropped
        self.assertEqual(d["related_persons"][1]["clarification"], "Investment Manager")
        r1, r2 = d["sales_compensation"]
        self.assertEqual((r1["name"], r1["crd"], r1["states"], r1["foreign_solicitation"]),
                         ("Example Markets, LLC", "283256", ["All States"], "true"))
        self.assertEqual((r2["states"], r2["broker_dealer"]), (["NY", "CA"], "Parent BD Inc."))
        self.assertEqual(d["signer"], "Jane Director — Director")

    def test_namespaced_and_all_states_element(self):
        raw = (b'<edgarSubmission xmlns="http://www.sec.gov/edgar/formd"><primaryIssuer>'
               b'<entityName>NS Fund</entityName></primaryIssuer><offeringData><salesCompensationList>'
               b'<recipient><recipientName>BD</recipientName><statesOfSolicitationList><allStates/>'
               b'</statesOfSolicitationList></recipient></salesCompensationList></offeringData></edgarSubmission>')
        d = ed.parse_form_d(raw)
        self.assertEqual(d["issuer"], "NS Fund")
        self.assertEqual(d["sales_compensation"][0]["states"], ["All States"])

    def test_minimal_and_malformed_xml(self):
        d = ed.parse_form_d(b"<edgarSubmission/>")
        self.assertEqual((d["issuer"], d["related_persons"], d["sales_compensation"], d["exemptions"]),
                         (None, [], [], []))
        with self.assertRaises(ed.FetchError) as cm:
            ed.parse_form_d(b"<html><body>Rate limited")
        self.assertEqual(cm.exception.kind, "bad_xml")

    def test_details_cli_fetches_latest_form_d_only_for_name_matches(self):
        xml = read_fixture("edgar", "form_d.xml", mode="rb")
        opener = self.use(FakeOpener([
            (lambda u: u.endswith("primary_doc.xml"), FakeResponse(xml, "application/xml")),
            (lambda u: True, json_response(fixture("hits.json"))),
        ]))
        code, out, _ = self.run_main("BlackRock USD Institutional Digital Liquidity Fund", "--details")
        self.assertEqual(code, 0)
        xml_calls = [u for u in opener.urls() if u.endswith(".xml")]
        self.assertEqual(xml_calls, ["https://www.sec.gov/Archives/edgar/data/2013810/000201381026000002/primary_doc.xml"])
        self.assertIn("Minimum investment:  100000", out)
        self.assertIn("Sales compensation:  Example Markets, LLC, CRD 283256 — states: All States", out)
        self.assertIn("Second Placement Agent, BD Parent BD Inc.", out)   # CRD "None" hidden

    def test_details_error_is_reported_not_fatal(self):
        self.use(FakeOpener([
            (lambda u: u.endswith("primary_doc.xml"), http_error("u", 404)),
            (lambda u: True, json_response(fixture("hits.json"))),
        ]))
        code, out, _ = self.run_main("BlackRock USD Institutional Digital Liquidity Fund", "--details", "--json")
        self.assertEqual(code, 0)
        details = json.loads(out)["form_d_details"]
        self.assertIn("HTTP 404", details[0]["error"])

    def test_details_without_form_d(self):
        payload = fixture("hits.json")
        payload["hits"]["hits"] = [h for h in payload["hits"]["hits"] if h["_source"]["form"] not in ("D", "D/A")]
        self.use(FakeOpener([(lambda u: True, json_response(payload))]))
        _, out, _ = self.run_main("Securitize", "--details")
        self.assertIn("--details found no Form D filing", out)


class HttpTests(Base):
    def test_403_then_success_backs_off(self):
        opener = self.use(FakeOpener([(lambda u: True, [http_error("u", 403), http_error("u", 429),
                                                        json_response(fixture("empty.json"))])]))
        code, _, _ = self.run_main("x")
        self.assertEqual(code, 0)
        self.assertEqual(len(opener.calls), 3)
        backoffs = [s for s in self.sleeps if s >= ed.BACKOFF]
        self.assertEqual(backoffs, [ed.BACKOFF, ed.BACKOFF * 2])

    def test_persistent_403_exit_1_with_hint(self):
        self.use(FakeOpener([(lambda u: True, http_error("u", 403))]))
        code, _, err = self.run_main("x")
        self.assertEqual(code, 1)
        self.assertIn("SEC_USER_AGENT", err)

    def test_html_instead_of_json(self):
        self.use(FakeOpener([(lambda u: True, FakeResponse(b"<html>Request Rate Threshold Exceeded</html>", "text/html"))]))
        with self.assertRaises(ed.FetchError) as cm:
            ed.fetch_json("https://x", UA)
        self.assertEqual(cm.exception.kind, "blocked")

    def test_timeout_then_fail(self):
        opener = self.use(FakeOpener([(lambda u: True, socket.timeout("t"))]))
        code, _, err = self.run_main("x")
        self.assertEqual(code, 1)
        self.assertIn("timeout", err)
        self.assertEqual(len(opener.calls), ed.RETRIES + 1)

    def test_400_not_retried(self):
        opener = self.use(FakeOpener([(lambda u: True, http_error("u", 400))]))
        with self.assertRaises(ed.FetchError):
            ed.fetch_json("https://x", UA)
        self.assertEqual(len(opener.calls), 1)

    def test_throttle_keeps_under_rate_limit(self):
        ed._last_request[0] = 0.0
        with mock.patch.object(ed.time, "monotonic", side_effect=[100.0, 100.0, 100.05, 100.05]):
            ed._throttle()
            ed._throttle()
        self.assertEqual(len(self.sleeps), 1)
        self.assertAlmostEqual(self.sleeps[0], ed.MIN_INTERVAL - 0.05)


class SubmissionsTests(Base):
    def test_parse_cik(self):
        for value in ("205021", "0000205021", "CIK205021", " cik0000205021 "):
            self.assertEqual(ed.parse_cik(value), "0000205021", value)
        for value in ("", "0", "abc", "12345678901", "205021x", "-5"):
            with self.assertRaises(ValueError, msg=value):
                ed.parse_cik(value)

    def test_summary_file_numbers_names_and_urls(self):
        r = ed.summarise_submissions(fixture("submissions.json"), "0000205021")
        self.assertEqual(r["name"], "EXAMPLE DISTRIBUTORS, INC.")            # whitespace collapsed
        self.assertEqual(r["state_of_incorporation"], "Delaware")
        self.assertEqual(r["business_address"], "HOUSTON, TX")
        self.assertEqual([f["name"] for f in r["former_names"]],
                         ["EXAMPLE AIM DISTRIBUTORS, INC.", "A I M DISTRIBUTORS INC /BD"])
        self.assertEqual(r["former_names"][0]["from"], "2009-02-27")
        bd, app = r["file_numbers"]                                          # newest first
        self.assertEqual((bd["file_number"], bd["kind"], bd["filings"], bd["latest"]),
                         ("008-21323", "broker-dealer", 3, "2026-02-26"))   # zero-padded prefix
        self.assertEqual(bd["forms"], ["X-17A-5", "X-17A-5/A"])
        self.assertEqual(app["kind"], "exemptive application")
        self.assertEqual([f["file_date"] for f in r["filings"]],
                         ["2026-02-26", "2025-02-27", "2025-01-10", "2024-03-01", "2020-12-07"])
        self.assertEqual(r["filings"][0]["url"], "https://www.sec.gov/Archives/edgar/data/205021/"
                         "000020502126000001/xslX-17A-5_X01/primary_doc.xml")
        self.assertIsNone(r["filings"][3]["url"])                            # no primary document
        self.assertEqual(r["older_filing_files"], 1)

    def test_forms_and_dates_filter_listed_filings_only(self):
        data = fixture("submissions.json")
        r = ed.summarise_submissions(data, "0000205021", ["X-17A-5"], "2025-02-01")
        self.assertEqual([(f["file_date"], f["form"]) for f in r["filings"]],
                         [("2026-02-26", "X-17A-5"), ("2025-02-27", "X-17A-5")])
        r = ed.summarise_submissions(data, "0000205021", ["X-17A-5"], date_to="2025-01-31")
        self.assertEqual([f["form"] for f in r["filings"]], ["X-17A-5/A"])   # amendments match too
        self.assertEqual(len(r["file_numbers"]), 2)                          # file numbers unfiltered

    def test_bad_shapes_do_not_crash(self):
        for data in ({"name": "X"}, {"name": "X", "filings": {"recent": {"form": "D"}}},
                     {"name": "X\x1b[31m", "filings": {"recent": {
                         "accessionNumber": ["a", "b"], "filingDate": ["2026-01-01"], "form": ["D", "D"],
                         "fileNumber": ["021-1", "021-2"], "primaryDocument": ["x", "y"]}}}):
            r = ed.summarise_submissions(data, "0000000001")
            self.assertLessEqual(len(r["filings"]), 1)
            self.assertNotIn("\x1b", r["name"])

    def test_cli_text_requests_padded_cik(self):
        opener = self.use(FakeOpener([(lambda u: "data.sec.gov" in u,
                                       json_response(fixture("submissions.json")))]))
        code, out, err = self.run_main("--submissions", "205021", "--max-results", "2")
        self.assertEqual(code, 0, err)
        url, headers = opener.calls[0]
        self.assertEqual(url, "https://data.sec.gov/submissions/CIK0000205021.json")
        self.assertEqual(headers.get("User-agent"), UA)
        self.assertIn("CIK 0000205021 — EXAMPLE DISTRIBUTORS, INC.", out)
        self.assertIn("008-21323       broker-dealer — X-17A-5, X-17A-5/A; 3 filing(s)", out)
        self.assertIn("2 of 5 recent filing(s):", out)
        self.assertIn("1 older filing file(s)", out)

    def test_cli_json_limits_filings(self):
        self.use(FakeOpener([(lambda u: True, json_response(fixture("submissions.json")))]))
        code, out, _ = self.run_main("--submissions", "205021", "--forms", "X-17A-5", "--json",
                                     "--max-results", "1")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([f["form"] for f in data["filings"]], ["X-17A-5"])
        self.assertEqual(data["file_numbers"][0]["file_number"], "008-21323")

    def test_unknown_cik_and_empty_record_exit_1(self):
        self.use(FakeOpener([(lambda u: True, http_error("u", 404))]))
        code, _, err = self.run_main("--submissions", "9999999999")
        self.assertEqual(code, 1)
        self.assertIn("no EDGAR record for CIK 9999999999", err)
        self.use(FakeOpener([(lambda u: True, json_response({"cik": "1"}))]))
        code, _, err = self.run_main("--submissions", "1")
        self.assertEqual(code, 1)
        self.assertIn("no EDGAR record", err)

    def test_bad_combinations_exit_2_without_request(self):
        opener = self.use(FakeOpener([]))
        for argv in (["X", "--submissions", "1"], ["--submissions", "1", "--details"],
                     ["--submissions", "1", "--raw"], ["--submissions", "x1"], []):
            code, _, _ = self.run_main(*argv)
            self.assertEqual(code, 2, argv)
        self.assertEqual(opener.calls, [])


if __name__ == "__main__":
    unittest.main()
