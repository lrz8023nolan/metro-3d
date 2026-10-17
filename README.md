# metro-3d · 3D metro depth-map generator

**English** | [**中文**](README.zh-CN.md)

> Interactive 3D metro maps drawn the way the network actually sits underground:
> vertically exaggerated depth, terrain context, one self-contained HTML file.
> **Generic**: any city = a data package + one build command.
> Bundled example: **Beijing** — 29 lines · 424 stations · 541 platform instances (data as of 2026-10).

![Beijing Subway 3D map](docs/images/iso.jpg)

## What it is

- **Single file, fully offline** — `dist/beijing.html` (~1 MB) opens by double-click. three.js, data and app code are inlined; no network, no API keys.
- **Real data, honest confidence** — geometry and stations from OpenStreetMap, ground elevation from SRTM, depths curated from Wikipedia and media reports. Documented values carry measure + source + confidence; interpolated values are marked `~` and flagged *estimated* in the station card.
- **Interactive** — drag / wheel zoom / right-drag pan · vertical-exaggeration slider · depth-emphasis slider · per-line toggles · station cards · three camera presets (iso / profile / top) · label decluttering.
- **City-agnostic** — the viewer only reads the unified data format. Adding a city means adding a data package, not writing code.

| Profile view | Depth ×80 | Station card |
|---|---|---|
| ![profile](docs/images/side.jpg) | ![depth](docs/images/depth.jpg) | ![card](docs/images/card.jpg) |

## Quick start

| I want to… | Do this |
|---|---|
| **See it** | Open [`dist/beijing.html`](dist/beijing.html) (~1 MB, works offline); or the city index `dist/index.html` on GitHub Pages |
| **Build locally** | `python scripts/build.py --all`; on Windows just double-click [`build.cmd`](build.cmd) (builds and opens the index) |
| **Map my own city** | Create `cities/<city>/city.json` → `python scripts/build.py --city <city>`; minimal format: [schema](docs/schema.md), walkthrough: [usage](docs/usage.md) |

Requirements: Python 3.10+ (stdlib only). The render self-check needs Node.js + a local Edge/Chrome (optional).

## Usage (summary)

- **Panel**: vertical exaggeration (5–150×), depth emphasis (1–6×, underground only), terrain / labels / auto-rotate toggles, per-line toggles (show / hide all), three camera presets.
- **Mouse**: drag to orbit, wheel to zoom, right-drag (or Shift + drag) to pan, click a station for details.
- **Reading depths**: `34m` = documented (the card shows measure + source); `~31m` = estimated (low confidence); at-grade / elevated stations show no number.
- Full guide: [docs/usage.md](docs/usage.md).

## Repository layout

```
viewer/     rendering layer (city-agnostic): app.js, template.html, vendored three.js
cities/     data layer, one package per city:
            city.json (required) · build_config.json / terrain_grid.csv / wiki_line_stations.csv (optional)
scripts/    build.py (--city one / --all + city index) · build_data.py · build_html.py
            collect/ (Beijing collection pipeline, kept for provenance)
dist/       built artifacts: dist/beijing.html, dist/index.html
docs/       usage guide, schema, data sources, images
tests/      data validation (--city / --all) + headless render check (optional city argument)
build.cmd   one-click build + open (Windows)
```

## Data model (short version)

Two inputs per city package:

- **`city.json`** — canonical dataset: `lines[]` (colour, geometry, station order) and `stations[]` (coordinates, elevation, laying type, opening date, depth + measure + source + confidence). Spec: [docs/schema.md](docs/schema.md).
- **`build_config.json` (optional)** — depth-model parameters: truth mapping, depth anchors, per-line defaults, above-ground offsets. Missing file → built-in defaults.

The build derives each line's vertical profile (`track = ground + signed offset`), interpolates along arc length, snaps every station onto the polyline, and inlines everything into one HTML file.

## Data sources & licensing

| Data | Source | License |
|---|---|---|
| Line geometry, stations, stop order | OpenStreetMap (Overpass API) | ODbL 1.0 |
| Station attributes & depth evidence | Chinese Wikipedia | CC BY-SA 4.0 |
| Ground elevation / terrain grid | SRTM 30 m via OpenTopoData | public domain |
| Specific station depths | news & engineering reports (cited per value) | — |

Per-value citations, confidence framework and known caveats: [docs/data-sources.md](docs/data-sources.md). Full build record of the Beijing dataset (Chinese): [docs/data-inventory.zh-CN.md](docs/data-inventory.zh-CN.md).

**License**: code (viewer + scripts) is MIT — see [LICENSE](LICENSE). Datasets keep the upstream licenses above; keep the attribution if you reuse them.

## Roadmap

- [ ] Origin–destination route search with path highlighting
- [ ] Timeline (network growth by year)
- [ ] Optional compliant basemap via a custom 3D layer
- [ ] More cities (data packages welcome)

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- Concept: Konstantin Dobrov's 3D Moscow Metro depth map; Yevgeny Varfalomeyev's 2013 original.
- Built with [three.js](https://threejs.org/) r149 (MIT).
- Data: © OpenStreetMap contributors (ODbL) · Chinese Wikipedia (CC BY-SA) · NASA/USGS SRTM.
