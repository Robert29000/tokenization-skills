# Securitize — sources

Entity names and URLs were checked in October 2026. Re-verify them on every run; if this file
conflicts with a primary source, trust the primary source and record the change in Appendix A.

Products: BUIDL (BlackRock), ACRED (Apollo), VBILL (VanEck), STAC (BNY / AAA CLO), sBUIDL and
other wrappers, Hamilton Lane / KKR feeder funds, HINC (Neuberger).

- **Docs**: no public docs site (`docs.securitize.io` returns 404). Use `securitize.io` product
  pages, `securitize.io/learn`, and the developer API docs `sec-connect-api-docs.securitize.io`.
- **Legal documents** sit behind investor onboarding or on the asset manager's site. Public
  copies: EDGAR Form D (exemptions claimed → eligibility), manager press releases, risk-curator
  reviews on forums (they often quote PPM sections).
- **Known entities** (verify):
  - BUIDL: *BlackRock USD Institutional Digital Liquidity Fund Ltd.*, BVI, EDGAR CIK 2013810;
    Form D claims Rule 506(c) + ICA §3(c)(7).
  - ACRED: *Securitize Tokenized Apollo Diversified Credit Fund, Ltd.* (BVI feeder).
  - STAC: *Securitize AAA CLO Tokenized Fund, Ltd.*; BNY as custodian / sub-adviser.
  - Securitize LLC — SEC-registered transfer agent; Securitize Markets, LLC — FINRA broker-dealer
    operating an ATS (check BrokerCheck); Securitize Holdings, Inc. — public holding company
    (S-1 / S-4 filings on EDGAR, CIK 2094496, 2025–26).
- **GitHub**: `https://github.com/securitize-io` (DS Protocol token contracts, compliance
  service / registry service — look for transfer-restriction and lock-up logic).
- **Forums**: Aave Horizon ARFCs (VBILL, HINC…), Euler (sBUIDL, Securitize markets), Morpho.
