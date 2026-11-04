# {{Platform name}} — sources

Entity names and URLs were checked in {{Month YYYY}}. Re-verify them on every run; if this file
conflicts with a primary source, trust the primary source and record the change in Appendix A.

Products: {{TICKER (one-line description), … — add "and others" when the list is long}}.

- **Docs**: {{docs site URL; whether `llms.txt` and `.md` page versions exist; whether it blocks scripts (403 / bot challenge) and which mirror or fallback works instead; the eligibility / onboarding page}}
- **Public API**: {{NAV / holdings / pool endpoints and what they return, or "none found (looked at <where>)"}}
- **Legal**: {{issuer entities with full legal name, jurisdiction, LEI / EDGAR CIK; every EDGAR entity behind the products (trust, each series, sponsor), other series of the same trust, registration statements and whether they became effective, and look-alike entities not to confuse with the issuer; legal form of the tokens; where the offering documents live (public URL, IPFS, regulator mirror, or a gated portal plus its public substitutes); regulators and register entries, with the official mirror of any register that blocks scripts. When products use different structures, number them as midas.md does}}
- **GitHub**: {{org URL; the main repos; the main token contract address on each chain and where the full address list and audits are; a note when the deployed code is newer than the repo}}
- **Forums**: {{governance forums and known threads with topic ids, including the platform's own forum, or "none found (searched <the forums forum_search.py lists> on YYYY-MM-DD)"}}
