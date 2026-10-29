import contextlib
import io
import json
import os
import re
import tempfile
import unittest

from helpers import SKILL_DIR, fixture_path, load_script, read_fixture

cr = load_script("check_report")
VALID = read_fixture("reports", "valid_report.md")
TEMPLATE = os.path.join(SKILL_DIR, "references", "report-template.md")


def check(text):
    return cr.validate("r.md", text)


def errors(text):
    return check(text).errors


def replace_once(text, old, new):
    assert text.count(old) == 1, f"fixture must contain exactly one {old!r}"
    return text.replace(old, new)


class TemplateTests(unittest.TestCase):
    def test_template_matches_canonical_structure(self):
        with open(TEMPLATE, encoding="utf-8") as fh:
            skeleton = cr.extract_skeleton(fh.read())
        res = cr.validate(TEMPLATE, skeleton, is_template=True)
        self.assertEqual(res.errors, [])
        self.assertEqual(res.warnings, [])
        self.assertEqual(res.signature["headings"],
                         [f"{'#' * l} {t}" for l, t in cr.SECTIONS])
        for title, spec in cr.TABLES.items():
            self.assertEqual(res.signature["tables"][title], spec["columns"], title)
            if spec["fixed_rows"] is not None:
                self.assertEqual(res.signature["fixed_rows"][title], spec["fixed_rows"], title)

    def test_template_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cr.main(["--template", TEMPLATE, "--strict"])
        self.assertEqual(code, 0, out.getvalue())

    def test_skill_md_paths_exist(self):
        with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("---\nname: tokenized-fund-research\ndescription: "))
        paths = set(re.findall(r"(?:references|scripts)/[\w./-]+\.(?:md|py)", text))
        self.assertGreaterEqual(len(paths), 10)
        for p in paths:
            self.assertTrue(os.path.exists(os.path.join(SKILL_DIR, p)), p)


class ValidReportTests(unittest.TestCase):
    def test_valid_fixture(self):
        res = check(VALID)
        self.assertEqual(res.errors, [])
        self.assertEqual(res.warnings, [])

    def test_appended_rows_allowed_where_permitted(self):
        text = replace_once(VALID, "| Unilateral Amendment of Terms | Trustee | With 30 days notice | No | [2] |",
                            "| Unilateral Amendment of Terms | Trustee | With 30 days notice | No | [2] |\n"
                            "| Side Letters | Trustee | Preferential terms possible | Unknown | [2] |")
        self.assertEqual(errors(text), [])


class SectionTests(unittest.TestCase):
    def test_missing_section(self):
        text = replace_once(VALID, "### 2.3 Leverage, Repo & Rehypothecation\n\n"
                                   "The trust agreement prohibits borrowing and securities lending [2].\n\n", "")
        self.assertIn("missing section: ### 2.3 Leverage, Repo & Rehypothecation", errors(text))

    def test_empty_section(self):
        text = replace_once(VALID, "Claims in the Delaware Court of Chancery against Series T assets [2].", "")
        self.assertTrue(any("[6.4 Investor Remedies] section is empty" in e for e in errors(text)))

    def test_bare_na_vs_na_with_reason(self):
        bare = replace_once(VALID, "The trust agreement prohibits borrowing and securities lending [2].", "N/A")
        self.assertTrue(any("bare 'N/A'" in e for e in errors(bare)))
        ok = replace_once(VALID, "The trust agreement prohibits borrowing and securities lending [2].",
                          "N/A – the trust may not borrow [2].")
        self.assertEqual(errors(ok), [])

    def test_heading_with_extra_text(self):
        text = replace_once(VALID, "### 2.2 Portfolio Composition", "### 2.2 Portfolio Composition (as of June)")
        errs = errors(text)
        self.assertTrue(any("does not match fixed heading '2.2 Portfolio Composition'" in e for e in errs))
        self.assertIn("missing section: ### 2.2 Portfolio Composition", errs)

    def test_wrong_level_and_unexpected_heading(self):
        text = replace_once(VALID, "### 5.2 Claim Chain", "## 5.2 Claim Chain")
        self.assertTrue(any("wrong level H2" in e for e in errors(text)))
        text = replace_once(VALID, "## Appendix A.", "## DeFi Integrations\n\nx [1]\n\n## Appendix A.")
        self.assertTrue(any("unexpected H2 heading 'DeFi Integrations'" in e for e in errors(text)))

    def test_h4_subsections_allowed(self):
        self.assertIn("#### Maturity Ladder", VALID)
        self.assertEqual(errors(VALID), [])

    def test_out_of_order_and_duplicate(self):
        a = "### 5.3 Bankruptcy Remoteness & Recourse\n\nDelaware series liabilities are enforceable only against that series [2].\n\n"
        text = replace_once(VALID, a, "")
        text = replace_once(text, "### 5.1 What the Investor Owns", a + "### 5.1 What the Investor Owns")
        self.assertTrue(any("out of order" in e for e in errors(text)))
        dup = replace_once(VALID, "## 1. Intro", "## 1. Intro\n\nx [1]\n\n## 1. Intro")
        self.assertTrue(any("duplicate section: 1. Intro" in e for e in errors(dup)))

    def test_headings_inside_code_blocks_ignored(self):
        text = replace_once(VALID, "```\nHolder", "```\n## 9. Not a heading\nHolder")
        self.assertEqual(errors(text), [])

    def test_header_fields(self):
        text = replace_once(VALID, "**Ticker:** EXTB\n", "")
        self.assertIn("header field '**Ticker:**' missing or empty", errors(text))
        text = replace_once(VALID, "**Report date:** 2026-10-28", "**Report date:** 28/10/2026")
        self.assertTrue(any("not YYYY-MM-DD" in e for e in errors(text)))
        text = replace_once(VALID, "# Example Treasury Fund (EXTB) — Tokenized Fund Report\n", "")
        self.assertIn("missing H1 title before the first section", errors(text))

    def test_placeholder_left(self):
        text = replace_once(VALID, "AUM was USD 100m", "AUM was {{AUM}}")
        self.assertTrue(any("unfilled placeholder {{AUM}}" in e for e in errors(text)))


class TableTests(unittest.TestCase):
    ROLE_SUB = "| Sub-Adviser | N/A – no sub-adviser appointed | N/A – no sub-adviser | N/A – no sub-adviser | N/A – no sub-adviser | — |\n"
    ROLE_AUD = "| Auditor | Audit LLP | LLP, US | PCAOB – registered firm | Independent | [2] |\n"

    def test_roles_reordered(self):
        text = replace_once(VALID, self.ROLE_SUB, "")
        text = replace_once(text, self.ROLE_AUD, self.ROLE_AUD + self.ROLE_SUB)
        self.assertTrue(any("[3.1 Universal Roles] fixed rows out of order" in e for e in errors(text)))

    def test_role_missing(self):
        text = replace_once(VALID, self.ROLE_AUD, "")
        self.assertTrue(any("missing fixed rows: ['Auditor']" in e for e in errors(text)))

    def test_extra_role_in_universal_table(self):
        text = replace_once(VALID, "| KYC / AML Provider | Example Inc. | Corporation, Delaware, US | FinCEN – AML programme | Principal | [1, 2] |",
                            "| KYC / AML Provider | Example Inc. | Corporation, Delaware, US | FinCEN – AML programme | Principal | [1, 2] |\n"
                            "| Paying Agent | Bank | Bank, US | OCC | Independent | [2] |")
        self.assertTrue(any("rows not allowed" in e and "Paying Agent" in e for e in errors(text)))

    def test_renamed_column(self):
        text = replace_once(VALID, "| Role | Entity | Legal Form & Jurisdiction | Regulator / Licence | Independence from Sponsor | Source |",
                            "| Role | Entity | Jurisdiction | Regulator / Licence | Independence from Sponsor | Source |")
        self.assertTrue(any("[3.1 Universal Roles] table columns" in e for e in errors(text)))

    def test_cell_count_mismatch(self):
        text = replace_once(VALID, "| Voting | Limited | Only on fundamental changes | [2] |",
                            "| Voting | Limited | Only on fundamental changes |")
        self.assertTrue(any("row 1 has 3 cells, header has 4" in e for e in errors(text)))

    def test_empty_and_bare_na_cells(self):
        text = replace_once(VALID, "| Redemption | Yes | Daily at NAV | [2] |", "| Redemption | Yes |  | [2] |")
        self.assertTrue(any("empty 'Detail' cell" in e for e in errors(text)))
        text = replace_once(VALID, "| Redemption | Yes | Daily at NAV | [2] |", "| Redemption | N/A | Daily at NAV | [2] |")
        self.assertTrue(any("'Held by Investor?' is 'N/A'" in e for e in errors(text)))
        text = replace_once(VALID, "| Redemption | Yes | Daily at NAV | [2] |", "| Redemption | Yes | Daily at NAV |  |")
        self.assertTrue(any("empty Source cell" in e for e in errors(text)))

    def test_source_cell_without_citation_warns(self):
        res = check(replace_once(VALID, "| Redemption | Yes | Daily at NAV | [2] |",
                                 "| Redemption | Yes | Daily at NAV | offering memo |"))
        self.assertEqual(res.errors, [])
        self.assertTrue(any("Source cell has no [n]" in w for w in res.warnings))

    def test_formatting_variants_parse(self):
        # no outer pipes, extra whitespace, alignment colons
        text = replace_once(VALID,
                            "| Document | Governing Law | Courts / Forum | Source |\n|---|---|---|---|\n"
                            "| Trust Agreement | Delaware | Delaware Court of Chancery | [2] |",
                            "Document   |  Governing Law | Courts / Forum|Source\n:---|:---:| ---: |---\n"
                            "Trust Agreement | Delaware | Delaware Court of Chancery | [2]")
        self.assertEqual(errors(text), [])

    def test_escaped_pipe_in_cell(self):
        res = check(VALID)
        self.assertIn("Cash | USD", res.signature["extra_rows"]["2.2 Portfolio Composition"])

    def test_product_specific_roles(self):
        table = ("> **Note:** certificates need a trustee [2].\n\n"
                 "| Role | Entity | Legal Form & Jurisdiction | Regulator / Licence | Why This Role Exists | Source |\n"
                 "|---|---|---|---|---|---|\n"
                 "| Security Trustee | Trustee GmbH | GmbH, Germany | Unregulated – trustee | Holds collateral | [2] |")
        na = "N/A – the trust series uses only the universal roles; no trustee, wrapper or liquidity provider is involved [2]."
        self.assertEqual(errors(replace_once(VALID, na, table)), [])
        no_note = replace_once(VALID, na, table.split("\n\n", 1)[1])
        self.assertTrue(any("preceded by a '> **Note:**'" in e for e in errors(no_note)))
        nothing = replace_once(VALID, na, "Some prose without a table [2].")
        self.assertTrue(any("[3.2 Product-Specific Roles] required table is missing" in e for e in errors(nothing)))

    def test_portfolio_section_na_allowed(self):
        start = VALID.index("### 2.2 Portfolio Composition")
        end = VALID.index("### 2.3")
        text = VALID[:start] + "### 2.2 Portfolio Composition\n\nN/A – holdings not published [3].\n\n" + VALID[end:]
        self.assertEqual(errors(text), [])


class CitationTests(unittest.TestCase):
    def test_parse_variants(self):
        self.assertEqual(cr.parse_citations("a [3][7] b"), {3, 7})
        self.assertEqual(cr.parse_citations("a [2-4] b [2–3, 9]"), {2, 3, 4, 9})
        self.assertEqual(cr.parse_citations("see [1](https://x) and [link](y) and [ ]"), set())
        self.assertEqual(cr.parse_citations("[ 5 , 6 ]"), {5, 6})
        with self.assertRaises(ValueError):
            cr.parse_citations("[4-2]")
        with self.assertRaises(ValueError):
            cr.parse_citations("[1-500]")

    def test_broken_citation(self):
        text = replace_once(VALID, "Treasury bills settle T+1; the fund redeems daily [2-3].",
                            "Treasury bills settle T+1 [99].")
        self.assertIn("citation [99] has no matching entry in Appendix B. Sources", errors(text))

    def test_reversed_range_is_error(self):
        text = replace_once(VALID, "the fund redeems daily [2-3].", "the fund redeems daily [3-2].")
        self.assertTrue(any("reversed citation range" in e for e in errors(text)))

    def test_uncited_source_warns(self):
        text = VALID.rstrip("\n") + "\n7. Unused source — accessed 2026-10-28\n"
        res = check(text)
        self.assertEqual(res.errors, [])
        self.assertIn("[Sources] entry 7 is never cited", res.warnings)

    def test_duplicate_source_and_missing_date(self):
        text = VALID.rstrip("\n") + "\n6. Duplicate number\n"
        res = check(text)
        self.assertIn("[Sources] duplicate source number 6", res.errors)
        self.assertIn("[Sources] entry 6 has no access date (YYYY-MM-DD)", res.warnings)

    def test_citation_only_in_table_cell_counts(self):
        # source 6 is cited only inside the 4.2 table
        self.assertNotIn("never cited", " ".join(check(VALID).warnings))

    def test_citations_in_code_ignored(self):
        text = replace_once(VALID, "Holder ──> EXTB token", "Holder [77] ──> EXTB token")
        self.assertEqual(errors(text), [])

    def test_no_sources(self):
        idx = VALID.index("## Appendix B. Sources")
        text = VALID[:idx] + "## Appendix B. Sources\n\nNone.\n"
        errs = errors(text)
        self.assertIn("[Sources] no numbered source entries found", errs)


class RefinementTests(unittest.TestCase):
    """Rules added after the first end-to-end run (USTB)."""

    def test_data_freshness_required(self):
        text = replace_once(VALID, "**Data freshness:** Portfolio as of 2026-09-30; AUM as of 2026-10-27\n", "")
        self.assertIn("header field '**Data freshness:**' missing or empty", errors(text))

    def test_bracketed_years_are_not_citations(self):
        self.assertEqual(cr.parse_citations("amended [2026] and [2020-2024], see [3]"), {3})
        text = replace_once(VALID, "AUM was USD 100m", "AUM was USD 100m [2026]")
        self.assertEqual(errors(text), [])

    def test_dash_source_on_non_na_row_warns(self):
        res = check(replace_once(VALID, "| Redemption | Yes | Daily at NAV | [2] |", "| Redemption | Yes | Daily at NAV | — |"))
        self.assertEqual(res.errors, [])
        self.assertTrue(any("Source is '—' but the row is not N/A" in w for w in res.warnings))

    def test_not_disclosed_row_may_use_dash_source(self):
        row = "| Legal Counsel | Not disclosed in public documents | Not disclosed in public documents | Not disclosed in public documents | Not disclosed in public documents | [2] |"
        res = check(replace_once(VALID, row, row.replace("| [2] |", "| — |")))
        self.assertFalse(any("Source is '—'" in w for w in res.warnings))

    def test_na_row_may_use_dashes(self):
        text = replace_once(VALID, TableTests.ROLE_SUB,
                            "| Sub-Adviser | N/A – no sub-adviser appointed | — | — | — | — |\n")
        self.assertEqual(errors(text), [])
        # but a dash in a row whose first data cell is not N/A is still an error
        text = replace_once(VALID, "| Auditor | Audit LLP | LLP, US |", "| Auditor | Audit LLP | — |")
        self.assertTrue(any("'Legal Form & Jurisdiction' is '—'" in e for e in errors(text)))

    def test_exercised_to_date_must_answer(self):
        res = check(replace_once(VALID, "| Compulsory Redemption | Trustee | \"for any reason\" | No | [2] |",
                                 "| Compulsory Redemption | Trustee | \"for any reason\" | Sometimes | [2] |"))
        self.assertTrue(any("'Exercised to Date?' should start with" in w for w in res.warnings))
        res = check(replace_once(VALID, "| Compulsory Redemption | Trustee | \"for any reason\" | No | [2] |",
                                 "| Compulsory Redemption | Trustee | \"for any reason\" | Yes – twice in 2025 | [2] |"))
        self.assertEqual(res.warnings, [])

    def test_entity_without_h4_warns(self):
        text = replace_once(VALID, "#### Audit LLP — Auditor\n\n- **Scope:** audits annual statements [2].\n\n", "")
        res = check(text)
        self.assertEqual(res.errors, [])
        self.assertIn("[3.3 Entity Responsibilities] no '#### Audit LLP — …' heading for an entity "
                      "named in 3.1/3.2", res.warnings)

    def test_entity_names_parsing(self):
        cell = ("Turnkey (key-management infrastructure; legal entity name not disclosed); admin keys are "
                "single EOAs [5]")
        self.assertEqual(cr.entity_names(cell), ["Turnkey"])
        self.assertEqual(cr.entity_names("PwC LLP (since 2026 (approx.); EY before)"), ["PwC LLP"])
        self.assertEqual(cr.entity_names('Chainlink "USTB NAV" feed and Pyth'), ["Chainlink"])
        self.assertEqual(cr.entity_names("Superstate Inc. via the portal"), ["Superstate Inc"])
        for skip in ("N/A – none", "Not disclosed in public documents", "—", ""):
            self.assertEqual(cr.entity_names(skip), [], skip)

    def test_group_entities_not_confused(self):
        # "Example Inc." heading must not cover "Example Advisers LLC"
        text = replace_once(VALID, "#### Example Advisers LLC — Investment Manager / Adviser\n\n"
                                   "- **Scope:** manages the portfolio [2].\n\n", "")
        self.assertTrue(any("Example Advisers LLC" in w for w in check(text).warnings))

    def test_responsibilities_without_any_h4_is_error(self):
        start = VALID.index("### 3.3 Entity Responsibilities")
        end = VALID.index("## 4. Who Can Invest")
        text = VALID[:start] + "### 3.3 Entity Responsibilities\n\nSee the tables above [2].\n\n" + VALID[end:]
        self.assertIn("[3.3 Entity Responsibilities] no H4 per entity found", errors(text))


class RenumberTests(unittest.TestCase):
    DOC = (
        "# T\n\n## 1. Intro\n\nFirst [3]. Then [1, 3] and [2-4]. Year [2026] stays. "
        "Code `[9]` stays.\n\n```\n[7] in fence\n```\n\n| A | Source |\n|---|---|\n| x | [4][3] |\n\n"
        "## Appendix B. Sources\n\nIntro line.\n\n1. One — accessed 2026-01-01\n"
        "2. Two — accessed 2026-01-01\n   continuation of two\n3. Three — accessed 2026-01-01\n"
        "4. Four — accessed 2026-01-01\n5. Uncited — accessed 2026-01-01\n"
    )

    def test_first_appearance_order(self):
        new, mapping = cr.renumber(self.DOC)
        self.assertEqual(mapping, {3: 1, 1: 2, 2: 3, 4: 4, 5: 5})
        self.assertIn("First [1]. Then [1, 2] and [1, 3, 4].", new)   # [2-4] -> {3,1,4} -> collapsed
        self.assertIn("Year [2026] stays.", new)
        self.assertIn("`[9]`", new)
        self.assertIn("[7] in fence", new)
        self.assertIn("| x | [4][1] |", new)
        src = new.split("## Appendix B. Sources")[1]
        self.assertIn("Intro line.", src)
        self.assertLess(src.index("1. Three"), src.index("2. One"))
        self.assertIn("3. Two — accessed 2026-01-01\n   continuation of two\n4. Four", src)
        self.assertTrue(src.rstrip().endswith("5. Uncited — accessed 2026-01-01"))

    def test_idempotent_and_collapses_runs(self):
        once, _ = cr.renumber(self.DOC)
        twice, mapping = cr.renumber(once)
        self.assertEqual(once, twice)
        self.assertEqual(cr._collapse([5, 1, 2, 3, 7, 8]), "1-3, 5, 7, 8")

    def test_errors(self):
        with self.assertRaises(ValueError):
            cr.renumber(self.DOC.replace("First [3]", "First [9]"))      # no such source
        with self.assertRaises(ValueError):
            cr.renumber("# T\n\n## 1. Intro\n\nx [1]\n")              # no sources section
        with self.assertRaises(ValueError):
            cr.renumber(self.DOC.replace("4. Four", "3. Four"))          # duplicate number

    def test_sources_section_followed_by_another_h2(self):
        doc = self.DOC + "\n## Appendix C. Extra\n\nTail [3]\n"
        new, _ = cr.renumber(doc)
        self.assertIn("## Appendix C. Extra\n\nTail [1]", new)

    def test_cli_renumbers_valid_report_and_keeps_it_valid(self):
        text = VALID.replace("Example product page", "TMP").replace(
            "1. TMP", "1. Example product page")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace("[1, 2]", "[2, 1]"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cr.main(["--renumber", path])
            self.assertEqual(code, 0, out.getvalue())
            self.assertTrue(os.path.exists(path + ".bak"))
            with open(path, encoding="utf-8") as fh:
                self.assertIn("[1, 2]", fh.read())
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    cr.main(["--renumber", path, path])


class TierTests(unittest.TestCase):
    """Source tiers and the secondary-only rule for legal claims (references/claim-check.md)."""

    AUDITOR = "| Auditor | Audit LLP | LLP, US | PCAOB – registered firm | Independent | [2] |"

    def test_missing_or_bad_tier_tag_warns(self):
        for bad in ("2. Example Asset", "2. [X] Example Asset", "2. [p] Example Asset"):
            text = replace_once(VALID, "2. [P] Example Asset", bad)
            res = check(text)
            self.assertEqual(res.errors, [])
            self.assertIn("[Sources] entry 2 has no [P] / [S] tier tag (references/claim-check.md)",
                          res.warnings, bad)

    def test_secondary_only_legal_row_warns(self):
        text = replace_once(VALID, self.AUDITOR, self.AUDITOR.replace("[2] |", "[3] |"))
        res = check(text)
        self.assertTrue(any("[3.1 Universal Roles] row 'Auditor': legal claim backed only by [S]" in w
                            for w in res.warnings))

    def test_attribution_silences_warning(self):
        row = "| Auditor | Audit LLP (per the factsheet) | LLP, US | PCAOB – registered firm | Independent | [3] |"
        res = check(replace_once(VALID, self.AUDITOR, row))
        self.assertFalse(any("backed only by [S]" in w for w in res.warnings))

    def test_mixed_tiers_ok_and_non_legal_tables_ignored(self):
        res = check(replace_once(VALID, self.AUDITOR, self.AUDITOR.replace("[2] |", "[2, 3] |")))
        self.assertFalse(any("backed only by [S]" in w for w in res.warnings))
        # 4.2 Eligible Venues cites only [S] source 6 and is not a legal table
        self.assertIn("| Eligible Venues | Listed as collateral on a lending protocol (proposal stage) | [6] |", VALID)
        self.assertEqual(check(VALID).warnings, [])

    def test_na_rows_and_untagged_sources_not_flagged_as_secondary(self):
        sub = "| Sub-Adviser | N/A – no sub-adviser appointed | N/A – no sub-adviser | N/A – no sub-adviser | N/A – no sub-adviser | — |"
        text = replace_once(VALID, sub, sub.replace("| — |", "| [3] |"))
        self.assertFalse(any("Sub-Adviser': legal claim" in w for w in check(text).warnings))
        # an untagged source is reported as untagged, not treated as secondary
        text = replace_once(VALID, "3. [S] Example factsheet", "3. Example factsheet")
        text = replace_once(text, self.AUDITOR, self.AUDITOR.replace("[2] |", "[3] |"))
        warns = check(text).warnings
        self.assertFalse(any("backed only by [S]" in w for w in warns))
        self.assertTrue(any("entry 3 has no [P] / [S]" in w for w in warns))

    def test_tiers_survive_renumber(self):
        new, mapping = cr.renumber(VALID)
        src = new.split("## Appendix B. Sources")[1]
        for line in src.strip().splitlines():
            self.assertRegex(line, r"^\d+\. \[(P|S)\] ")
        self.assertEqual(check(new).warnings, [])


class MultiReportTests(unittest.TestCase):
    def run_cli(self, *texts, extra=()):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i, t in enumerate(texts):
                p = os.path.join(d, f"r{i}.md")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(t)
                paths.append(p)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = cr.main(paths + list(extra))
        return code, out.getvalue()

    def test_identical_structure_with_product_specific_differences(self):
        other = replace_once(VALID, "| US Accredited Investor |",
                             "| US Qualified Purchaser | ICA §2(a)(51) | US | USD 5m investments | KYC | [4] |\n| US Accredited Investor |")
        code, out = self.run_cli(VALID, other)
        self.assertEqual(code, 0, out)
        self.assertIn("0 structural difference(s)", out)
        self.assertIn("[info] 4.1 Primary Market Eligibility: product-specific rows", out)

    def test_structural_difference_fails(self):
        bad = replace_once(VALID, TableTests.ROLE_AUD, "")
        code, out = self.run_cli(VALID, bad)
        self.assertEqual(code, 1)
        self.assertIn("[DIFF] 3.1 Universal Roles: fixed rows", out)

    def test_json_output(self):
        code, out = self.run_cli(VALID, VALID, extra=["--json"])
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual(data["structural_differences"], 0)

    def test_strict_mode_fails_on_warning(self):
        text = VALID.rstrip("\n") + "\n7. Unused — accessed 2026-10-28\n"
        self.assertEqual(self.run_cli(text)[0], 0)
        self.assertEqual(self.run_cli(text, extra=["--strict"])[0], 1)

    def test_missing_file_exit_2(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cr.main([fixture_path("reports", "nope.md")]), 2)

    def test_no_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cr.main([])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
