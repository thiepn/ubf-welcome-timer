# GitHub repository preparation — thiepn/ubf-welcome-timer

**Pre-upload status (verified 15 November 2026):** [`thiepn/ubf-welcome-timer`](https://github.com/thiepn/ubf-welcome-timer) exists and is public, with default branch configured as `main`. GitHub returned no files or branches; no initial commit exists. This preparation makes **no commit or upload**, and does not enable or deploy GitHub Pages. The Pages setting could not be read independently through the available GitHub connection.

## Proposed structure

For a separately authorized initial import, upload the **contents of this project folder as the repository root** (not the containing folder or ZIP) of the existing public `thiepn/ubf-welcome-timer` repository. The configured default branch is `main`; it will acquire its first commit on initial import.

The pages can later be served using GitHub Pages **Deploy from a branch → main → /(root)**, *only after separate deployment authorization and browser/projector release acceptance*. `.nojekyll` disables Jekyll processing of the static HTML site. The application uses `./` paths and works under `/ubf-welcome-timer/`. No build is needed.

## Prepared changes

- `.gitignore`, `.gitattributes`: protect local environment files and normalize source text; deliberately retain original PNG images.
- `.github/workflows/tests.yml`: CI runs on pushes to `main`, pull requests, or manual dispatch; includes JS unit tests, GitHub Pages path checks, and Chromium browser tests. Read-only repository token. **No upload, publish, or deploy steps.**
- `requirements-test.txt`: pinned browser test dependency.
- `.nojekyll`: disable Jekyll preprocessing.
- `tests/pages.test.js`: repository-prefix static path checks and matching asset dimensions.
- `tests/test_browser.py`: replaces fixed 1536-pixel assertion with real image-load and equal-dimension checks so future Canva exports can use other 16:9 resolutions.
- `ASSET_RIGHTS.md`: records the user's explicit publication-permission confirmation and its limits; no independent third-party license verification or software/image open-source license is implied.

Core app HTML/CSS/JS and local server are unchanged. The two provisional PNGs have now been replaced with the supplied Canva originals; the standalone logo is preserved as a non-rendered reference.

## Release blockers / constraints

1. **Asset permissions:** the user expressly confirmed permission to publish the included Canva-derived files in this public repository. That confirmation is recorded; independent verification of underlying third-party licenses was not performed, and no downstream reuse license is granted. See `ASSET_RIGHTS.md`.
2. `background-clean.png` is now the supplied original clean Canva export, aligned with `welcome.png`. **Projector visual acceptance is still required.**
3. Local Chromium is subject to `ERR_BLOCKED_BY_ADMINISTRATOR` on localhost; local browser acceptance did not pass. The pinned Playwright Chromium bundle was also unavailable. GitHub CI is prepared to run browser tests only after the existing empty repository receives its first source commit and the workflow runs; no CI result is claimed.
4. Windows extended-display and physical projector acceptance are outstanding.
5. A public `control.html` has no login. Same-profile browser state remains local: a visitor opening this page on another machine cannot operate the church projector, but the page is not access-controlled.
6. Public repository visibility exposes all committed images and source immediately, **even with GitHub Pages disabled**. Do not treat 'Pages disabled' as keeping repository contents private.
7. If GitHub Pages branch publication is enabled later, pushes to `main` may automatically deploy regardless of this test workflow's status. Do not enable Pages without separate authorization; the present Pages setting was not independently readable in this audit. A gated deployment workflow would be a separate change.
8. GitHub Pages hosting requires a network connection when opening/reloading pages without an offline cache. v1 supports already-loaded offline countdowns, not offline reopening. Keep a local server fallback for services.

## Local verification

```sh
npm test
python -m py_compile tests/test_browser.py
node --check server.mjs
```

Optional browser tests on a computer with unrestricted Chromium:

```sh
python -m pip install -r requirements-test.txt
python -m playwright install chromium
npm run test:browser
```

## Deliberately not included

- No GitHub Pages deployment workflow, publishing permissions, Pages artifact upload, secrets, CNAME, or production domain. This package does not create or modify the already-existing repository.
- No modifications to runtime countdown behavior or synchronization architecture.
- No automatic dependency installations during ordinary local operation.
