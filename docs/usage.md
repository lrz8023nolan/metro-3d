# Usage guide

This page serves two audiences: people who just want to **look at the map**, and
people who want to **build a map for their own city**.

## 1. Three ways to use it

### 1.1 Open the built file

- Double-click `dist/beijing.html` — no installation, works offline.
- Or open `dist/index.html` (city index) on GitHub Pages and pick a city.

### 1.2 Build locally

```bash
python scripts/build.py --city beijing   # one city → dist/beijing.html
python scripts/build.py --all            # every city + dist/index.html (city index)
```

On Windows, double-clicking `build.cmd` is equivalent to `--all` and opens the
index when done.

### 1.3 Map a new city

1. Create `cities/<city-id>/` with a `city.json` (field spec: [schema](schema.md)).
2. Optional files: `build_config.json` (depth anchors / defaults),
   `terrain_grid.csv` (ground elevation), `wiki_line_stations.csv` (per-line
   station attributes). Missing files degrade gracefully.
3. Validate: `python tests/validate_data.py --city <city-id>`
4. Build: `python scripts/build.py --city <city-id>` → `dist/<city-id>.html`

## 2. Controls

| Action | How |
|---|---|
| Orbit | Drag with the left mouse button / one finger |
| Zoom | Wheel / pinch |
| Pan | Right-drag, or Shift + drag |
| Station details | Click a station dot |
| Camera presets | Panel → 斜视 (iso) / 剖面 (profile) / 俯视 (top) |
| Vertical scale | “垂直夸张” 5–150× (default 80); “埋深强化” 1–6× (default 3) applies to underground segments only |
| Display toggles | Terrain / labels / auto-rotate |
| Line toggles | Per-line chips in the panel; show-all / hide-all |

## 3. Reading the map

- **Numbers**: digits next to a station name are its depth. `34m` is documented (public engineering data); `~31m` is estimated (low confidence). At-grade / elevated stations show no number, only a small visual offset.
- **Measures differ**: the station card states what a documented number measures (slab / rail / station body / construction pit / unspecified) and where it comes from. Treat low-confidence figures with care.
- **Vertical exaggeration**: the vertical axis is stretched so underground depth is visible. Relative height differences along a line are real depth differences; lower the exaggeration to approximate true proportions.
- **Mountains**: the terrain surface is context only. In some cities (e.g. the Western Hills in Beijing) tall mountains are softly compressed for display.
- **Colours**: line colours come from each package's `colour` field, typically following the official network map.

## 4. Build & checks

```bash
python scripts/build.py --all                 # build every city + index page
python tests/validate_data.py --all           # static data validation
npm install && node tests/verify_render.js    # headless render check (optional; default beijing, city id as argument)
```

## 5. FAQ

**No street basemap?**
By design — the default build loads no online tiles: single file, offline, and
no basemap-compliance issues. A compliant basemap (Tencent / AMap / Baidu /
Tianditu) is on the roadmap as an optional layer.

**I only have station names and lines — no depths. Can I still build?**
Yes. `city.json` only needs names, coordinates, lines and stop order. Without
depths, underground stations fall back to a per-line default (20 m) and are
labelled *estimated*. Add depth anchors in `build_config.json` to improve.

**I want a new city but don't want to write code.**
Prepare `cities/<city>/city.json` as described in [schema](schema.md); the build
takes care of the rest.

**Coordinate system?**
WGS-84 everywhere. If you overlay a Chinese basemap, convert to GCJ-02 first and
follow that service's terms.

## 6. Data & licensing

Sources and per-value citations: [data-sources.md](data-sources.md). Code is MIT;
data keeps upstream licenses (ODbL / CC BY-SA / public domain).
