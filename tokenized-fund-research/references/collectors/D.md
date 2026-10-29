# Your task — collector D: Governance forums & curators

Collect what lending-protocol governance forums and risk curators say about the product. Follow the search recipe in the section "Governance Forums & Risk Curators" of this bundle.

1. Search all four forums (Aave, Morpho, Euler, Fluid) with `forum_search.py`, using the ticker, the issuer brand, and the underlying fund or manager name. Then search for curator authors with `@LlamaRisk` and similar.
2. Read every relevant thread **in full** with `--thread`, and save each dump as `D/thread-<forum>-<id>.txt`.
3. **Extract**, citing the per-post URL (`…/t/<slug>/<id>/<post_number>`) and naming the author:
   - facts the issuer disclosed in the thread (structure, entities, documents quoted with section / page)
   - curator legal and risk analysis: governing law, regulatory perimeter, bankruptcy remoteness, waterfall ranking, custodian pledges, admin keys, redemption limits
   - listing status and parameters for each protocol: proposed / live / rejected, LTV, liquidation threshold, caps, oracle
   - unresolved questions raised in the thread
4. If a product has no asset-specific thread (e.g. Horizon launch assets), say so explicitly and use the launch and weekly-update threads instead.
5. Fluid often has nothing. Record the search and its empty result under **Gaps**.

Curator statements are opinions. Record them as "<author> considers / recommends …".
