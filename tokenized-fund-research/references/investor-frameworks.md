# Investor Categories & Regulators by Jurisdiction

Use these definitions to fill section 4 (Who Can Invest) and section 6 (Obligations).
**This file is a starting point, not authority.** Every product's documents set their own tests,
and thresholds change. Quote the product's own definitions and cite them. Use this file only to
explain what a category means and to check the documents are consistent with it.

## How to read the offering

1. Find the **exemption or regime** the offering relies on. That decides who can invest.
   - US: the Form D "exemptions" line from `scripts/edgar_search.py` (506(b) / 506(c), 3(c)(1) / 3(c)(7)), Reg S legends, 1940 Act registration (N-1A / N-2).
   - EU: is there an approved prospectus (Prospectus Regulation) or an exemption (qualified investors only, ≥ EUR 100,000 denomination or per-investor minimum, < 150 persons per member state)? Is there a PRIIPs KID? (No KID usually means no retail distribution.)
   - Offshore (BVI / Cayman): the fund category (professional, private, incubator / approved, registered mutual fund) and its minimum subscription.
2. List **excluded jurisdictions**: US persons for Reg S offerings; sanctioned countries; often Canada, the UK, China, and others named in the documents.
3. Record the **minimum subscription** both as a legal floor and as the issuer's operational minimum, when they differ.
4. Record **onboarding**: KYC/KYB, accreditation verification method (self-certification vs third-party verification for 506(c)), wallet allowlisting.
5. Record **secondary-market rules**: can a token move to a non-allowlisted wallet? Must transferees meet the same tests? Are there lock-ups (Reg S distribution-compliance period, Rule 144 holding periods)?

## United States

| Category | Legal basis | Core test (summary; verify) |
|---|---|---|
| Accredited Investor (natural person) | Securities Act Rule 501(a) | Net worth > USD 1m excluding primary residence; or income > USD 200k (300k joint) in each of the last 2 years; or holds Series 7/65/82 |
| Accredited Investor (entity) | Rule 501(a) | E.g. total assets > USD 5m; all equity owners accredited; certain regulated institutions |
| Qualified Purchaser | Investment Company Act §2(a)(51) | Individuals / family companies with ≥ USD 5m investments; other entities ≥ USD 25m investments |
| Qualified Client | Advisers Act Rule 205-3 | Relevant for performance fees; AUM / net-worth thresholds (indexed) |
| Qualified Institutional Buyer (QIB) | Rule 144A | Institutions owning / investing ≥ USD 100m in securities (USD 10m for broker-dealers) |
| Non-US person (Reg S) | Regulation S | Offer and sale outside the US to non-US persons; distribution-compliance period restricts resale to US persons |
| Retail | 1940 Act-registered fund or registered offering | Only if the fund is registered (N-1A / N-2) or the offering is registered |

How the exemptions bear on eligibility:
- 506(b): no general solicitation; up to 35 sophisticated non-accredited investors.
- 506(c): general solicitation allowed; *all* purchasers must be accredited, and the issuer must take reasonable steps to verify that.
- 3(c)(1): ≤ 100 beneficial owners.
- 3(c)(7): all owners must be Qualified Purchasers.

Regulators and bodies:
- **SEC**: securities offerings, investment advisers (RIA), registered transfer agents, registered funds.
- **FINRA**: broker-dealers and ATS operators.
- **CFTC**: commodity pools, if the fund uses futures or swaps.
- **State regulators**: blue-sky notice filings; trust companies (e.g. NYDFS-chartered custodians).
- **FinCEN / OFAC**: AML programme and sanctions.

## European Union / EEA

| Category | Legal basis | Core test (summary; verify) |
|---|---|---|
| Professional client (per se) | MiFID II Annex II §I | Credit institutions, investment firms, insurers, funds and their managers, large undertakings meeting 2 of 3 tests (balance sheet ≥ EUR 20m, net turnover ≥ EUR 40m, own funds ≥ EUR 2m), governments, central banks |
| Elective professional client (opt-up) | MiFID II Annex II §II | 2 of 3: ≥ 10 significant trades per quarter over the last 4 quarters; portfolio > EUR 500k; ≥ 1 year working in the financial sector in a relevant role |
| Qualified investor | Prospectus Regulation Art. 2(e) | Professional clients and eligible counterparties |
| Retail client | MiFID II | Everyone else. Needs an approved prospectus for public offers, a PRIIPs KID for packaged products, and appropriateness / suitability tests from the distributor. |
| Well-informed investor (Luxembourg) | SIF / RAIF laws | Institutional, professional, or ≥ EUR 100k invested with a bank / firm certification |

Prospectus exemptions often relied on:
- Art. 1(4)(a): qualified investors only.
- Art. 1(4)(b): < 150 non-qualified persons per member state.
- Art. 1(4)(c)/(d): ≥ EUR 100,000 minimum per investor, or ≥ EUR 100,000 denomination.

Regulators and bodies:
- **National competent authorities**: BaFin (DE), FMA (LI), AFM (NL), CSSF (LU), AMF (FR), CBI (IE), MFSA (MT). The **home-member-state** authority approves a prospectus, and passporting notifies the host states. Prospectus approval is **not** supervision of the issuer's business.
- **ESMA**: coordination, registers.
- **MiCA**: applies to crypto-assets that are *not* financial instruments. Tokenized securities stay under MiFID II and the Prospectus Regulation. State which regime applies and why.
- **Luxembourg Securitisation Act 2004**: a securitisation undertaking is unregulated unless it issues to the public on a continuous basis (more than 3 issues a year), in which case the CSSF authorises it.

## Offshore fund jurisdictions

| Jurisdiction | Fund categories (summary; verify) | Regulator |
|---|---|---|
| British Virgin Islands | Professional Fund (professional investors only; minimum initial investment USD 100,000 for non-exempt investors); Private Fund (≤ 50 investors or private offer); Incubator / Approved Funds; Public Fund. Segregated Portfolio Companies under the BVI Business Companies Act. | BVI Financial Services Commission (FSC), under SIBA 2010 |
| Cayman Islands | Registered mutual fund under s.4(3) of the Mutual Funds Act (minimum initial investment per investor set by statute, around USD 100k / KYD 80k, verify); Private Funds Act funds; SPCs | Cayman Islands Monetary Authority (CIMA) |
| Bermuda | Professional / private / standard funds | Bermuda Monetary Authority (BMA) |
| Jersey | Expert / JPF funds; purpose trusts used as orphan owners | Jersey Financial Services Commission (JFSC) |

## Other

| Jurisdiction | Note |
|---|---|
| Switzerland | FinSA client segmentation (professional / institutional / retail); FINMA. A Swiss ISIN (e.g. CH…) on an EU certificate is just a numbering choice and doesn't by itself put the product under Swiss law. |
| Switzerland: ledger-based securities | Under the DLT Act (in force 2021), **art. 973d CO** lets a right exist *only* on a distributed ledger (*Registerwertrecht*), so transfer happens by ledger entry. The registration agreement and the terms set governing law and courts. Check who operates the ledger, what happens to holders if the ledger fails, and whether a FINMA-licensed DLT trading facility is involved (often not). Holders still need a FinSA prospectus or exemption for a Swiss public offer. |
| United Kingdom | FCA. Financial promotion restrictions (high-net-worth / sophisticated investor exemptions); most tokenized funds exclude UK retail. |
| Singapore | MAS. Accredited / institutional investor regime under the SFA. |

## Investor-protection checklist for section 6.2 / 6.3

For each investor type, say whether it has each of the following:
- An approved prospectus with statutory prospectus liability (EU), or anti-fraud liability only (US Rule 10b-5 applies to private placements too).
- Ongoing disclosure obligations (annual audited financials, NAV publication, material-change notices).
- Compensation schemes. These are usually **not** available: there is no SIPC or EU ICS cover for fund shares or notes held in self-custody.
- Supervision of the **entity** (fund / manager / transfer agent) versus supervision of the **document** only (prospectus approval).
- An ombudsman or complaints body, if any applies.
- The actual enforcement route: trustee enforcement, the courts named in the documents, arbitration.
