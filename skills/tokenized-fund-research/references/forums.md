# Governance Forums & Risk Curators

Lending protocols publish asset-onboarding proposals and independent risk reviews. These often
contain facts the issuer does not put on its website: section and page references to private
offering documents, answers to due-diligence questions, admin-key setups, redemption limits and
holder concentration. Treat them as **secondary sources**. Cite the specific post
(`.../t/<slug>/<id>/<post_number>`), name its author, and prefer the primary document when the
post quotes one you can reach.

## Forums

Every forum the skill searches has its own file, `references/forums/<name>.md`. In this bundle those files follow this section, and each one says what to look for on that forum and who posts there. `forum_search.py` reads the same files and searches all of them by default. `--list-forums` prints their names, URLs and curator handles.

A forum file starts with front matter:

```
---
base_url: https://forum.example.org
engine: discourse
curators: LlamaRisk, steakhouse
---
```

- `base_url`: https and the host only, no path.
- `engine`: `discourse`, the only engine `forum_search.py` supports.
- `curators` (optional): forum usernames that `--curators` searches with `@<username>`.

To add a forum, add its file. To remove one, delete its file. Nothing else in the skill changes.

`forum_search.py` wraps these Discourse endpoints. Raw endpoints, if you need them:
- search: `<base>/search.json?q=<urlencoded>&page=<n>`. Terms must be at least 3 characters; the response has `topics`, `posts[].blurb` and `grouped_search_result.more_full_page_results`.
- topic: `<base>/t/<id>.json`. `post_stream.stream` lists all post ids, and only about 20 are loaded.
- more posts: `<base>/t/<id>/posts.json?post_ids[]=<id>&post_ids[]=<id>…`

`forum_search.py` spaces requests to the same forum by 0.5 s and retries HTTP 429 up to 6 times.
If you still get 429s (for example, several collectors searching at once), wait a minute and rerun
only the forums that failed, using `--forums <name>,<name>`.

## Search recipe

```bash
# 1. ticker + issuer + product name, one query per term, merged and de-duplicated
python3 -I scripts/forum_search.py <TICKER> "<Issuer brand>" "<Fund short name>"
# 2. ambiguous ticker? require several terms in one query (a forum file may suggest one)
python3 -I scripts/forum_search.py <TICKER> "<Issuer brand>" --all-terms
# 3. curator reviews: curators appear as post AUTHORS, so use Discourse's @user filter;
#    --curators runs "<TICKER> @<username>" for every curator in each forum's file
python3 -I scripts/forum_search.py <TICKER> --curators
# 4. read every relevant thread in full
python3 -I scripts/forum_search.py --thread <url> > reports/.work/<slug>/thread-<forum>-<id>.txt
```

A curator that a forum file names in prose but not in `curators:` has no known username there; search its name as a term instead.

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

Which forums each curator posts on is in the forum files. A forum file may name curators that are not listed here.

| Curator | Also publishes at | Notes |
|---|---|---|
| LlamaRisk | `llamarisk.com/research`; GitHub `llama-risk` | Most detailed legal reviews of RWA collateral. They often had NDA access to offering documents and cite section and page numbers. |
| Chaos Labs | — | Market-risk parameters (caps, LTV) |
| Steakhouse Financial | Steakhouse research | RWA vault curation and collateral views |
| Gauntlet | — | Parameter recommendations |
| Block Analitica, B.Protocol | Spark | Market-risk analysis |
| Objective Labs, Re7, MEV Capital, Sentora | — | Curator notes on vault integrations |

When a curator's opinion goes into the report, attribute it: "LlamaRisk recommends … [n]". Do not present it as a fact about the fund.
