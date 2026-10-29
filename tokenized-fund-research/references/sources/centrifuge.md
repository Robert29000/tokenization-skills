# Centrifuge — sources

Entity names and URLs were checked in October 2026. Re-verify them on every run; if this file
conflicts with a primary source, trust the primary source and record the change in Appendix A.

Products: JTRSY (Janus Henderson Anemoy Treasury Fund), JAAA (Janus Henderson Anemoy AAA CLO
Fund), deJAAA (wrapper), other Anemoy funds.

- **Docs**: `https://docs.centrifuge.io` — HTML returns 403 to scripts; use
  `https://docs.centrifuge.io/llms.txt`. API: `https://api.centrifuge.io` (GraphQL) for pool,
  tranche, NAV data.
- **Legal**: fund documents and decks are on IPFS (`https://ipfs.centrifuge.io/ipfs/<CID>`) —
  CIDs are linked from the Centrifuge app pool pages. Issuer: *Anemoy Capital SPC Limited*
  (BVI segregated portfolio company, BVI FSC); tokens are participating shares of a segregated
  portfolio. deJAAA is a separate wrapper token — describe both layers.
- **GitHub**: `https://github.com/centrifuge` — main repo `centrifuge/protocol`; audits in
  `centrifuge/protocol/tree/main/docs/audits`.
- **Forums**: Centrifuge's own forum `https://gov.centrifuge.io`; Aave Horizon (JTRSY, JAAA),
  Morpho, Euler.
