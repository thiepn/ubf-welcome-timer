# UBF Köln Projector Timer — Canva asset update verification

**Date:** 14 November 2026  
**Scope:** Replacing provisional slides with user-provided Canva PNG exports in the GitHub-prepared source package. No publication, deployment, repo creation or hosting changes.

## Completed checks

| Check | Result |
|---|---|
| New welcome PNG | **PASS** — actual user export installed at `assets/welcome.png` |
| New clean PNG | **PASS** — actual user export installed at `assets/background-clean.png` |
| Export dimensions | **PASS** — both 2048×1152, RGBA, 16:9 |
| Layer alignment | **PASS** — differences greater than 1 RGB channel value confined to title-removal region; see `ASSET_VERIFICATION.md` |
| Brand color | **PASS** — sampled Canva headline `#0F5EAB`, matches ring CSS |
| Standalone logo | **PASS** — preserved at `reference/ubf-logo-source.png`, not overlaid (logo already embedded) |
| Runtime/source preservation | **PASS** — 16/16 original runtime, browser test, and CI files byte-identical to previously prepared repository package |
| JavaScript syntax | **PASS** — Node `--check` of all runtime and Node test files |
| Python browser-test syntax | **PASS** — `py_compile` |
| Node unit, synchronization, and Pages compatibility tests | **PASS — 21/21** |
| Local HTTP serving, assets, HTML/CSS/JS | **PASS — 10/10** paths matched disk bytes |
| GitHub Pages subpath/static references | **PASS** — included in Node checks under `/ubf-welcome-timer/`; live hosting not tested |

## Not yet accepted

- **Actual Chromium browser interactions:** **BLOCKED**, not PASS. Initial `npm run test:browser` could not launch because the pinned Playwright Chromium bundle was absent. A second run with installed `/usr/bin/chromium` launched and attempted all six browser tests, but browser policy returned `net::ERR_BLOCKED_BY_ADMINISTRATOR` for `http://127.0.0.1:18765/display.html`, before any test could evaluate the application. These are environment restrictions, not proven product defects or passes.
- **Actual Windows extended-display / physical church projector:** **NOT TESTED**. Timer progress ring placement and fade visual fidelity must be checked on the real display.
- **GitHub Actions execution:** **NOT TESTED** — no repository action performed.
- **GitHub Pages production:** **NOT DEPLOYED**.
- **Public image redistribution rights (subsequent status update):** **USER-CONFIRMED**, not independently legally verified. The user explicitly confirmed permission to publish the included Canva-derived assets in the public repository. No license for downstream reuse is asserted. See `ASSET_RIGHTS.md`.

## Release status

**Source and images ready for a separately authorized initial repository import; live church use not yet accepted.** The clean Canva image requirement is resolved, the public repository exists but was confirmed empty, and the user has explicitly confirmed publication permission. Real-browser and physical-projector acceptance remain outstanding; no independent underlying-license audit is claimed. No publishing or deployment was performed in the original asset update or this documentation-only correction.

## Pre-upload documentation update — 15 November 2026

- GitHub verification: `thiepn/ubf-welcome-timer` exists and is public, default branch configured as `main`; the Contents API reported “This repository is empty” and the branches endpoint returned `[]`. No repository write was made.
- User confirmation: permission to publish the included Canva-derived assets in that repository was expressly confirmed; the scope and lack of independent licensing review are described in `ASSET_RIGHTS.md`.
- GitHub Pages settings could not be read through the available GitHub connection; no Pages action or deployment was performed.
- The 14 November results above are preserved as historical test evidence. Fresh test results for the documentation-only package must be reported separately in the handoff.

### Fresh checks for this documentation-only package (15 November 2026)

| Check | Result |
|---|---|
| Original ZIP comparison | **PASS** — exactly five Markdown documents changed; all other 24 files byte-identical |
| `npm test` | **PASS — 21/21** Node tests |
| JavaScript syntax (`node --check`) | **PASS** — runtime and Node test files |
| Python browser-test syntax (`py_compile`) | **PASS** |
| Local HTTP GET and exact response-byte matching | **PASS — 13/13** static resources |
| Playwright browser interactions | **BLOCKED**, not PASS — bundled Chromium executable missing; system Chromium launches but its managed policy rejects local navigation (`net::ERR_BLOCKED_BY_ADMINISTRATOR`); 0/6 scenarios exercised |
| Physical extended-display projector acceptance | **NOT TESTED** |
| GitHub Actions | **NOT RUN** — repository still empty at last read |

These checks do not authorize uploading, committing or deploying. Existing source, image and test files remain unchanged.
