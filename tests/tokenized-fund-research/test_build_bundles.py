import contextlib
import hashlib
import importlib.util
import io
import os
import re
import shutil
import tempfile
import unittest

from helpers import SKILL_DIR, load_script

bb = load_script("build_bundles")


def forum_files():
    """The forum files collector D's bundle should hold, in file-name order."""
    folder = os.path.join(SKILL_DIR, "references", "forums")
    return [f"references/forums/{f}" for f in sorted(os.listdir(folder)) if f.endswith(".md")]

PRODUCT = """# Midas mTBILL (mTBILL)

- Platform: midas
- Ticker: mTBILL
- Token legal form: certificate
- Issuer legal entity: Midas Software GmbH
- Underlying fund / manager: USTB, BUIDL
- Chains and main contracts: Ethereum: 0xDD62...
- Date: 2026-10-28
- SEC_USER_AGENT: set
- PDF tooling: pdftotext no, pdftoppm no, pypdf no
- Collector models: A=sonnet B=opus C=sonnet D=sonnet

## Focus notes

Final Terms of 17 Jul 2026 switched mTBILL to Swiss law.
"""


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.work = os.path.join(self.tmp, "reports", ".work", "midas-mTBILL")
        os.makedirs(self.work)
        self.write("product.md", PRODUCT)
        self.write(".sec-user-agent", "Jane Analyst jane@example.com\n")

    def write(self, name, text):
        path = os.path.join(self.work, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def read(self, name):
        with open(os.path.join(self.work, name), encoding="utf-8") as fh:
            return fh.read()

    def run_main(self, *argv, module=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = (module or bb).main(list(argv))
        return code, out.getvalue(), err.getvalue()


class BuildTests(Base):
    def test_builds_all_four_with_expected_parts(self):
        code, out, err = self.run_main(self.work)
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")                      # complete product.md -> no warnings
        expected_extras = {"A": [], "B": ["references/investor-frameworks.md", "references/roles.md"],
                           "C": [], "D": ["references/forums.md"] + forum_files()}
        for letter, extras in expected_extras.items():
            bundle = self.read(f"bundle-{letter}.md")
            parts = re.findall(r"<!-- bundle part: (.+?) -->", bundle)
            self.assertEqual(parts, ["product.md", f"references/collectors/{letter}.md",
                                     "references/collectors/rules.md", "references/sources/common.md",
                                     "references/sources/midas.md"] + extras, letter)
            self.assertIn("Final Terms of 17 Jul 2026 switched mTBILL to Swiss law.", bundle)
            self.assertIn(f"bundle-{letter}.md", out)

    def test_parts_are_copied_verbatim(self):
        self.run_main(self.work)
        with open(os.path.join(SKILL_DIR, "references", "collectors", "rules.md"), encoding="utf-8") as fh:
            rules = fh.read()
        self.assertIn(rules, self.read("bundle-A.md"))

    def test_deterministic(self):
        self.run_main(self.work)
        first = {n: digest(os.path.join(self.work, n)) for n in os.listdir(self.work) if n not in ("product.md", ".sec-user-agent")}
        self.run_main(self.work)
        second = {n: digest(os.path.join(self.work, n)) for n in os.listdir(self.work) if n not in ("product.md", ".sec-user-agent")}
        self.assertEqual(len(first), 8)
        self.assertEqual(first, second)

    def test_crlf_product_gives_same_bundle(self):
        self.run_main(self.work)
        before = digest(os.path.join(self.work, "bundle-B.md"))
        self.write("product.md", PRODUCT.replace("\n", "\r\n") + "\r\n\r\n")
        self.run_main(self.work)
        self.assertEqual(digest(os.path.join(self.work, "bundle-B.md")), before)

    def test_prompt_filled_and_line_count_correct(self):
        self.run_main(self.work)
        for letter in "ABCD":
            prompt = self.read(f"prompt-{letter}.md")
            self.assertIsNone(re.search(r"\{[A-Z_]+\}", prompt), letter)
            self.assertNotIn("\n\n\n", prompt)          # empty {RESUME} line removed cleanly
            self.assertNotIn("resumed run", prompt)
            lines = self.read(f"bundle-{letter}.md").count("\n")
            work = os.path.normpath(self.work)
            self.assertIn(f"- {work}/bundle-{letter}.md ({lines} lines)", prompt)
            self.assertIn(f"collector {letter} (", prompt)
            self.assertIn(f"{SKILL_DIR}/scripts/", prompt)

    def test_prompt_matches_template_outside_placeholders(self):
        self.run_main(self.work)
        with open(os.path.join(SKILL_DIR, "references", "collectors", "prompt.md"), encoding="utf-8") as fh:
            template = fh.read()
        prompt = self.read("prompt-C.md")
        # every fixed line of the template appears unchanged in the prompt
        for line in template.splitlines():
            if line.strip() and "{" not in line:
                self.assertIn(line, prompt)

    def test_subset_and_order(self):
        code, out, _ = self.run_main(self.work, "--collectors", "d, b,B")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(n for n in os.listdir(self.work) if n.startswith("bundle")),
                         ["bundle-B.md", "bundle-D.md"])
        self.assertLess(out.index("bundle-B.md"), out.index("bundle-D.md"))

    def test_platform_override_case_and_markdown(self):
        self.write("product.md", PRODUCT.replace("- Platform: midas", "- **Platform:** `Midas` (midas.app)"))
        code, _, err = self.run_main(self.work, "--platform", "MIDAS")
        self.assertEqual(code, 0, err)

    def test_trailing_slash_and_dot_paths_normalised(self):
        self.run_main(self.work + "/./")
        self.assertIn(f"{os.path.normpath(self.work)}/notes-A.md", self.read("prompt-A.md"))
        self.assertNotIn("/./", self.read("prompt-A.md"))


class ResumeTests(Base):
    def test_resume_when_letter_folder_has_files(self):
        self.write("C/pdf/terms.pdf", "x")
        code, out, _ = self.run_main(self.work)
        self.assertEqual(code, 0)
        self.assertIn("resumed run", self.read("prompt-C.md"))
        self.assertIn(f"{os.path.normpath(self.work)}/C/", self.read("prompt-C.md"))
        self.assertNotIn("resumed run", self.read("prompt-A.md"))
        self.assertIn("[resume]", [l for l in out.splitlines() if l.startswith("C ")][0])

    def test_resume_when_notes_exist(self):
        self.write("notes-B.md", "- fact\n  src: x\n")
        self.run_main(self.work)
        self.assertIn("resumed run", self.read("prompt-B.md"))

    def test_no_resume_for_empty_or_hidden_leftovers(self):
        os.makedirs(os.path.join(self.work, "A"))
        self.write("A/.DS_Store", "x")
        self.write("A/.cache/blob", "x")
        self.write("notes-D.md", "  \n\n")
        self.run_main(self.work)
        self.assertNotIn("resumed run", self.read("prompt-A.md"))
        self.assertNotIn("resumed run", self.read("prompt-D.md"))


class ErrorTests(Base):
    def test_missing_work_dir(self):
        code, _, err = self.run_main(os.path.join(self.tmp, "nope"))
        self.assertEqual(code, 1)
        self.assertIn("work dir not found", err)

    def test_missing_or_empty_product(self):
        os.remove(os.path.join(self.work, "product.md"))
        code, _, err = self.run_main(self.work)
        self.assertEqual((code, "missing file: product.md" in err), (1, True))
        self.write("product.md", "  \n")
        code, _, err = self.run_main(self.work)
        self.assertEqual((code, "product.md is empty" in err), (1, True))

    def test_no_platform_anywhere(self):
        self.write("product.md", PRODUCT.replace("- Platform: midas\n", ""))
        code, _, err = self.run_main(self.work)
        self.assertEqual(code, 1)
        self.assertIn("no platform", err)

    def write_draft(self, platform, text="# Franklin — sources\n\n- **Docs**: https://example.com/docs\n"):
        path = os.path.join(os.path.dirname(self.work), f"platform-{platform}", "sources.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_unknown_platform_without_draft_fails(self):
        self.write("product.md", PRODUCT.replace("- Platform: midas", "- Platform: Franklin Templeton"))
        code, _, err = self.run_main(self.work)
        self.assertEqual(code, 1)
        self.assertIn("no sources for platform 'franklin'", err)
        self.assertIn("tokenization-platform-fetch", err)
        self.assertIn("midas", err)                    # lists the known ones
        self.assertFalse(os.path.exists(os.path.join(self.work, "bundle-A.md")))

    def test_unknown_platform_uses_draft(self):
        self.write("product.md", PRODUCT.replace("- Platform: midas", "- Platform: franklin"))
        draft = self.write_draft("franklin")
        code, out, err = self.run_main(self.work)
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        for letter in "ABCD":
            bundle = self.read(f"bundle-{letter}.md")
            self.assertIn("https://example.com/docs", bundle)
            self.assertIn("platform-franklin/sources.md (draft by tokenization-platform-fetch)", bundle)
            self.assertNotIn("references/sources/franklin.md", bundle)
        # resumes pick the draft up again with no extra flag; an empty draft is an error
        code, _, _ = self.run_main(self.work, "--collectors", "B")
        self.assertEqual(code, 0)
        with open(draft, "w", encoding="utf-8") as fh:
            fh.write("  \n")
        code, _, err = self.run_main(self.work)
        self.assertEqual((code, "empty reference file" in err), (1, True))
        os.remove(draft)
        os.makedirs(draft)                              # a folder where the draft should be
        code, _, err = self.run_main(self.work)
        self.assertEqual((code, "no draft at" in err), (1, True))

    def test_built_in_file_wins_over_draft(self):
        self.write_draft("midas", "# Midas — sources\n\n- **Docs**: https://draft.example\n")
        code, _, err = self.run_main(self.work)
        self.assertEqual(code, 0)
        self.assertIn("a draft exists", err)
        self.assertNotIn("https://draft.example", self.read("bundle-A.md"))
        self.assertIn("<!-- bundle part: references/sources/midas.md -->", self.read("bundle-A.md"))

    def test_generic_flag_is_gone(self):
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
            bb.main([self.work, "--generic"])
        self.assertEqual(cm.exception.code, 2)

    def test_placeholder_platform_names_rejected(self):
        for value in ("other", "Other", "**other**", "`generic`", "N/A", "unknown", "TBD", "common"):
            self.write("product.md", PRODUCT.replace("- Platform: midas", f"- Platform: {value}"))
            self.write_draft(value.strip("*`").lower().split("/")[0])   # a draft doesn't make it valid
            code, _, err = self.run_main(self.work)
            self.assertEqual(code, 1, value)
            self.assertIn("not a platform name", err, value)
        self.write("product.md", PRODUCT.replace("- Platform: midas\n", ""))
        code, _, err = self.run_main(self.work, "--platform", "other")
        self.assertEqual((code, "not a platform name" in err), (1, True))

    def test_sec_contact_never_in_product_md(self):
        for value in ("Jane Analyst jane@example.com", '"Jane j@x.io"', "**set** jane@example.com"):
            self.write("product.md", PRODUCT.replace("- SEC_USER_AGENT: set", f"- SEC_USER_AGENT: {value}"))
            code, _, err = self.run_main(self.work)
            self.assertEqual(code, 1, value)
            self.assertIn(".sec-user-agent", err)
            self.assertFalse(os.path.exists(os.path.join(self.work, "bundle-B.md")), value)
        # the contact file itself never reaches a bundle
        self.write("product.md", PRODUCT)
        code, _, err = self.run_main(self.work)
        self.assertEqual(code, 0, err)
        for letter in "ABCD":
            self.assertNotIn("jane@example.com", self.read(f"bundle-{letter}.md"))

    def test_sec_set_without_file_warns(self):
        for content in (None, "", "  \n"):
            path = os.path.join(self.work, ".sec-user-agent")
            if content is None:
                os.remove(path)
            else:
                self.write(".sec-user-agent", content)
            code, _, err = self.run_main(self.work)
            self.assertEqual(code, 0, err)
            self.assertIn("collector B cannot query EDGAR", err, repr(content))
        for value in ("declined", "Set (in .sec-user-agent)"):
            self.write(".sec-user-agent", "Jane jane@example.com")
            self.write("product.md", PRODUCT.replace("- SEC_USER_AGENT: set", f"- SEC_USER_AGENT: {value}"))
            _, _, err = self.run_main(self.work)
            self.assertNotIn("cannot query EDGAR", err, value)
        os.remove(os.path.join(self.work, ".sec-user-agent"))
        self.write("product.md", PRODUCT.replace("- SEC_USER_AGENT: set", "- SEC_USER_AGENT: declined"))
        _, _, err = self.run_main(self.work)
        self.assertNotIn("cannot query EDGAR", err)

    def test_platform_contradiction(self):
        code, _, err = self.run_main(self.work, "--platform", "ondo")
        self.assertEqual(code, 1)
        self.assertIn("contradicts", err)

    def test_bad_collectors_argument(self):
        for value in ("E", "A,X", ",", ""):
            code, _, _ = self.run_main(self.work, "--collectors", value)
            self.assertEqual(code, 2, value)

    def test_missing_fields_warn_but_build(self):
        self.write("product.md", "# X (Y)\n\n- Platform: midas\n")
        code, _, err = self.run_main(self.work)
        self.assertEqual(code, 0)
        for name in ("SEC_USER_AGENT", "PDF tooling", "Collector models", "## Focus notes"):
            self.assertIn(name, err)

    def test_work_dir_is_a_file(self):
        path = os.path.join(self.tmp, "file")
        open(path, "w").close()
        code, _, err = self.run_main(path)
        self.assertEqual(code, 1)


class SkillCopyTests(Base):
    """Break a copy of the skill and check the builder refuses to build."""

    def copy_skill(self):
        dst = os.path.join(self.tmp, "skill")
        shutil.copytree(os.path.join(SKILL_DIR, "scripts"), os.path.join(dst, "scripts"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(SKILL_DIR, "references"), os.path.join(dst, "references"))
        spec = importlib.util.spec_from_file_location("bb_copy", os.path.join(dst, "scripts", "build_bundles.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return dst, module

    def edit(self, path, old, new):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert old in text
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new))

    def test_missing_reference_part(self):
        dst, module = self.copy_skill()
        os.remove(os.path.join(dst, "references", "forums.md"))
        code, _, err = self.run_main(self.work, module=module)
        self.assertEqual(code, 1)
        self.assertIn("missing file: references/forums.md", err)

    def test_forum_files_are_picked_up_and_required(self):
        dst, module = self.copy_skill()
        folder = os.path.join(dst, "references", "forums")
        with open(os.path.join(folder, "newdao.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nbase_url: https://gov.newdao.example\nengine: discourse\n---\n\n# NewDAO\n")
        code, _, err = self.run_main(self.work, "--collectors", "D", module=module)
        self.assertEqual(code, 0, err)
        self.assertIn("<!-- bundle part: references/forums/newdao.md -->", self.read("bundle-D.md"))
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        code, _, err = self.run_main(self.work, "--collectors", "D", module=module)
        self.assertEqual(code, 1)
        self.assertIn("no files match references/forums/*.md", err)

    def test_unknown_placeholder_in_template(self):
        dst, module = self.copy_skill()
        self.edit(os.path.join(dst, "references", "collectors", "prompt.md"), "{ROLE}", "{ROLES}")
        code, _, err = self.run_main(self.work, module=module)
        self.assertEqual(code, 1)
        self.assertIn("unknown placeholder(s) ['ROLES']", err)

    def test_required_placeholder_missing(self):
        dst, module = self.copy_skill()
        self.edit(os.path.join(dst, "references", "collectors", "prompt.md"), "{LINES} lines", "many lines")
        code, _, err = self.run_main(self.work, module=module)
        self.assertEqual(code, 1)
        self.assertIn("required placeholder(s) missing ['LINES']", err)

    def test_resume_placeholder_must_be_alone(self):
        dst, module = self.copy_skill()
        self.edit(os.path.join(dst, "references", "collectors", "prompt.md"), "\n{RESUME}\n", "\nNote: {RESUME}\n")
        code, _, err = self.run_main(self.work, module=module)
        self.assertEqual(code, 1)
        self.assertIn("own line", err)

    def test_empty_reference_part(self):
        dst, module = self.copy_skill()
        with open(os.path.join(dst, "references", "collectors", "C.md"), "w") as fh:
            fh.write("\n\n")
        code, _, err = self.run_main(self.work, "--collectors", "C", module=module)
        self.assertEqual(code, 1)
        self.assertIn("empty reference file: references/collectors/C.md", err)


class StatusTests(Base):
    COMPLETE = ("- fact one\n  src: https://a | doc | p. 1 | accessed 2026-10-28\n"
                "- fact two\n  src: https://b | doc | §2 | accessed 2026-10-28\n\n"
                "## Gaps\n- none\n\n## Conflicts\n- none\n\n## Leads for B\n- x\n")

    def test_all_states(self):
        self.write("notes-A.md", self.COMPLETE)
        self.write("notes-B.md", "- fact\n  src: x\n\n## Gaps\n- y\n")       # cut off mid-way
        self.write("C/pdf/a.pdf", "x")                                       # raw files, no notes
        self.write("C/.hidden", "x")
        code, out, _ = self.run_main(self.work, "--status")
        self.assertEqual(code, 1)
        lines = {l[0]: l for l in out.splitlines() if l[:1] in "ABCD" and l[1:3] == "  "}
        self.assertIn("complete", lines["A"])
        self.assertIn("   2 facts", lines["A"])
        self.assertIn("incomplete", lines["B"])
        self.assertIn("missing lists: Conflicts, Leads", lines["B"])
        self.assertIn("missing", lines["C"])
        self.assertIn("   1 raw files", lines["C"])
        self.assertIn("1/4 complete", out)
        self.assertFalse(any(n.startswith("bundle-") for n in os.listdir(self.work)))   # builds nothing

    def test_heading_variants_and_exit_0(self):
        variants = ["**Gaps**\n**Conflicts**\n**Leads for A**\n",
                    "Gaps:\n- a\nConflicts:\n- b\nLeads:\n- c\n",
                    "1. Gaps\n2. Conflicts\n3. Leads for C\n",
                    "### gaps\n### conflicts\n### leads for d\n"]
        for letter, tail in zip("ABCD", variants):
            self.write(f"notes-{letter}.md", "- f\n  src: s\n\n" + tail)
        code, out, _ = self.run_main(self.work, "--status")
        self.assertEqual(code, 0, out)
        self.assertIn("4/4 complete", out)

    def test_words_inside_sentences_do_not_count(self):
        self.write("notes-A.md", "- the Gaps in coverage and Conflicts of interest and Leads to\n  src: s\n")
        code, out, _ = self.run_main(self.work, "--status", "--collectors", "A")
        self.assertEqual(code, 1)
        self.assertIn("incomplete", out)

    def test_subset_and_missing_work_dir(self):
        self.write("notes-D.md", self.COMPLETE)
        code, out, _ = self.run_main(self.work, "--status", "--collectors", "D")
        self.assertEqual(code, 0)
        self.assertIn("1/1 complete", out)
        code, _, err = self.run_main(os.path.join(self.tmp, "nope"), "--status")
        self.assertEqual(code, 1)
        self.assertIn("work dir not found", err)

    def test_status_needs_no_product_md(self):
        os.remove(os.path.join(self.work, "product.md"))
        code, out, _ = self.run_main(self.work, "--status")
        self.assertEqual(code, 1)
        self.assertIn("0/4 complete", out)


class LayoutTests(unittest.TestCase):
    def test_every_platform_and_collector_file_exists(self):
        for platform in ("common", "securitize", "superstate", "centrifuge", "midas", "ondo"):
            self.assertTrue(os.path.isfile(os.path.join(SKILL_DIR, "references", "sources", f"{platform}.md")), platform)
        for name in ("prompt", "rules", "A", "B", "C", "D"):
            self.assertTrue(os.path.isfile(os.path.join(SKILL_DIR, "references", "collectors", f"{name}.md")), name)
        self.assertLessEqual({"centrifuge", "midas", "ondo", "securitize", "superstate"}, set(bb.known_platforms()))
        self.assertNotIn("common", bb.known_platforms())


if __name__ == "__main__":
    unittest.main()
