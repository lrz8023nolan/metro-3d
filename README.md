# metro-3d · Vertical metro maps

**English** | [**中文**](README.zh-CN.md)

> Vertical-exaggerated, single-file 3D metro maps — built entirely from open data.
> First city: **Beijing** — 29 lines · 424 stations · 541 platform instances.

![Beijing Subway 3D map](docs/images/iso.jpg)

## What is this

An interactive 3D map that shows a metro network as it actually sits in the
ground: every line is drawn at its real depth below the surface, with the
terrain as context. The idea follows Konstantin Dobrov's 3D Moscow Metro depth
map (and Yevgeny Varfalomeyev's 2013 original, whose method is publicly
documented) — this project adapts it to Beijing and generalizes it to any city.

- **Single file, fully offline** — `dist/beijing.html` (~1 MB) opens in any
  modern browser by double-click. three.js, the data and the app code are all
  inlined; no network, no API keys.
- **Real data, honest confidence** — geometry and stations from OpenStreetMap,
  ground elevation from SRTM, station depths curated from Wikipedia and media
  reports. Every documented depth carries its measure, source and confidence
  level; interpolated depths are marked `~` and flagged *estimated* in the UI.
- **Interaction**: drag / wheel zoom / right-drag pan · vertical-exaggeration
  slider · depth-emphasis slider · per-line toggles · station cards · three
  camera presets (iso / profile / top) · auto-rotate · label decluttering.

| Profile view | Depth ×80 | Station card |
|---|---|---|
| ![profile](docs/images/side.jpg) | ![depth](docs/images/depth.jpg) | ![card](docs/images/card.jpg) |

## Try it

- **Download & open**: grab [`dist/beijing.html`](dist/beijing.html) and
  double-click it. That's it.
- **GitHub Pages**: once Pages is enabled for this repo (branch `main`, `/root`),
  the viewer is served at `https://lrz8023nolan.github.io/metro-3d/`.

## Build from source

Requirements: Python 3.10+ (standard library only).

```bash
python scripts/build.py --city beijing
# → build/beijing_data.js   (intermediate runtime data)
# → dist/beijing.html       (single-file viewer)
```

Checks:

```bash
python tests/validate_data.py                     # schema + reference-integrity checks
npm install && node tests/verify_render.js        # headless render check (uses Edge/Chrome)
```

## Repository layout

```
viewer/    rendering layer (city-agnostic): app.js, template.html, vendored three.js r149
cities/    data layer, one package per city:
           city.json · build_config.json · terrain_grid.csv · wiki_line_stations.csv · manual/
scripts/   build.py / build_data.py / build_html.py
           collect/   original Beijing collection pipeline (kept for provenance)
dist/      built artifacts (committed): dist/beijing.html
docs/      schema, data sources, images
tests/     data validation + headless render verification
```

## Data model (short version)

Each city package has two inputs:

- **`city.json`** — the canonical dataset: `lines[]` (colour, geometry, station
  order) and `stations[]` (coordinates, elevation, laying type, opening date,
  depth + measure + source + confidence). Full spec: [docs/schema.md](docs/schema.md).
- **`build_config.json`** — build-time parameters for the depth model: truth
  mapping, depth anchors, per-line defaults, above-ground offsets.

The build derives each line's vertical profile (`track = ground + signed
offset`), interpolates along arc length, snaps every station onto the polyline,
and inlines everything into one HTML file.

## Data sources & licensing

| Data | Source | License |
|---|---|---|
| Line geometry, stations, stop order | OpenStreetMap (Overpass API) | ODbL 1.0 |
| Station attributes & depth evidence | Chinese Wikipedia | CC BY-SA 4.0 |
| Ground elevation / terrain grid | SRTM 30 m via OpenTopoData | public domain |
| Specific station depths | news & engineering reports (cited per value) | — |

Per-value citations, confidence framework and known caveats:
[docs/data-sources.md](docs/data-sources.md).
The full build record of the Beijing dataset (Chinese):
[docs/data-inventory.zh-CN.md](docs/data-inventory.zh-CN.md).

**License**: code (viewer + scripts) is MIT — see [LICENSE](LICENSE). Datasets
keep the upstream licenses above; keep the attribution if you reuse them.

## Roadmap

- [ ] Origin–destination route search with path highlighting
- [ ] Timeline (watch the network grow by year)
- [ ] Optional compliant basemap via a custom 3D layer
- [ ] More cities — the viewer is city-agnostic; a new city = a new data package

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- Concept: Konstantin Dobrov's 3D Moscow Metro depth map; Yevgeny
  Varfalomeyev's 2013 original.
- Built with [three.js](https://threejs.org/) r149 (MIT).
- Data: © OpenStreetMap contributors (ODbL) · Chinese Wikipedia (CC BY-SA) ·
  NASA/USGS SRTM.
