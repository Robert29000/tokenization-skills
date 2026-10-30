# Your task — collector D: Governance forums & curators

Collect what lending-protocol governance forums and risk curators say about the product. Follow the search recipe in the section "Governance Forums & Risk Curators" of this bundle.

1. Search the forums with `forum_search.py`, using the ticker, the issuer brand, and the underlying fund or manager name. It searches every forum in `references/forums/`; their files follow the "Governance Forums & Risk Curators" section of this bundle and say what to look for on each. Then search for curator authors with `--curators`.
2. Read every relevant thread **in full** with `--thread`, and save each dump as `D/thread-<forum>-<id>.txt`.
3. **Extract**, citing the per-post URL (`…/t/<slug>/<id>/<post_number>`) and naming the author:
   - facts the issuer disclosed in the thread (structure, entities, documents quoted with section / page)
   - curator legal and risk analysis: governing law, regulatory perimeter, bankruptcy remoteness, waterfall ranking, custodian pledges, admin keys, redemption limits
   - listing status and parameters for each protocol: proposed / live / rejected, LTV, liquidation threshold, caps, oracle
   - unresolved questions raised in the thread
4. If a product has no asset-specific thread on a forum, say so explicitly and use the other threads that forum's file points to, if any.
5. A forum with no relevant threads: record the search and its empty result under **Gaps**.
6. If the platform part of this bundle names a forum that has no file in `references/forums/` (e.g. the platform's own governance forum), `forum_search.py` can't reach it. List it under **Gaps** so a forum file can be added.

Curator statements are opinions. Record them as "<author> considers / recommends …".
