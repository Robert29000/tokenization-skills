# Tokenized Fund Research Skills

> AI skills that research tokenized funds and RWA tokens and write cited, comparable reports.

## Requirements

| Requirement | Status | Purpose |
|---|---|---|
| Python 3.9 or later, available as `python3` | Required | Runs the bundled scripts: forum and EDGAR search, bundle builder, report and sources checkers. The scripts use only the Python standard library; no packages need to be installed. Tested with Python 3.9, 3.10 and 3.13. |
| `curl` | Required | Downloads documents. It is included with macOS and most Linux distributions. |
| Poppler (`pdftotext`, `pdftoppm`) | Optional | Extracts text and pages from PDF offering documents, which substantially reduces the cost of reading long prospectuses. Install with `brew install poppler` (macOS) or `apt install poppler-utils` (Debian / Ubuntu). If Poppler is absent, the skill uses `pypdf` where installed, and otherwise relies on search snippets. |

## Install, Run & Update Prompts

Install:
```
Install https://github.com/Robert29000/tokenization-skills and research Midas mTBILL
Install https://github.com/Robert29000/tokenization-skills and add the Franklin Templeton platform to tokenized-fund-research
```

Run:
```
research Superstate USTB
write a tokenized fund report on Centrifuge JTRSY
add the Spiko platform to tokenized-fund-research
refresh the Ondo platform sources
```

Update:
```
update skills to latest version
```

## Skills

| Skill | Description |
|---|---|
| [tokenized-fund-research](skills/tokenized-fund-research) | One cited report per product: underlying assets, legal entities and roles, who can invest, investor rights and the fund's obligations. Four parallel collectors (issuer docs, legal, on-chain, forums); every legal claim is checked against a primary source |
| [tokenization-platform-fetch](skills/tokenization-platform-fetch) | Finds where a tokenization platform publishes its products, docs, legal documents, registers, GitHub and forum threads, and writes them as a short sources file. After your review, it can update tokenized-fund-research with it |

## How the skills work together

tokenized-fund-research ships sources for Securitize, Superstate, Centrifuge, Midas and Ondo. For any other platform:

1. tokenized-fund-research runs tokenization-platform-fetch first, so install both skills.
2. The fetch skill writes a draft to `reports/.work/platform-<slug>/sources.md` and checks it with `check_sources.py` for format and for hidden or unsafe content.
3. It shows you the diff and asks whether to update tokenized-fund-research. Nothing changes in the research skill without your yes.
   - **Update the skill**: the draft becomes `tokenized-fund-research/references/sources/<slug>.md`, and every later run on that platform uses it.
   - **Keep the draft only**: research runs keep using the draft from `reports/.work/`.

To refresh a platform the research skill already covers, ask for it (e.g. `refresh the Ondo platform sources`). The fetch skill re-checks every item and asks the same question.

## Governance forums

Each forum the skills search is one file, `skills/tokenized-fund-research/references/forums/<name>.md`: front matter with `base_url`, `engine: discourse` and optional `curators`, then what to look for on that forum. To add a forum, add a file; to remove one, delete it. `python3 -I skills/tokenized-fund-research/scripts/forum_search.py --list-forums` shows the current set.

## Tests

From the repository root:

```bash
python3 -I -B -m unittest discover -s tests/tokenized-fund-research
python3 -I -B -m unittest discover -s tests/tokenization-platform-fetch
```
