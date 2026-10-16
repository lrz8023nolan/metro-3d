# Contributing

[English](CONTRIBUTING.md) | [中文](CONTRIBUTING.zh-CN.md)

Thanks for helping make accurate metro depth maps!

## Ways to contribute

- **Report data errors** (wrong depth, missing station, colour mismatch, wrong
  status) — open an issue and include a source link.
- **Add depth evidence** — the biggest gap: most Beijing underground stations
  are still estimated. Any documented figure with measure + source helps.
- **Improve the viewer** — keep it dependency-light (three.js only) and
  city-agnostic. For larger features, open an issue first.
- **Add a new city** — see below.

## Adding a city

1. Create `cities/<city-id>/` following [docs/schema.md](docs/schema.md):
   `city.json`, `build_config.json`, `terrain_grid.csv` and any per-line
   attribute table.
2. Run `python tests/validate_data.py` — it currently targets Beijing; extend
   it for your city (a `--city` flag is welcome).
3. Run `python scripts/build.py --city <city-id>` — it must produce
   `dist/<city-id>.html` without errors. If you can, run
   `node tests/verify_render.js`.
4. Open a PR that describes your data sources and their licenses.

## Data quality rules

- Every documented value needs **value + what it measures + source +
  confidence**. No naked numbers.
- Estimates must stay clearly marked as estimates in the UI — never silently
  mix them with sourced values.
- Coordinates are WGS-84. Never mix in GCJ-02.
- Don't redistribute copyrighted maps. Official network maps are usable as a
  cross-check reference only.

## Licensing of contributions

Code: MIT (see [LICENSE](LICENSE)).
Data: by submitting, you confirm it may be distributed under its source
license (ODbL / CC BY-SA / public domain, or your own clearly stated terms for
estimates), consistent with [docs/data-sources.md](docs/data-sources.md).
