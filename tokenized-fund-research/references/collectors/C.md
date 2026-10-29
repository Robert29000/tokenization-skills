# Your task — collector C: GitHub & on-chain

Collect what the code and the chain show. Give the address and the chain for every on-chain fact, and the commit or file path for every code fact.

1. **GitHub org** (see the platform sources in this bundle; if they name none, search GitHub for the issuer and the token's contract name, and follow the explorer's verified-source links): find the token contract, the vaults (deposit / redemption), the oracle / NAV feed, the access-control contracts, and any per-chain address config.
2. **Token contract**:
   - transfer restrictions: allowlist / greenlist / blacklist logic, and whether transfers to a non-allowlisted wallet revert
   - roles: minter, burner, pauser, freezer, upgrader, allowlist manager
   - proxy pattern, proxy admin, timelock
   - supply cap, if any
3. **Block explorers**: every deployment on every chain, current role holders, multisig owners and threshold (Safe), EOAs vs contracts, holder concentration. Check that the deployed code matches the GitHub source (explorer "verified source"), and note it when the deployed version is newer than the repo.
4. **Oracle / NAV feed**: who publishes the price, from what source, how often, staleness checks, bounds.
5. **Instant-redemption paths**: contracts, liquidity providers, daily limits, fees.
6. **Audits and bug bounty**: auditors, dates, scope, unresolved findings; bug bounty platform and size.

Your facts feed report sections 3.3 (on-chain powers), 4.2 (allowlist enforcement), 5.5 (freeze / upgrade / pause powers) and 2.4 (instant liquidity).
