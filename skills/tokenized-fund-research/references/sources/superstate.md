# Superstate — sources

Entity names and URLs were checked in October 2026. Re-verify them on every run; if this file
conflicts with a primary source, trust the primary source and record the change in Appendix A.

Products: USTB (short-duration US Treasuries), USCC (crypto carry, managed by Bitwise), plus
newer series of the same trust (e.g. VBDC, the Valinor BDC Exposure Fund, and CUSHY). List the
current series with `edgar_search.py "Superstate Asset Trust" --forms D`.

- **Docs**: `https://docs.superstate.com` (Investors / Issuers / Integration partners);
  product pages `https://superstate.com/ustb`, `https://superstate.com/assets/<ticker>`;
  terms `https://superstate.com/terms`.
- **Public API**, a primary source for NAV and holdings:
  `https://api.superstate.com/v1/funds/1/nav-daily`, `https://api.superstate.com/v2/funds/1/holdings`
  (fund id 1 = USTB; find the ids of other series in the docs).
- **Legal**: each fund is a **series of Superstate Asset Trust**, a Delaware statutory trust.
  - USTB is the series at EDGAR CIK 2004367. Since mid-2026 it has been named *Invesco Short Duration US Government Securities Fund, a separate series of Superstate Asset Trust*; its earlier name was *Superstate Short Duration US Government Securities Fund*.
  - Its Form D claims Rule 506(c) + ICA §3(c)(7) and a USD 100,000 minimum. Use `--details` to see the current manager and portfolio managers.
  - CIK 1982577 is **Superstate Trust**, a different trust whose N-1A never became effective. Don't treat it as USTB's registration.
  - The PPM and Declaration of Trust are only available after onboarding. Use the Form D, VaultStreet and forum quotations instead, and list the PPM as unread in Appendix A.
- **Service providers change.** As of Oct 2026 the USTB run found:
  - investment manager Invesco Advisers, Inc. since 2026-06-01, replacing Superstate entities; a sub-adviser was shown until May 2026
  - placement agent Invesco Distributors, Inc.
  - transfer agent Superstate Services LLC
  - custodian The Bank of New York Mellon
  - auditor PwC since about July 2026, EY before
  - administrator NAV Fund Services
  - Delaware trustee CSC Delaware Trust Company

  Re-verify all of these every run. Use **Wayback Machine** snapshots of `superstate.com/ustb` (`https://web.archive.org/web/2026*/superstate.com/ustb*`) to date each change, and take the Form D over marketing pages.
- **GitHub**: `https://github.com/superstateinc` (token contracts with allowlist, continuous price oracle, redemption contracts). The deployed token version may be newer than the public repo; compare it with the verified source on the explorer.
- **Forums**: Morpho (Steakhouse vaults), Euler, and Aave Horizon. USTB and USCC were Horizon **launch assets**, so they have no individual ARFC or LlamaRisk asset review. Look for them in Horizon launch and weekly-update threads instead.
