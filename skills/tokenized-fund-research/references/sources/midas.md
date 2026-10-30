# Midas — sources

Entity names and URLs were checked in October 2026. Re-verify them on every run; if this file
conflicts with a primary source, trust the primary source and record the change in Appendix A.

Products: mTBILL, mBASIS, mEDGE, mRe7YIELD, mF-ONE, mWIN, mGLO / mGLOBAL and others ("mTokens").

- **Docs**: `https://docs.midas.app` and `https://midas.app/legal` return 403 to scripts. The
  same GitBook content is served from **`https://midas-docs.gitbook.io`**, which works: it has
  `llms.txt`, `.md` page versions, and the PDF attachments (Final Terms) on GitBook's files host.
  The list of audits is at `docs.midas.app/resources/audits`.
- **Legal — two different structures; identify which one the product uses:**
  1. **EU prospectus certificates** (e.g. mTBILL, mBASIS): issuer *Midas Software GmbH*
     (Berlin, HRB 254645, LEI 984500BB00BN6D2B7C48). Base prospectus approved by Liechtenstein's
     **FMA** under the EU Prospectus Regulation and passported; renewed every year around 17 July.
     Each product has **Final Terms**, re-issued with each base prospectus. Always use the
     latest. As of Oct 2026, mTBILL (ISIN CH1371002986) runs under **Final Terms dated 17 Jul 2026**.
     These turned it into a **Swiss-law ledger-based security** (art. 973d CO, Zurich courts),
     name Maerki Baumann & Co. AG as custodian and Ankura Trust Company, LLC as security agent, and
     replace the earlier German-law terms. Earlier Final Terms (7 Oct 2024, 2025) are still useful
     for the change history. Public PDFs: MFSA mirror
     `mfsa.mt/wp-content/uploads/YYYY/MM/Midas-Software-GmbH-{Base-Prospectus|Final-Terms}-Document-dated-<date>.pdf`
     (Cloudflare challenge to curl — try WebFetch) and the AFM notified-prospectus register
     (`...details?id=12445`; lists notifications but has **no downloadable documents**).
     Midas Software GmbH's annual accounts (issuer solvency) are in the German
     Unternehmensregister.
  2. **Luxembourg securitisation notes** (e.g. mWIN, mGLO): notes issued from a compartment of
     an unregulated Luxembourg securitisation fund; management company held by the Midas
     Purpose Trust (Jersey); professional investors only, USD 130,000 authorised denomination
     (per LlamaRisk's mWIN review on the Aave forum). Information Memorandum / T&Cs are private —
     use risk-curator reviews that cite section and page numbers.
- **GitHub**: `https://github.com/midas-apps` (mToken, DepositVault, RedemptionVault, data
  feeds, greenlist / blacklist access control). The contracts repo has a per-chain address
  config (`addresses.ts`); use it to find every deployment. rwa.xyz covers only some chains and
  missed, for example, mTBILL on Etherlink.
- **Forums**: Aave Horizon ARFCs (mWIN topic 25536, mGLOBAL), Euler (mBASIS on Base, topic 1282),
  Morpho (Midas markets), Fluid.
