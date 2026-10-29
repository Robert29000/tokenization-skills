# Roles Catalogue

Section 3 of every report has two tables:
- **3.1 Universal Roles** has the same 15 rows, in the same order, for every product. That is what makes reports comparable.
- **3.2 Product-Specific Roles** holds anything else and opens with a note explaining why the structure needs those roles.

## 3.1 Universal roles: definitions and how to fill them

| # | Role (exact row label) | Who it is | How to fill it when it doesn't map 1:1 |
|---|---|---|---|
| 1 | Sponsor / Tokenization Platform | The brand that built and distributes the token (Securitize, Superstate, Centrifuge, Midas, Ondo) and its operating company | Name the operating legal entity, not the brand. If several group entities share the work, name the main one and list the rest in 3.3. |
| 2 | Issuer | The legal entity whose security the token *is* or *evidences* | Fund share → the fund (or SPC cell). Certificate / note → the note issuer. Wrapper → the wrapper issuer here, with the wrapped fund in row 3. |
| 3 | Underlying Fund | The pooled vehicle whose portfolio the investor is ultimately exposed to | Pick exactly one case: **(a)** the issuer is itself a fund (a fund share or trust series) → repeat the entity and add "(same as Issuer)"; **(b)** the issuer is a feeder or wrapper → give the master or wrapped fund; **(c)** the issuer is a note or certificate issuer with no fund, holding assets in a custody account → "N/A – the issuer holds the assets directly; see 2.2". |
| 4 | Investment Manager / Adviser | Entity with discretion over the portfolio | Give the registered adviser entity, e.g. an SEC RIA or an FCA / CSSF-authorised manager. |
| 5 | Sub-Adviser | A delegated manager | "N/A – no sub-adviser appointed" if none. |
| 6 | Board / Directors / Trustee | Governing body: fund board, trust trustee, management company of a securitisation fund | Name the entity, or name the directors (and say whether they are independent). |
| 7 | Fund Administrator / NAV Calculation Agent | Calculates NAV, keeps the books | If NAV is struck by a different party than the administrator, name both in the cell. |
| 8 | Transfer Agent / Registrar | Keeps the official register of holders | Say whether the on-chain ledger *is* the register or mirrors an off-chain one. |
| 9 | Custodian (Underlying Assets) | Holds the securities and cash | Name any sub-custodian or prime broker in 3.3. |
| 10 | Token Custody / Key Management | Holds the admin, minter and treasury keys, e.g. a multisig, MPC provider (Fireblocks, BitGo, Anchorage) or Safe | Give the multisig threshold if it's known. |
| 11 | Distributor / Placement Agent / Broker-Dealer | Markets and places the security; may run an ATS | "N/A – direct subscription via issuer platform only", if that's the case. |
| 12 | Auditor | Audits the financial statements of the fund or issuer | Smart-contract auditors go in 3.3 under the sponsor, not here. |
| 13 | Legal Counsel | Fund or issuer counsel named in the documents | "Not disclosed in public documents" is common. |
| 14 | NAV Oracle / Pricing Provider | Publishes the NAV or price on-chain (Chainlink, Chronicle, RedStone, the issuer's own feed) | Name both the data source and the on-chain publisher. |
| 15 | KYC / AML Provider | Runs investor onboarding checks | The sponsor itself, or a vendor (Sumsub, Persona, Jumio…). |

### Mapping for certificates and notes (no fund)

For a debt certificate or note (Midas EU mTokens, Ondo USDY), the issuer fills most of the fund roles itself. Keep every row and map it like this:

| Row | Write |
|---|---|
| Underlying Fund | `N/A – the issuer holds the collateral directly; see 2.1 Look-through` (name the funds or tokens held as collateral in 2.1 / 2.2, not here) |
| Investment Manager / Adviser | `N/A – no manager appointed; the issuer selects collateral` (or the named manager for "AMC" products) |
| Fund Administrator / NAV Calculation Agent | the **Calculation Agent** under the terms, often the issuer itself |
| Transfer Agent / Registrar | the entity keeping the register or securities ledger (for Swiss ledger-based securities, the ledger operator) |
| Board / Directors / Trustee | the issuer's managing directors, with names if published |

Give the issuer **one** H4 in 3.3 that lists all its roles, then a short bullet per role. Its scope, powers and liability usually differ by role.

Rules:
- One entity may hold several roles. Repeat its name in each row and give it a single H4 in 3.3.
- Use full legal names everywhere. Give the regulator *and* the licence type, e.g. "SEC – registered transfer agent" or "FMA – prospectus approval (not entity supervision)".
- **Independence from Sponsor** is always measured against **row 1** (the tokenization platform), even when the fund's manager belongs to a bigger group. It takes one of these values, plus a note:
  - `Principal`: this entity is the sponsor
  - `Affiliate`: same corporate group as the sponsor
  - `Related`: common founders or shareholders, but not a legal affiliate
  - `Independent`: no ownership link. Add the commercial tie if one exists, e.g. "Independent – contractual partner; manages the fund under an IMA with the trust"

  When the manager's group also fills other roles (e.g. Invesco Advisers as manager and Invesco Distributors as placement agent), point that out in the note and in 3.3 "Conflicts of interest".
- **Third-party providers whose legal form or licence isn't in the fund documents.** Look these up before writing "Not disclosed":

  | Provider | Where to look |
  |---|---|
  | Any entity | GLEIF LEI search: legal form, jurisdiction |
  | US advisers | SEC IAPD / Form ADV |
  | Broker-dealers | FINRA BrokerCheck, or the CRD from the Form D `--details` |
  | US banks / trust companies | FDIC BankFind, OCC, state charter |
  | Auditors | PCAOB firm search |
  | EU firms | the national register (BaFin, CSSF, CBI…) |

  If none of these resolves it, write `Not disclosed in public documents`.

## 3.2 Product-specific roles: catalogue

Use the exact labels below where they fit, so the same role reads the same way across reports.
Add a new label only when none of these fits.

| Role label | Typical in | Why it exists |
|---|---|---|
| Security Trustee / Collateral Agent | Debt certificates and notes (Midas EU certificates, Ondo USDY) | Holds security over the collateral for noteholders and enforces it if the issuer defaults |
| Paying Agent | Listed or prospectus notes | Makes payments to holders |
| Calculation Agent | Certificates and notes | Computes redemption amounts or the reference value under the terms |
| Management Company (Securitisation Fund) | Luxembourg securitisation funds (Midas mWIN / mGLO) | A securitisation *fund* has no legal personality and acts through its management company |
| Purpose Trust / Orphan Shareholder | Orphan SPV structures | Owns the issuer or management company so that no corporate parent can affect it (bankruptcy remoteness) |
| Segregated Portfolio (Cell) | BVI and Cayman SPCs (Anemoy) | The token is a share of one cell; that cell's assets are ring-fenced from the other cells |
| Wrapper Issuer / Vault Operator | deJAAA, sBUIDL, ERC-4626 wrappers | A second token layered on the fund share; adds its own issuer and its own risks |
| Feeder Fund | Tokenized feeders (ACRED) | The token is a share of a feeder that invests in a master fund |
| ATS Operator | Securitize Markets | Runs the regulated secondary venue |
| Instant Redemption Liquidity Provider | Midas Staked Liquidity, Grove Basin, Circle (BUIDL → USDC), Ondo instant redemptions | Provides same-block liquidity outside the fund's own redemption cycle; usually limited by size |
| Attestation / Proof-of-Reserve Provider | Chronicle, Chainlink PoR, accounting-firm attestations | Independently checks that the assets exist |
| Rating Agency | S&P, Moody's, Particula, ARC | Credit or fund rating |
| Bridge / Cross-Chain Messaging | Wormhole, LayerZero, CCIP, Axelar | Mints the token on other chains; adds bridge risk |
| Prime Broker / Repo Counterparty | Basis and carry strategies (mBASIS, USCC) | Supplies leverage or holds positions off-exchange |
| Exchange / Venue Custodian (Off-Exchange Settlement) | Crypto carry strategies | Holds collateral used on centralised exchanges |
| Underlying Product Issuer | Tokens whose fund buys other tokenized funds | Look-through layer (e.g. USDY holding OUSG, a vault holding BUIDL) |
| Stablecoin Settlement / USDC Custody | Funds that subscribe and redeem in USDC (Circle, a USDC custodian bank) | Subscription and redemption cash moves in a stablecoin, which adds issuer and custody risk on the cash leg |
| Delaware Trustee | Delaware statutory trusts (Superstate) | Statutory resident trustee with limited, ministerial duties. Name it here, or in 3.1 row 6 if no other governing body is named. |

## 3.3 Entity responsibilities: what each H4 covers

For each entity, in the order it appears in the tables:
1. **Scope**: the actions it takes and the decisions it makes under the documents.
2. **On-chain powers**: mint, burn, pause, freeze, force-transfer, allowlist management, oracle updates and upgrades. Give the address, the multisig threshold and any timelock.
3. **Liability & standard of care**: e.g. "liable only for gross negligence, wilful default or fraud"; indemnities the fund pays it.
4. **Conflicts of interest**: whether it is an affiliate of the sponsor, its fee arrangements, and whether it also acts for other products.
