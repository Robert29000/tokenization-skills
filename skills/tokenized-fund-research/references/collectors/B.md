# Your task — collector B: Legal & regulatory

Collect what the legal documents and the regulators say. Your notes are the main source for report sections 3–6, so precision matters more than coverage.

1. **Offering documents**: offering memorandum / PPM, base prospectus + Final Terms, terms & conditions, trust agreement / articles, subscription agreement. Always use the **latest** version, and keep the earlier versions for the change history. Download the PDFs into `B/pdf/` and use the PDF tooling recorded in `product.md`.
2. **EDGAR** (US-offered products):
   `python3 -I "<scripts dir>/edgar_search.py" "<issuer legal name>" --forms D --details --user-agent-file "<work dir>/.sec-user-agent"`.
   `--details` gives the claimed exemptions, related persons (managers, directors), placement agent with CRD, minimum investment, amount sold and investor count. If `product.md` says `SEC_USER_AGENT: declined`, skip EDGAR and list it under **Gaps**. Don't copy the contact from that file into your notes or into a command line.
3. **Regulator registers** for every regulated entity: FMA, AFM, MFSA, BaFin, BVI FSC, CIMA, CSSF, SEC IAPD, FINRA BrokerCheck, GLEIF. When a register blocks scripts, use its official mirror before third-party sites (see "Regulator registers" in the common sources).
4. **Extract**, quoting the clause and giving section / page:
   - every named entity, with its role, full legal name, legal form, jurisdiction and licence
   - investor eligibility tests and minimums for each investor type; cumulative tests (e.g. QP *and* AI) stated as such
   - excluded jurisdictions
   - transfer restrictions and secondary-market rules
   - what the holder legally owns (share / trust interest / certificate / note / wrapper), and the claim chain
   - investor rights: voting, redemption, distributions, information, transfer, claim in insolvency
   - issuer powers: compulsory redemption, suspension, gating, haircut / write-down, freeze / burn, upgrade / pause, unilateral amendment. Say whether each has been exercised.
   - bankruptcy remoteness, segregation, limited recourse, non-petition, security interests
   - governing law and courts for each document
   - reporting, NAV and disclosure duties; complaint and dispute channels
   - the issuer's own financial statements, when it is the debtor (certificates and notes)
   - other filings by the issuer, its trust or its sponsor: other series, and registration statements (N-1A, S-1) with whether they became effective

The investor-category and role definitions are in this bundle ("Investor Categories & Regulators by Jurisdiction", "Roles Catalogue"). Use them to name things consistently, but always quote the product's own definitions.
