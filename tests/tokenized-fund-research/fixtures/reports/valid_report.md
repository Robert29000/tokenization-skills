# Example Treasury Fund (EXTB) — Tokenized Fund Report

**Platform:** Exampleplatform
**Ticker:** EXTB
**Token type:** Beneficial interest in a Delaware statutory trust series
**Chains:** Ethereum (0x0000000000000000000000000000000000000001)
**Report date:** 2026-10-28
**Data freshness:** Portfolio as of 2026-09-30; AUM as of 2026-10-27

## 1. Intro

EXTB is a token representing a beneficial interest in a series of Example Asset Trust, investing in short-dated US Treasury bills for US accredited investors [1].

## 2. Underlying Assets

### 2.1 Mandate & Eligible Assets

The series invests in US Treasury bills with maturities under 6 months [1, 2].

### 2.2 Portfolio Composition

As of 2026-09-30, AUM was USD 100m across 12 holdings [3].

| Asset Class | Allocation (% of NAV) | Notes | Source |
|---|---|---|---|
| US Treasury bills | 98.0% | 1–6 month maturities | [3] |
| Cash \| USD | 2.0% | Held at custodian | [3] |

#### Maturity Ladder

Not disclosed in public documents.

### 2.3 Leverage, Repo & Rehypothecation

The trust agreement prohibits borrowing and securities lending [2].

### 2.4 Liquidity of the Underlying

Treasury bills settle T+1; the fund redeems daily [2-3].

## 3. Key Roles & Legal Entities

### 3.1 Universal Roles

| Role | Entity | Legal Form & Jurisdiction | Regulator / Licence | Independence from Sponsor | Source |
|---|---|---|---|---|---|
| Sponsor / Tokenization Platform | Example Inc. | Corporation, Delaware, US | Unregulated – technology provider | Principal | [1, 2] |
| Issuer | Example Asset Trust – Series T | Delaware statutory trust (series), US | SEC – Form D filer (Rule 506(c)) | Affiliate | [4] |
| Underlying Fund | Example Asset Trust – Series T | Delaware statutory trust (series), US | SEC – Form D filer | Affiliate – same as Issuer | [4] |
| Investment Manager / Adviser | Example Advisers LLC | LLC, Delaware, US | SEC – registered investment adviser | Affiliate | [2] |
| Sub-Adviser | N/A – no sub-adviser appointed | N/A – no sub-adviser | N/A – no sub-adviser | N/A – no sub-adviser | — |
| Board / Directors / Trustee | Example Trust Company | Trust company, Delaware, US | Delaware Office of the State Bank Commissioner | Independent | [2] |
| Fund Administrator / NAV Calculation Agent | Admin Services Ltd | Ltd, Ireland | CBI – fund administrator | Independent | [2] |
| Transfer Agent / Registrar | Example Inc. | Corporation, Delaware, US | SEC – registered transfer agent | Principal | [2] |
| Custodian (Underlying Assets) | Custody Bank N.A. | National bank, US | OCC – national bank | Independent | [2] |
| Token Custody / Key Management | Not disclosed in public documents | Not disclosed in public documents | Not disclosed in public documents | Not disclosed in public documents | [5] |
| Distributor / Placement Agent / Broker-Dealer | N/A – direct subscription via issuer platform only | N/A – none | N/A – none | N/A – none | — |
| Auditor | Audit LLP | LLP, US | PCAOB – registered firm | Independent | [2] |
| Legal Counsel | Not disclosed in public documents | Not disclosed in public documents | Not disclosed in public documents | Not disclosed in public documents | [2] |
| NAV Oracle / Pricing Provider | Example Inc. (on-chain feed) | Corporation, Delaware, US | Unregulated – data publication | Principal | [5] |
| KYC / AML Provider | Example Inc. | Corporation, Delaware, US | FinCEN – AML programme | Principal | [1, 2] |

### 3.2 Product-Specific Roles

N/A – the trust series uses only the universal roles; no trustee, wrapper or liquidity provider is involved [2].

### 3.3 Entity Responsibilities

#### Example Inc. — Sponsor, Transfer Agent, NAV Oracle, KYC

- **Scope:** runs onboarding and keeps the register [2].
- **On-chain powers:** mint, burn, pause and allowlist via a 3-of-5 Safe [5].
- **Liability & standard of care:** liable for gross negligence only [2].
- **Conflicts of interest:** affiliate of the adviser [2].

#### Example Asset Trust – Series T — Issuer, Underlying Fund

- **Scope:** holds the portfolio [2].
- **On-chain powers:** none [5].
- **Liability & standard of care:** limited to series assets [2].
- **Conflicts of interest:** none disclosed [2].

#### Example Advisers LLC — Investment Manager / Adviser

- **Scope:** manages the portfolio [2].

#### Example Trust Company — Board / Directors / Trustee

- **Scope:** trustee of the trust [2].

#### Admin Services Ltd — Fund Administrator / NAV Calculation Agent

- **Scope:** strikes NAV daily [2].

#### Custody Bank N.A. — Custodian (Underlying Assets)

- **Scope:** holds the T-bills [2].

#### Audit LLP — Auditor

- **Scope:** audits annual statements [2].

## 4. Who Can Invest

### 4.1 Primary Market Eligibility

| Investor Type | Legal Qualification | Jurisdiction (Allowed / Excluded) | Financial Requirements & Minimum | Onboarding / KYC | Source |
|---|---|---|---|---|---|
| US Accredited Investor | Rule 501(a); offering relies on Rule 506(c) | US allowed; sanctioned countries excluded | Net worth > USD 1m; minimum USD 100,000 | KYC + third-party accreditation check | [4] |

### 4.2 Secondary Market

| Aspect | Detail | Source |
|---|---|---|
| Transfer Restrictions | Transfers only to other qualified holders | [2] |
| Allowlist Enforcement | Token contract checks an on-chain allowlist | [5] |
| Eligible Venues | Listed as collateral on a lending protocol (proposal stage) | [6] |
| Lock-up / Holding Period | N/A – no lock-up | — |
| Secondary Buyer Eligibility | Same tests as primary subscribers | [2] |

## 5. Investor Ownership & Rights

### 5.1 What the Investor Owns

A beneficial interest in Series T; the token evidences the interest and the transfer agent's register is authoritative [2].

### 5.2 Claim Chain

```
Holder ──> EXTB token ──> beneficial interest in Series T ──> T-bills at Custody Bank N.A.
```

The claim stops at Series T assets [2].

### 5.3 Bankruptcy Remoteness & Recourse

Delaware series liabilities are enforceable only against that series [2].

### 5.4 Investor Rights

| Right | Held by Investor? | Detail | Source |
|---|---|---|---|
| Voting | Limited | Only on fundamental changes | [2] |
| Redemption | Yes | Daily at NAV | [2] |
| Distributions / Income | No | Income accrues in NAV | [2] |
| Information & Reporting | Yes | Annual audited statements | [2] |
| Transfer | Limited | To allowlisted holders only | [2] |
| Claim on Assets in Insolvency | Yes | Pro rata on series assets | [2] |

### 5.5 Issuer Powers Limiting Investor Rights

| Power | Held By | Detail | Exercised to Date? | Source |
|---|---|---|---|---|
| Compulsory Redemption | Trustee | "for any reason" | No | [2] |
| Suspension of Redemptions / NAV | Trustee | Market closure | No | [2] |
| Gating / Redemption Limits | N/A – no gate in documents | N/A – none | N/A – none | — |
| Haircut / Write-down | N/A – not provided | N/A – none | N/A – none | — |
| Token Freeze / Seizure / Burn | Example Inc. | Freeze for sanctions | No | [5] |
| Contract Upgrade / Pause | Example Inc. | Proxy upgrade by Safe, no timelock | No | [5] |
| Unilateral Amendment of Terms | Trustee | With 30 days notice | No | [2] |

## 6. Tokenized Fund's Obligations to Investors

### 6.1 Governing Law & Jurisdiction

| Document | Governing Law | Courts / Forum | Source |
|---|---|---|---|
| Trust Agreement | Delaware | Delaware Court of Chancery | [2] |

### 6.2 Regulators & Supervisory Bodies

| Regulator / Body | Jurisdiction | Scope of Oversight | Relevance to Investor | Source |
|---|---|---|---|---|
| SEC | US | Adviser and transfer agent | Anti-fraud protection only | [4] |

The fund is not registered under the 1940 Act [4].

### 6.3 Obligations by Investor Type

| Obligation | Owed By | Investor Type(s) | Detail | Source |
|---|---|---|---|---|
| Redemption & Settlement | Trust | All | T+1 in USDC | [2] |
| NAV Calculation & Publication | Admin Services Ltd | All | Daily | [2] |
| Periodic Reporting | Trust | All | Monthly statements | [2] |
| Audited Financial Statements | Trust | All | Annual | [2] |
| Disclosure of Material Changes | Trust | All | 30 days notice | [2] |
| Offering / Investor Protection Documents | Trust | All | PPM at onboarding | [2] |
| Complaints & Dispute Resolution | Trust | All | Delaware courts | [2] |

### 6.4 Investor Remedies

Claims in the Delaware Court of Chancery against Series T assets [2].

## Appendix A. Open Questions & Conflicting Information

1. Key-management provider not disclosed [5].

## Appendix B. Sources

1. [S] Example product page — https://example.com/extb — accessed 2026-10-28
2. [P] Example Asset Trust Offering Memorandum, 2026-01-01 — §§1–9 — accessed 2026-10-28
3. [S] Example factsheet, September 2026 — https://example.com/extb.pdf — accessed 2026-10-28
4. [P] SEC EDGAR Form D, CIK 0000000001 — accessed 2026-10-28
5. [P] Etherscan token contract — https://etherscan.io/address/0x0000000000000000000000000000000000000001 — accessed 2026-10-28
6. [S] Lending protocol forum thread — https://governance.aave.com/t/example/1 — accessed 2026-10-28
