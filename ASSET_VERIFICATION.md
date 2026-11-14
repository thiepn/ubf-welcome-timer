# Canva asset replacement verification (14 November 2026)

## Source material

- `assets/welcome.png`: original user-provided complete Canva export, **2048×1152**, RGBA.
- `assets/background-clean.png`: original user-provided clean Canva export, **2048×1152**, RGBA.
- `reference/ubf-logo-source.png`: supplied standalone logo, **1266×291**, RGB, retained for reference but not composited over the existing logo.

## Pixel-level findings

- Both slide exports have identical **16:9** dimensions.
- Pixels with an RGB channel difference **greater than 1** are confined to the text removal region: **x=117–1245, y=462–695** (coordinates in original 2048×1152 canvas).
- Only **585** other pixel positions show a difference of at most 1 channel value. Such subvisual differences do not indicate meaningful displacement of the background.
- Dominant sampled blue of the welcome heading: `RGB(15,94,171)`, or **`#0F5EAB`**, matching `css/display.css`.
- Existing overlay placement in CSS is proportional, not fixed to the original 1536×864 provisional image.

## SHA-256 provenance

| Source asset | SHA-256 |
|---|---|
| `assets/welcome.png` | `d57e8cdd480888c9290776736dbec11423aa089d1d27e49fda5bbec5d46d1df4` |
| `assets/background-clean.png` | `670aa1138d1b09e6179d7e18e2a405a9fa76d3b3679a9ec9b3be01f9c92d95e4` |
| `reference/ubf-logo-source.png` | `7de883ebafcc61f1b57dbd138a979743ed63c54b2e2178a83d8196480ef62b8c` |

## Scope and outstanding checks

Original HTML, CSS, timer logic, synchronization engine, and local server have **not** been changed for this asset update. The two embedded church-logo renderings are preserved as part of the slide assets; the standalone logo is not duplicated on screen.

The pixel comparison verifies exported slide alignment, **not** actual browser rendering or external projector alignment. Those remain separate acceptance gates. The user has since explicitly confirmed permission to publish the supplied Canva-derived files in `thiepn/ubf-welcome-timer` (see `ASSET_RIGHTS.md`); underlying third-party licenses were not independently audited. This documentation-only handoff does not upload or publish the assets.
