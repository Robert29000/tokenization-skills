# Sources — common to all platforms

How to fetch, which cross-platform sources and registers to use, and how to reach pages that
block scripted fetches. The platform-specific sources are in `sources/<platform>.md`, or, for a
platform this skill doesn't cover yet, in the draft written by the tokenization-platform-fetch skill.
Entity names and URLs were checked in October 2026. **Re-verify them on every run**: issuers
rename entities, move documents and launch new share classes. If this file conflicts with a
primary source, trust the primary source and record the change in Appendix A.

## Fetching strategy (all platforms)

1. **Try machine-readable docs first**: `<docs-site>/llms.txt` (an index of every page) and the
   `.md` version of a page (append `.md` to the URL on GitBook / Mintlify sites).
2. **PDFs** (prospectus, PPM, Final Terms, audited financials):
   - Download into a fresh directory under your own collector folder, e.g.
     `curl -sL --max-filesize 100000000 -o reports/.work/<slug>/B/pdf/<name>.pdf <url>`. Choose
     the file name yourself (never `-O` / `-J`, which take it from the server), and don't unpack
     archives.
   - Use the PDF tooling recorded in `product.md`: `pdftotext -layout` when available. The Read
     tool's `pages` option needs `pdftoppm`; without it Read loads the whole PDF, which is
     expensive for a long prospectus.
   - Codex / shell: `pdftotext -layout file.pdf -` if installed, otherwise
     `python3 -c "import pypdf"` to check for pypdf. If neither exists, say so and fall back to
     search snippets.
   - Record document name, date, page / section number for every fact.
3. **403 / 406 / bot protection.** Known blockers as of Oct 2026: `docs.midas.app`, Centrifuge
   HTML docs, DeFiLlama, BrokerCheck / IAPD, `invesco.com` (406 to curl), and MFSA (a Cloudflare
   challenge to curl; try WebFetch). Fall back in this order and record which one worked:
   llms.txt / `.md` → official mirror (regulator register, IPFS, EDGAR) → web search with
   `site:` filter and quoted snippets → record as "not accessible" in Appendix A.
4. **Gated investor portals** (Securitize investor onboarding, data rooms): never try to log in.
   Use public copies (EDGAR, regulator registers, forum posts where the issuer quoted the
   documents, risk-curator reviews that cite section numbers) and list the gated document as
   unread in Appendix A.

## Cross-platform sources

| Source | URL / pattern | Use for |
|---|---|---|
| rwa.xyz | `https://app.rwa.xyz/assets/{TICKER}` (long slugs also work; the page data sits in the `<script id="__NEXT_DATA__">` JSON — curl the page and parse that instead of reading rendered HTML); `/platforms/{slug}`, `/asset-managers/{slug}` | AUM, holders, chains, contract addresses, issuer LEI / SEC CIK links. **Its service-provider fields (manager, custodian, auditor) can be stale** — the USTB run found all three wrong — so never cite rwa.xyz for a role; cite it only for on-chain metrics. |
| DeFiLlama RWA | `https://defillama.com/rwa/asset/{TICKER}` | fallback for metrics; returns 403 to curl and WebFetch, so only search snippets reach it — prefer rwa.xyz |
| Wayback Machine | `https://web.archive.org/web/<YYYY>*/<url>*`; raw snapshot `https://web.archive.org/web/<timestamp>id_/<url>` | dating changes of manager / provider / terms; recovering pages that changed |
| SEC EDGAR | `scripts/edgar_search.py "<entity>" --forms D` | US-offered funds: Form D (exemptions → investor eligibility), N-1A, 13F, S-1 |
| GLEIF LEI | `https://search.gleif.org/#/search/simpleSearch=<name>` | exact legal name, jurisdiction, registered address, parent |
| Block explorers | etherscan.io, basescan.org, arbiscan.io, solscan.io, stellar.expert, snowtrace.io | token contract, proxy admin, roles, multisig signers / threshold, holder concentration |
| Safe | `https://app.safe.global/home?safe=<chain>:<address>` | multisig threshold and owners |
| GitHub | see the platform sources | contract source, roles, allowlist logic, audits folder |
| Governance forums | `scripts/forum_search.py` — see `references/forums.md` | onboarding disclosures, risk-curator legal reviews |
| VaultStreet | `https://app.vaultstreet.com/research/{ticker-lowercase}` | independent research (USTB, JTRSY, JAAA, mWIN, mGLO covered as of Oct 2026) — cite as secondary |
| Attestations | e.g. Chronicle proof-of-asset dashboards, Chainlink PoR, auditor attestations | reserve verification |

### Regulator registers

| Regulator | Register | Typical use |
|---|---|---|
| SEC (US) | EDGAR; transfer-agent registrations via Form TA | fund filings, transfer-agent status |
| SEC IAPD (US) | `https://adviserinfo.sec.gov` | registered investment advisers (Form ADV) |
| FINRA (US) | `https://brokercheck.finra.org` | broker-dealer / ATS status. Both IAPD and BrokerCheck sit behind Cloudflare (a 307 challenge) for scripts. Use EDGAR as the official mirror: `edgar_search.py --submissions <CIK>` gives the firm's legal name, state, former names, filings and the SEC file numbers on them, and counts as [P]. A broker-dealer's 8- number shows on its X-17A-5 filings; an adviser's Form ADV is not on EDGAR, so its 801- number usually doesn't show. Find the CIK with a name search (`edgar_search.py "<firm>"`). CRD numbers from third-party sites are [S] |
| FMA (Liechtenstein) | `https://www.fma-li.li` — approved prospectuses | Midas base prospectus approval |
| AFM (Netherlands) | notified-prospectus register `afm.nl/en/sector/registers/meldingenregisters/genotificeerde-prospectussen` | passported EU prospectuses |
| MFSA (Malta) | `mfsa.mt/wp-content/uploads/YYYY/MM/<file>.pdf` | public PDF mirror of passported prospectuses |
| BaFin (Germany) | `https://portal.mvp.bafin.de/database/` | German entities, crypto custody licences |
| BVI FSC | `https://www.bvifsc.vg` — regulated entities search | BVI professional / private funds |
| CIMA (Cayman) | `https://www.cima.ky/search-entities-cima` | Cayman mutual / private funds |
| CSSF (Luxembourg) | `https://www.cssf.lu/en/entities/` | Luxembourg funds and authorised securitisation undertakings |
| Bermuda BMA, Jersey JFSC, Swiss FINMA | their entity search pages | when a structure uses those jurisdictions |
