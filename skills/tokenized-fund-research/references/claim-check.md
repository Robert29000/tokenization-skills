# Legal Claim Check

Run this in Step 2, after the report is drafted and before `--renumber`. The goal is that every
**legal claim** the report makes is backed by the document that creates the obligation, quoted
precisely and current. A claim that fails a gate is **fixed, not defended**: you attribute it,
narrow it, date it or remove it.

You are checking your own draft. Read each claim as a sceptical counterparty would: "show me the
clause". A legal claim without a primary quote behind it reads as more certain than it is.

## Source tiers

Every Appendix B entry starts with its tier: `1. [P] …` or `1. [S] …`.

| Tier | Counts as | Examples |
|---|---|---|
| **[P] primary** | The document or register that creates or records the legal fact | prospectus, Final Terms, PPM / offering memorandum, trust agreement, articles, subscription agreement, token terms; SEC filings (Form D, N-1A); regulator registers (FMA, BaFin, CSSF, BVI FSC, FINRA, IAPD, GLEIF); court / commercial register entries; audited financial statements; for **on-chain** facts only: verified contract code and on-chain state |
| **[S] secondary** | Someone describing the legal fact | the issuer's website, docs and FAQ; factsheets; press releases; research (ratings, VaultStreet); risk-curator and forum posts, **even when they quote the documents**; aggregators (rwa.xyz, DeFiLlama); news |

The issuer's own docs site is **[S]** for legal claims. Marketing pages simplify, and they aren't
the terms you are bound by. A curator post that quotes "§8.2 p. 20" of a private memorandum is
still **[S]**: you have the curator's quote, not the document.

## What counts as a legal claim

Check every claim in these places:

| Section | Legal claims |
|---|---|
| 3.1 / 3.2 / 3.3 | an entity's role, full legal name, legal form, jurisdiction, regulator / licence; liability and standard of care |
| 4.1 / 4.2 | eligibility tests, thresholds, minimums, excluded jurisdictions, transfer restrictions, lock-ups |
| 5.1 / 5.3 | what the holder legally owns, the claim chain, segregation, limited recourse, non-petition, security interests, ranking |
| 5.4 / 5.5 | each right and each issuer power, and whether a power has been exercised |
| 6.1 – 6.4 | governing law, courts, regulators and what they supervise, every obligation and its terms, remedies |

Numbers that aren't legal terms (AUM, yield, holder counts) and on-chain facts are checked only
against Gate 1 with their own source type. Opinions, already attributed ("LlamaRisk considers …"),
skip the gates.

## The four gates

Run them in order. Once a claim fails a gate, apply that gate's fix; later gates still apply to the fixed claim.

### Gate 1 — Source

Does the claim cite at least one **[P]** source?

- Yes → continue.
- Only **[S]** sources → **ATTRIBUTE**: rewrite the claim so the reader sees who says it ("According to the issuer's docs [n], …", "LlamaRisk, quoting the Information Memorandum §8.2, reports that … [n]"). Add an Appendix A entry: "Not verified against a primary document: <claim> — <which document would settle it>".
- No source at all → **REMOVE**: replace it with `Not disclosed in public documents`, and record the gap in Appendix A.

### Gate 2 — Quote

Does a collector note hold a verbatim `quote:` from that primary source that supports the claim **exactly as written**?

- Yes → continue.
- The quote supports a narrower claim → **NARROW**: rewrite the claim to match the quote. Typical cases:
  - "may suspend" written as "will suspend"
  - "at its discretion" dropped
  - a power held "with trustee consent" written as unilateral
  - "professional investors" written as "institutional investors"
  - a minimum "per subscription" written as "per investor"
- There's no quote, only a paraphrase in the notes → go back to the source and get the quote. If the source can't be reached again, **ATTRIBUTE** to the collector's reading ("per the Final Terms as summarised in the collector notes") and log it in Appendix A.

### Gate 3 — Currency

Is the cited document the **current** version for the date of the report?

- Yes → continue.
- It was superseded (older Final Terms, a prior PPM, a renamed entity, a replaced service provider) → **DATE**: state the claim for the current document, or, if only the old one is available, date it ("Under the Final Terms of 7 Oct 2024 [n], …; whether the 2026 terms keep this is unverified") and log the question in Appendix A.

### Gate 4 — Conflict

Does any other source, of either tier, say something different?

- No → **CONFIRMED**.
- Yes → keep the higher-tier, more current claim. Mention the other one in the text ("rwa.xyz lists BlackRock Advisors as sub-adviser [n]; the Final Terms appoint none [m]") and add an Appendix A entry. Verdict: **CONFIRMED** if the primary source wins clearly, otherwise **ATTRIBUTE** both.

## Verdicts

| Verdict | Meaning | What the report shows |
|---|---|---|
| CONFIRMED | primary source, exact quote, current, no unresolved conflict | the claim as written |
| ATTRIBUTED | only secondary support, or the conflict can't be resolved | the claim, with who says it |
| NARROWED | rewritten to match the primary quote | the narrower claim |
| DATED | supported only by a superseded document | the claim, with its date and an Appendix A question |
| REMOVED | no support | `Not disclosed in public documents` plus an Appendix A entry |

## The log

Write `<work dir>/claim-check.md`, one row per checked claim, in report order:

```markdown
| Section | Claim (short) | Sources | Tier | Quote in notes | Current | Verdict | Change made |
|---|---|---|---|---|---|---|---|
| 3.1 Issuer | Midas Software GmbH, GmbH, Germany | [1], [18] | P | yes (FT §1) | yes | CONFIRMED | — |
| 5.5 Suspension | issuer may suspend redemptions | [4] | P | yes — "may, in its sole discretion" | yes | NARROWED | added "in its sole discretion" |
| 3.1 Sub-Adviser | BlackRock Advisors, LLC | [7] | S | no | — | ATTRIBUTED | "rwa.xyz lists …; Final Terms appoint none" |
```

End the log with the counts per verdict. The final reply to the user includes those counts.

`check_report.py` checks part of this mechanically:
- it warns when an Appendix B entry has no `[P]` / `[S]` tag
- it warns when a row of a legal table (3.1, 3.2, 4.1, 5.4, 5.5, 6.1, 6.2, 6.3) cites only `[S]` sources but doesn't say who says it ("per", "according to", "reported by", "states", "considers", "lists", "claims")
