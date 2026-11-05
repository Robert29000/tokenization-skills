# Your task — collector B: Legal & regulatory

Collect what the legal documents and the regulators say. Your notes are the main source for report sections 3–6, so precision matters more than coverage.

1. **Find the current version first.** Before extracting anything, establish which offering documents are in force on the report date: the base document (base prospectus, offering memorandum / PPM, trust agreement) and the product terms (Final Terms, supplements, token terms).
   - Check the issuer's legal pages and the regulator registers. Approval and passport notifications show that a new version exists even when the register has no documents; a base prospectus also states its own validity end date.
   - When a newer version exists but isn't where you looked, go through the search order in the rules: other file hosts of the issuer, mirrors, a web and GitHub search for the exact title, file name or ISIN with the year, and third parties that link or quote it.
   - Write the result at the top of your notes: which version is current, its date, and where you got it. If you can't read the current version, say which version you used instead and mark the core item "Current offering documents" as `partial` or `not found`, so a follow-up run can chase it.
2. **Offering documents**: offering memorandum / PPM, base prospectus + Final Terms, terms & conditions, trust agreement / articles, subscription agreement. Use the current version from step 1, and keep the earlier versions for the change history. Download the PDFs into `B/pdf/` and use the PDF tooling recorded in `product.md`.
3. **EDGAR** (US-offered products):
   `python3 -I "<scripts dir>/edgar_search.py" "<issuer legal name>" --forms D --details --user-agent-file "<work dir>/.sec-user-agent"`.
   `--details` gives the claimed exemptions, related persons (managers, directors), placement agent with CRD, minimum investment, amount sold and investor count. If `product.md` says `SEC_USER_AGENT: declined`, skip EDGAR and list it under **Gaps**. Don't copy the contact from that file into your notes or into a command line.
4. **Regulator registers** for every regulated entity: FMA, AFM, MFSA, BaFin, BVI FSC, CIMA, CSSF, SEC IAPD, FINRA BrokerCheck, GLEIF. When a register blocks scripts, use its official mirror before third-party sites (see "Regulator registers" in the common sources).
5. **Extract**, quoting the clause and giving section / page:
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

## Core items

1. **Current offering documents**: the base document and the product terms in force on the report date, read in full (step 1).
2. **What the holder owns and the governing law**: legal form of the token, issuer, governing law and courts, quoted from the current documents.
3. **Issuer powers**: compulsory redemption, suspension, gating, write-down, freeze / burn, upgrade, unilateral amendment, each quoted, with whether it has been exercised.
