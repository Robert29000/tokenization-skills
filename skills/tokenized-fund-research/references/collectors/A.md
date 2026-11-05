# Your task — collector A: Issuer docs & data

Collect what the issuer and data providers publish about the product.

1. **Docs site**: try `llms.txt` and the `.md` page versions first. Read the product pages, the FAQ, and the subscription / redemption pages.
2. **Product page and factsheet**: AUM, NAV, yield, fees, minimums, subscription and redemption mechanics, settlement times, cut-offs.
3. **Eligibility and onboarding pages**: who may invest, supported and excluded countries, investor-type thresholds, required documents and how status is verified, minimums and waivers. These are leads for B to confirm against the offering documents.
4. **Portfolio composition**, with an as-of date: asset classes and allocation %, top holdings, maturity ladder, duration, cash buffer. If the issuer's product or transparency page is blocked or says nothing, go through the search order in the rules: the issuer's transparency / holdings API, proof-of-reserve and attestation reports and the repositories that produce them (you own these on GitHub too), then third-party reserve monitors and research that quote the issuer's data. Record which layer each figure comes from and whether an attestation covers the holdings or only the total.
5. **Issuer API**, if there is one (e.g. Superstate's NAV and holdings endpoints, a transparency or proof-of-reserve endpoint): primary data for NAV and holdings.
6. **rwa.xyz / DeFiLlama**: AUM, holder count, chains, contract addresses, holder concentration. Cite these only for on-chain metrics; their service-provider fields can be stale.
7. **Third-party research**: Rating reports (S&P, Moody's, Particula…), attestation / proof-of-reserve reports, VaultStreet reports, reserve monitors. Cite them as secondary sources.
8. **Wayback Machine** snapshots, to date changes in manager, providers, fees or terms.
9. **News about the parties**: press releases and news on the sponsor, manager and main service providers, such as appointments and replacements, ownership stakes between them, mergers and enforcement actions. An ownership link between two parties is a conflict of interest for 3.3.

Your facts feed report sections 1, 2 (underlying assets), 4.2 (venues, concentration) and 6.3 (redemption, NAV, reporting). Service-provider names you find here are leads for B to confirm against the legal documents. Note them, but don't treat them as final. A link to an offering document you come across (a newer prospectus, Final Terms, a PPM copy) is a lead for B: write its full URL.

## Core items

1. **Portfolio composition**, with an as-of date: what the product actually holds (by instrument or asset class), not only its mandate.
2. **AUM and NAV per token**, with an as-of date, from the issuer, its attestation or reports.
