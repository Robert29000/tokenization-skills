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
   - **Scanned pages have no text.** Signed pages, auditor's opinions and annexes are often
     images, and `pdftotext` returns nothing for them. Check the word count per page
     (`pdftotext -f N -l N file.pdf - | wc -w`). For every page with 0 words, render it
     (`pdftoppm -f N -l N -r 70 -png file.pdf <your folder>/pages/p`) and read the image. A
     text search of `pdftotext` output is not proof that something is absent: before you
     write that a document "contains no" clause, opinion or signature, read its image-only pages.
     Without `pdftoppm`, list the image-only pages under Gaps.
   - Record document name, date, page / section number for every fact.
3. **403 / 406 / bot protection.** Known blockers as of Oct 2026: `docs.midas.app`, Centrifuge
   HTML docs, DeFiLlama, BrokerCheck / IAPD, `invesco.com` (406 to curl), and MFSA (a Cloudflare
   challenge to curl; try WebFetch). Fall back in the search order of the collector rules and
   record which step worked: llms.txt / `.md` → official mirror (regulator register, IPFS,
   EDGAR) → the issuer's own data endpoints and repositories → web and GitHub search for the
   exact title, file name or ISIN with the year → third parties that quote or mirror it
   (secondary) → record as "not accessible" in Appendix A. Never get past a bot check
   (no spoofed User-Agent, no headless browser).
4. **Gated investor portals** (Securitize investor onboarding, data rooms): never try to log in.
   Use public copies (EDGAR, regulator registers, forum posts where the issuer quoted the
   documents, risk-curator reviews that cite section numbers) and list the gated document as
   unread in Appendix A.
5. **Rate limits**: on HTTP 429 or a result capped at the API's maximum, back off, narrow the
   query and switch endpoint (another public RPC or explorer) before recording a gap.

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
| Issuer transparency / proof-of-reserve data | the issuer's transparency or holdings API (often what its product page calls in the browser), its proof-of-reserve repository on GitHub (token config, attestation records), on-chain attestation contracts | portfolio composition and reserves when the product page is blocked; say whether an attestation covers the holdings or only the total |
| Third-party mirrors and reserve monitors | GitHub search for issues and pull requests (`https://api.github.com/search/issues?q="<file name or product>"` works without a token; code search needs one, so use a web search with `site:github.com`), reserve monitors and dashboards that quote issuer APIs, research write-ups that link documents | copies or links of blocked offering documents and portfolio data. Always secondary: say who quotes whom, and fetch the original from the link they give when it works |

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
