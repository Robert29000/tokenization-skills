# Governance Forums & Risk Curators

Lending protocols publish asset-onboarding proposals and independent risk reviews. These often
contain facts the issuer does not put on its website: section and page references to private
offering documents, answers to due-diligence questions, admin-key setups, redemption limits and
holder concentration. Treat them as **secondary sources**. Cite the specific post
(`.../t/<slug>/<id>/<post_number>`), name its author, and prefer the primary document when the
post quotes one you can reach.

## Forums

All four run Discourse. `scripts/forum_search.py` wraps the endpoints below.

| Forum | Base URL | What to look for |
|---|---|---|
| Aave | `https://governance.aave.com` | `[ARFC] Onboard <TICKER> … to Aave Horizon` threads. **Horizon launch assets** (USTB, USCC, USYC, JAAA, JTRSY, VBILL) went live without individual ARFCs or LlamaRisk asset reviews; for these, look at the Horizon launch / weekly-highlights threads and say in the report that no asset-specific review exists. Since 2026 Horizon onboarding requires a business case, a **LlamaRisk risk assessment posted as a reply inside the ARFC thread**, an Aave Labs technical assessment and a Snapshot vote. Also "Horizon Weekly Highlights", "LlamaRisk – Monthly Community Update" and Chaos Labs parameter posts. |
| Morpho | `https://forum.morpho.org` | Curator vault whitelisting threads (Steakhouse "RWA-backed" vaults), the **Llama Risk** category, market listings that use the token as collateral. |
| Euler | `https://forum.euler.finance` | "Integrate <TICKER> on Euler <market>" and "Accept <token> as collateral" threads, Gauntlet / Objective Labs / risk-steward posts, Securitize-market threads. |
| Fluid | `https://gov.fluid.io` | Little RWA content so far. Search anyway and say "no threads found" if empty. |

Raw endpoints, if you need them:
- search: `<base>/search.json?q=<urlencoded>&page=<n>`. Terms must be at least 3 characters; the response has `topics`, `posts[].blurb` and `grouped_search_result.more_full_page_results`.
- topic: `<base>/t/<id>.json`. `post_stream.stream` lists all post ids, and only about 20 are loaded.
- more posts: `<base>/t/<id>/posts.json?post_ids[]=<id>&post_ids[]=<id>…`

`forum_search.py` spaces requests to the same forum by 0.5 s and retries HTTP 429 up to 6 times.
If you still get 429s (for example, several collectors searching at once), wait a minute and rerun
only the forums that failed, using `--forums aave,fluid`.

## Search recipe

```bash
# 1. ticker + issuer + product name, one query per term, merged and de-duplicated
python3 -I scripts/forum_search.py <TICKER> "<Issuer brand>" "<Fund short name>"
# 2. ambiguous ticker? require several terms in one query
python3 -I scripts/forum_search.py <TICKER> Horizon --all-terms
# 3. curator reviews: curators appear as post AUTHORS, so use Discourse's @user filter
python3 -I scripts/forum_search.py <TICKER> @LlamaRisk --all-terms --forums aave,morpho
python3 -I scripts/forum_search.py <TICKER> @steakhouse --all-terms --forums morpho
# 4. read every relevant thread in full
python3 -I scripts/forum_search.py --thread <url> > reports/.work/<slug>/thread-<forum>-<id>.txt
```

`--thread` prints a URL for every post (`…/t/<slug>/<id>/<post_number>`); cite those, not the
topic URL. Discourse treats a quoted multi-word term as separate words that must all match, not as
an exact phrase, so check that each hit is really relevant.

Results matched by more terms are listed first. Drop false positives. Common ones:
- a username that contains the term (e.g. "midapple" matching "Midas")
- unrelated projects with the same name (e.g. "Midas Capital" exploit threads)
- delegate-platform threads that only mention the asset in a vote rationale

Also search for the **underlying fund or manager** (e.g. "Wellington", "Janus Henderson", "BUIDL"). Wrapper and feeder products are often discussed under the underlying's name.

## What to extract (and where it goes in the report)

| Extract | Report section |
|---|---|
| Issuer's description of legal structure, entities, service providers | 3.1 / 3.2 / 3.3 (cross-check against legal docs) |
| Curator legal analysis: governing law, regulatory perimeter, bankruptcy remoteness, limited recourse, ranking in waterfall, custodian pledges | 5.1, 5.3, 6.1, 6.2 |
| Eligibility (professional / accredited only, denomination, greenlisting) and secondary-transfer rules | 4.1, 4.2 |
| Lending-protocol status: listed / proposed / rejected, LTV, liquidation threshold, supply cap, oracle | 4.2 → *Eligible Venues* row |
| Admin keys, multisig thresholds, timelocks, pause / freeze powers, upgradeability | 3.3 (on-chain powers), 5.5 |
| Redemption mechanics, instant-liquidity facilities and their limits, gating history | 2.4, 5.4, 6.3 |
| Holder concentration, AUM history | 2.2 (as-of date) or 4.2 |
| Curator opinion / recommendation (support, conditions, concerns) | the section the concern is about, quoted with attribution |
| Unresolved questions raised in the thread | Appendix A |

## Risk curators and reviewers

| Curator | Where they publish | Notes |
|---|---|---|
| LlamaRisk | Aave (in ARFC threads; monthly updates), Morpho (Llama Risk category); `llamarisk.com/research`; GitHub `llama-risk` | Most detailed legal reviews of RWA collateral. They often had NDA access to offering documents and cite section and page numbers. |
| Chaos Labs | Aave parameter recommendations | Market-risk parameters (caps, LTV) |
| Steakhouse Financial | Morpho vault threads, Steakhouse research | RWA vault curation and collateral views |
| Gauntlet | Euler, Morpho, Aave (historically) | Parameter recommendations |
| Block Analitica, B.Protocol | Morpho, Spark | Market-risk analysis |
| Objective Labs, Re7, MEV Capital, Sentora | Euler and Morpho vaults | Curator notes on integrations |
| Aave Labs / Aave Chan Initiative | Aave | Technical assessments, process updates |

When a curator's opinion goes into the report, attribute it: "LlamaRisk recommends … [n]". Do not present it as a fact about the fund.
