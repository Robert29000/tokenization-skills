# Report Template

Every report copies the skeleton below **verbatim** and replaces each `{{…}}` placeholder.
The structure is fixed so that reports on different products (e.g. Superstate USTB and Midas mTBILL)
can be compared line by line. `scripts/check_report.py` enforces it.

## Structural rules

1. **Headings are fixed.** Never rename, reorder, renumber or drop an H2/H3 heading. Do not add
   text to a heading (no "2.2 Portfolio Composition (as of June)"). Product-specific sub-topics
   go under **H4** (`####`) inside the relevant section.
2. **Fixed table rows are fixed.** Tables in 3.1, 4.2, 5.4, 5.5 and 6.3 start with a fixed list
   of rows in a fixed order. In 3.1 no other rows are allowed — product-specific roles go in 3.2.
   In 4.2, 5.4, 5.5 and 6.3 product-specific rows may be **appended after** the fixed rows.
3. **Fixed columns.** Never add, drop or rename a table column.
4. **Nothing is left blank.** A cell or section that does not apply says `N/A – <reason>`.
   Facts that should exist but could not be found say `Not disclosed in public documents`.
   Bare `N/A`, `-`, `TBD` or `?` are errors. **Whole row not applicable** (e.g. no sub-adviser):
   put `N/A – <reason>` in the first data cell (Entity / Detail) and `—` in every other cell,
   including Source, unless a source confirms the absence.
5. **Every claim is cited** with an inline number `[n]` (or `[n, m]`, `[n-m]`) that matches an
   entry in Appendix B. Every table has a `Source` column; use `—` only for rows that are `N/A`.
   Every Appendix B entry starts with its tier, `[P]` (primary) or `[S]` (secondary), as defined in
   `references/claim-check.md`. A legal claim backed only by `[S]` sources says who says it.
6. **Same field, same kind of value.** "Entity" cells always give the **full legal name**
   (e.g. "Midas Software GmbH", not "Midas"). Format: `Legal Name (short explanation)`, with
   several entities separated by `;`. Explanations go **only in parentheses**: text after a `;`
   is read as another entity name and needs its own H4 in 3.3. Contract and wallet addresses go
   in 3.3, not in the Entity cell. "Legal Form & Jurisdiction" always gives form +
   jurisdiction (e.g. "GmbH, Germany"; "Delaware statutory trust (series), US").
   "Regulator / Licence" names the regulator **and** the licence/registration type or says
   `Unregulated – <why>`.
7. **Facts from governance forums and risk curators** (Aave, Morpho, Euler, Fluid; LlamaRisk,
   Steakhouse, Chaos Labs, Gauntlet, Block Analitica…) are woven into the section they concern —
   there is no separate DeFi section. Name the author when quoting an opinion:
   "LlamaRisk notes that … [12]". Lending-protocol listings appear in 4.2 under *Eligible Venues*.
8. **Conflicts**: when two sources disagree, state both with citations in the body and add an
   entry in Appendix A.
9. **Dates**: give an "as of" date for every number that changes over time (AUM, NAV,
   allocation, holder counts) and an access date for every source.
10. **Exercised to Date?** (5.5) starts with `Yes`, `No`, `Partially`, `Unknown` or `N/A`,
   then optional detail. When a row covers more than one power (e.g. upgrade *and* pause, or a
   legal suspension power *and* an on-chain pause), give a status for each, worst first:
   `Partially – pause used 2025-03 [n]; upgrade never used`.
11. **Citation order**: number sources in order of first citation. After editing, run
   `check_report.py --renumber <report>`, which renumbers, sorts the citation groups and
   reorders Appendix B, keeping a `.bak` copy.

## Source priority (highest first)

1. Legal/offering documents: prospectus, Final Terms, PPM / offering memorandum, trust
   agreement, articles, subscription agreement, token terms.
2. Regulatory filings and registers: SEC EDGAR, FMA / AFM / MFSA registers, BVI FSC, CIMA, CSSF.
3. Audited financials, attestation and proof-of-reserve reports, rating reports.
4. Smart-contract code (GitHub) and on-chain state (block explorers).
5. Issuer docs sites and product pages, factsheets.
6. Governance-forum posts by the issuer (disclosures) and by risk curators (opinions).
7. Aggregators (rwa.xyz, DeFiLlama), press releases, news.

When a lower-priority source contradicts a higher-priority one, report the higher-priority fact
and mention the discrepancy in Appendix A.

## Skeleton

<!-- BEGIN SKELETON -->
# {{Product full name}} ({{TICKER}}) — Tokenized Fund Report

**Platform:** {{Securitize | Superstate | Centrifuge | Midas | Ondo | the platform's own name}}
**Ticker:** {{TICKER}}
**Token type:** {{e.g. "Participating share in a BVI segregated portfolio", "Debt certificate (EU prospectus)", "Beneficial interest in a Delaware statutory trust series", "Note", "ERC-4626 wrapper of …"}}
**Chains:** {{Ethereum (0x…), Solana (…), …}}
**Report date:** {{YYYY-MM-DD}}
**Data freshness:** {{as-of dates of the main data points, e.g. "Portfolio as of 2026-09-30; AUM as of 2026-10-27"}}

## 1. Intro

{{1–2 sentences, any format (prose or a single bullet pair): what the token legally is, which fund
or strategy it gives exposure to, who issues it, and for whom. Cite [n].}}

## 2. Underlying Assets

### 2.1 Mandate & Eligible Assets

{{Investment objective, eligible asset classes, concentration / duration / rating limits,
benchmark. For wrappers or fund-of-funds, add an H4 "#### Look-through" describing each layer down
to the final assets. Cite [n].}}

### 2.2 Portfolio Composition

{{As-of date, total AUM / NAV, number of holdings [n].}}

| Asset Class | Allocation (% of NAV) | Notes | Source |
|---|---|---|---|
| {{e.g. US Treasury bills}} | {{e.g. 92.4%}} | {{maturity range, issuer, rating}} | {{[n]}} |

{{Optional H4 sub-sections: "#### Top Holdings", "#### Maturity Ladder", "#### Credit Quality".
If the portfolio is not public, replace this whole section with
"N/A – <reason>" plus what *is* known about the mandate.}}

### 2.3 Leverage, Repo & Rehypothecation

{{Whether the fund may borrow, use repo / reverse repo, derivatives, securities lending; whether
underlying assets can be rehypothecated; current use. Cite [n].}}

### 2.4 Liquidity of the Underlying

{{How quickly the underlying assets can be turned into cash, redemption frequency of any
underlying fund, liquidity buffers, instant-liquidity facilities. Cite [n].}}

## 3. Key Roles & Legal Entities

### 3.1 Universal Roles

| Role | Entity | Legal Form & Jurisdiction | Regulator / Licence | Independence from Sponsor | Source |
|---|---|---|---|---|---|
| Sponsor / Tokenization Platform | {{full legal name}} | {{form, jurisdiction}} | {{regulator + licence}} | {{Principal / Affiliate / Independent + note}} | {{[n]}} |
| Issuer | {{legal entity whose security the token is}} | {{}} | {{}} | {{}} | {{[n]}} |
| Underlying Fund | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Investment Manager / Adviser | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Sub-Adviser | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Board / Directors / Trustee | {{name the governing body; a Delaware trustee that has only statutory duties goes here *and* gets a note in 3.3}} | {{}} | {{}} | {{}} | {{[n]}} |
| Fund Administrator / NAV Calculation Agent | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Transfer Agent / Registrar | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Custodian (Underlying Assets) | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Token Custody / Key Management | {{MPC / multisig / wallet provider holding admin & treasury keys}} | {{}} | {{}} | {{}} | {{[n]}} |
| Distributor / Placement Agent / Broker-Dealer | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Auditor | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| Legal Counsel | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| NAV Oracle / Pricing Provider | {{}} | {{}} | {{}} | {{}} | {{[n]}} |
| KYC / AML Provider | {{}} | {{}} | {{}} | {{}} | {{[n]}} |

### 3.2 Product-Specific Roles

> **Note:** {{Why this product needs roles beyond the universal set, e.g. "mTBILL is a debt
> certificate under an EU base prospectus, so it has a security trustee, paying agent and
> calculation agent that a fund share does not need." See references/roles.md for the catalogue.}}

| Role | Entity | Legal Form & Jurisdiction | Regulator / Licence | Why This Role Exists | Source |
|---|---|---|---|---|---|
| {{e.g. Security Trustee}} | {{}} | {{}} | {{}} | {{}} | {{[n]}} |

{{If the product has no roles beyond the universal set, replace the note and table with
"N/A – <reason>".}}

### 3.3 Entity Responsibilities

{{One H4 per entity named in 3.1 / 3.2 (an entity holding several roles gets one H4), in the
same order as the tables:

#### <Full legal name> — <Role(s)>

- **Scope:** what it does and decides.
- **On-chain powers:** mint / burn / pause / freeze / upgrade / allowlist / oracle update — with
  the controlling address or multisig and threshold if known.
- **Liability & standard of care:** what the documents say it is (not) liable for.
- **Conflicts of interest:** affiliations, fee arrangements.

Cite [n] on every bullet.}}

## 4. Who Can Invest

### 4.1 Primary Market Eligibility

| Investor Type | Legal Qualification | Jurisdiction (Allowed / Excluded) | Financial Requirements & Minimum | Onboarding / KYC | Source |
|---|---|---|---|---|---|
| {{e.g. US Qualified Purchaser}} | {{definition + legal basis, e.g. "ICA §2(a)(51); fund relies on §3(c)(7)"}} | {{allowed / excluded jurisdictions, sanctions lists}} | {{wealth / income / asset test + minimum subscription}} | {{KYC/KYB, accreditation verification, wallet allowlisting}} | {{[n]}} |

{{One row per investor type the documents admit. Use the categories in
references/investor-frameworks.md. When tests are **cumulative** (e.g. a 3(c)(7) + 506(c) fund
needs investors who are both Qualified Purchasers and Accredited Investors), write one row named
after the stricter category with the other one stated, e.g. "US Qualified Purchaser (must also be
Accredited Investor)", and give both tests in Legal Qualification. Use separate rows only for
alternative routes (e.g. US QP *or* non-US professional under Reg S). Then, if needed, add H4 notes
on how eligibility is verified.}}

### 4.2 Secondary Market

| Aspect | Detail | Source |
|---|---|---|
| Transfer Restrictions | {{legal transfer restrictions from the documents}} | {{[n]}} |
| Allowlist Enforcement | {{how the smart contract enforces it: allowlist / whitelist / none; who manages it}} | {{[n]}} |
| Eligible Venues | {{ATS, DEX pools, lending protocols (Aave Horizon, Morpho, Euler, Fluid…) with status}} | {{[n]}} |
| Lock-up / Holding Period | {{e.g. Reg S distribution-compliance period, Rule 144}} | {{[n]}} |
| Secondary Buyer Eligibility | {{must buyers meet the same tests as primary subscribers? differences?}} | {{[n]}} |

## 5. Investor Ownership & Rights

### 5.1 What the Investor Owns

{{Exactly what the token represents legally: a direct share, a fractional share, a beneficial
interest in a trust series, a debt certificate / note, or a wrapper / derivative claim on shares.
Whether the token *is* the security or *evidences* it (and where the official register is).
Quote the defining clause. Cite [n].}}

### 5.2 Claim Chain

{{Text diagram from token holder to final assets, e.g.:}}

```
Token holder ──(holds)──> {{TICKER}} token ──(represents)──> {{instrument}} issued by {{Issuer}}
     └─> {{Issuer}} ──(invests in)──> {{Underlying fund / assets}} ──(held at)──> {{Custodian}}
```

{{One or two sentences on where the legal claim stops (e.g. limited recourse to a compartment). Cite [n].}}

### 5.3 Bankruptcy Remoteness & Recourse

{{Segregation of assets (SPC cell, trust series, securitisation compartment, SPV), limited
recourse and non-petition clauses, what happens if the sponsor / issuer / custodian becomes
insolvent, security interests held for investors. Cite [n].}}

### 5.4 Investor Rights

| Right | Held by Investor? | Detail | Source |
|---|---|---|---|
| Voting | {{Yes / No / Limited}} | {{}} | {{[n]}} |
| Redemption | {{}} | {{}} | {{[n]}} |
| Distributions / Income | {{}} | {{}} | {{[n]}} |
| Information & Reporting | {{}} | {{}} | {{[n]}} |
| Transfer | {{}} | {{}} | {{[n]}} |
| Claim on Assets in Insolvency | {{}} | {{}} | {{[n]}} |

### 5.5 Issuer Powers Limiting Investor Rights

| Power | Held By | Detail | Exercised to Date? | Source |
|---|---|---|---|---|
| Compulsory Redemption | {{}} | {{quote the clause}} | {{No / Yes – when}} | {{[n]}} |
| Suspension of Redemptions / NAV | {{}} | {{}} | {{}} | {{[n]}} |
| Gating / Redemption Limits | {{}} | {{}} | {{}} | {{[n]}} |
| Haircut / Write-down | {{}} | {{}} | {{}} | {{[n]}} |
| Token Freeze / Seizure / Burn | {{}} | {{on-chain role + legal basis}} | {{}} | {{[n]}} |
| Contract Upgrade / Pause | {{}} | {{proxy admin, timelock, multisig threshold}} | {{}} | {{[n]}} |
| Unilateral Amendment of Terms | {{}} | {{documents / terms changed without investor consent; a manager replacement or a change of service providers made without a vote belongs here too, with the date}} | {{}} | {{[n]}} |

## 6. Tokenized Fund's Obligations to Investors

### 6.1 Governing Law & Jurisdiction

| Document | Governing Law | Courts / Forum | Source |
|---|---|---|---|
| {{e.g. Base Prospectus / Terms and Conditions}} | {{}} | {{}} | {{[n]}} |

### 6.2 Regulators & Supervisory Bodies

| Regulator / Body | Jurisdiction | Scope of Oversight | Relevance to Investor | Source |
|---|---|---|---|---|
| {{e.g. SEC}} | {{}} | {{which entity / activity it supervises}} | {{what protection this gives the investor, or why it gives none}} | {{[n]}} |

{{After the table: the investor-protection regime that applies (e.g. 1940 Act exemption and its
consequences, EU Prospectus Regulation liability, PRIIPs KID, MiFID II product governance,
deposit / investor compensation schemes — usually *not* available) and what is **not** protected.
Cite [n].}}

### 6.3 Obligations by Investor Type

| Obligation | Owed By | Investor Type(s) | Detail | Source |
|---|---|---|---|---|
| Redemption & Settlement | {{}} | {{}} | {{frequency, cut-off, settlement time, currency, fees}} | {{[n]}} |
| NAV Calculation & Publication | {{}} | {{}} | {{}} | {{[n]}} |
| Periodic Reporting | {{}} | {{}} | {{}} | {{[n]}} |
| Audited Financial Statements | {{}} | {{}} | {{}} | {{[n]}} |
| Disclosure of Material Changes | {{}} | {{}} | {{}} | {{[n]}} |
| Offering / Investor Protection Documents | {{}} | {{}} | {{prospectus / PPM / KID delivered to whom}} | {{[n]}} |
| Complaints & Dispute Resolution | {{}} | {{}} | {{}} | {{[n]}} |

{{Where obligations differ by investor type (e.g. EU retail vs professional, direct holder vs
secondary-market holder, holder of a wrapper token), explain under H4 headings. Cite [n].}}

### 6.4 Investor Remedies

{{What an investor can actually do if the issuer fails its obligations: enforce against
collateral via trustee, sue in which court, regulator complaint, arbitration, ombudsman;
practical limits (limited recourse, non-petition, no direct claim against the underlying fund).
Cite [n].}}

## Appendix A. Open Questions & Conflicting Information

{{Numbered list: each conflicting or unverified fact, the sources on each side [n], and what
document would settle it. Also list every source that could not be accessed (403, gated
investor portal) and what it would have answered. If none, "N/A – no conflicts found".}}

## Appendix B. Sources

1. {{[P] or [S]}} {{Title — publisher — document section/page — URL — accessed YYYY-MM-DD}}
<!-- END SKELETON -->

## Self-check (before saving)

- [ ] Every H2/H3 heading is present, unchanged, in order.
- [ ] 3.1 has all 15 universal roles in order; nothing else.
- [ ] 3.2 has the Note + table, or `N/A – reason`.
- [ ] Every entity in 3.1/3.2 has an H4 in 3.3.
- [ ] 4.1 has a row for each investor type with legal, jurisdiction **and** financial requirements.
- [ ] 4.2 covers all five secondary-market aspects, including lending-protocol venues.
- [ ] 5.1 states exactly what the holder owns and quotes the defining clause.
- [ ] 5.5 states for every power whether it has been exercised.
- [ ] 6.2 names each regulator and what it does (and does not) protect.
- [ ] No `{{` placeholders remain; no bare `N/A`.
- [ ] Every `[n]` resolves to Appendix B; every source has a `[P]`/`[S]` tier and an access date; `--renumber` has been run.
- [ ] Every legal claim in sections 3–6 has a verdict in `claim-check.md`; ATTRIBUTED claims say who says it; REMOVED claims are gone.
- [ ] `python3 -I scripts/check_report.py reports/<file>.md` passes; if other reports exist, it
      also passes when run with one of them as a second argument.
