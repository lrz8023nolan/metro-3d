# City data schema

[English](schema.md) | [中文](schema.zh-CN.md)

Everything the viewer renders comes from a **city package** under
`cities/<city-id>/`:

| File | Required | Role |
|---|---|---|
| `city.json` | **yes** | canonical dataset (lines + stations + viewer copy) |
| `build_config.json` | no | build-time parameters for the vertical / depth model |
| `terrain_grid.csv` | no | ground elevation grid: `lat,lon,elevation_m` (0.01° step) |
| `wiki_line_stations.csv` | no | per-line station attributes (laying / opening / platform …) |
| `manual/` | no | hand-curated corrections & sourced figures (Beijing collection) |

### Minimal city package

`city.json` alone is enough to build a viewer — everything else degrades
gracefully.

```json
{
  "meta": { "city": "yourcity", "name": "Your City Metro", "generated": "2026-10-01" },
  "lines": [
    { "id": "1", "name": "Line 1", "colour": "#E4002B", "length_km": 30.0,
      "station_sequence": ["A", "B"],
      "geometry": [[116.30, 39.90], [116.40, 39.90]] }
  ],
  "stations": [
    { "id": "A", "name": "A", "lat": 39.90, "lon": 116.30, "lines": ["1"],
      "status": "operational", "laying": "地下" },
    { "id": "B", "name": "B", "lat": 39.90, "lon": 116.40, "lines": ["1"],
      "status": "operational", "laying": "地下" }
  ]
}
```

Run `python scripts/build.py --city yourcity` → `dist/yourcity.html`.

`tests/validate_data.py` checks the invariants below. Enum values are authored
in Chinese where they describe source wording (地下/高架/…); keep them as-is.

## `city.json`

### `meta`

| Field | Type | Notes |
|---|---|---|
| `city` / `name` | string | id (folder name) / display name |
| `generated` | string | snapshot date, `YYYY-MM-DD` |
| `crs` | string | coordinate note — **WGS-84**; convert before mixing with GCJ-02 basemaps |
| `sources` | string[] | human-readable source list |
| `bbox` | `[lon_min, lon_max, lat_min, lat_max]` | optional; used by the validator |
| `counts` | object | optional; `{lines, stations, stations_with_depth, …}` — verified against the arrays when present |
| `disclaimers` | string[] | known caveats |
| `ui` | object | optional viewer copy, see below |

### `meta.ui` (optional viewer copy)

| Field | Used as | Placeholders |
|---|---|---|
| `title` | panel heading | — |
| `page_title` | document `<title>` | — |
| `subtitle` | line below the heading | `{lines}` `{stations}` `{instances}` `{truth}` |
| `footer_html` | panel footer (small HTML allowed) | same |
| `credits` | station-card footer line | — |

Missing fields fall back to `meta.name` + generic Chinese defaults.

### `lines[]`

| Field | Type | Notes |
|---|---|---|
| `id` | string | stable key used everywhere (`"1"`, `"cp"`, `"dxjc"`, …) |
| `name` | string | display name |
| `type` | enum | `metro` / `express` / `maglev` / `tram` |
| `colour` | string | `#RRGGBB` |
| `open_date` | string | first opening (date precision varies) |
| `length_km` / `station_count` | number | |
| `station_sequence` | string[] | ordered names; each must exist in `stations[]` |
| `from` / `to` | string | termini |
| `geometry` | `[lon, lat][]` | polyline, WGS-84, 5 decimals |
| `direction_relations` | number[] | source OSM relation ids |
| `notes` | string[] | data provenance notes |

### `stations[]`

| Field | Type | Notes |
|---|---|---|
| `id` / `name` | string | station name — unique, the join key (`id` mirrors `name` today) |
| `name_en` | string? | |
| `lat` / `lon` | number | WGS-84 |
| `lines` | string[] | line ids serving this station |
| `status` | enum | `operational` / `suspended` (`closed` reserved) |
| `elevation_m` | number? | ground elevation (SRTM 30 m) |
| `floors` | number? | underground level count parsed from infobox (rare) |
| `laying` | enum | `地下` underground / `高架` elevated / `地面` at-grade / `半地下` semi-underground — merged over lines |
| `open_date` | string | |
| `district` / `platform` / `transfers` | string | as reported by sources |
| `depth_m` | number? | documented depth (m) |
| `depth_min_m` / `depth_max_m` | number? | when the source gives a range |
| `depth_measure` | string? | what the value measures: `底板` slab, `轨面` rail, `站体深度`, `基坑深度` pit, `埋深` (unspecified), `信息框` infobox, … |
| `depth_source` | string? | citation key, e.g. `zh.wikipedia:东四站`, `北京日报（2023-11）` |
| `depth_conf` | enum? | `high` / `medium` / `low` |
| `depth_alt` | string[] | alternative figures kept for reference |
| `notes` | string[] | |

## `build_config.json` (optional)

All keys are optional; missing values fall back to built-in defaults (no
documented depths, 20 m line default, standard above-ground offsets, no tram
lines). A city package with only `city.json` builds fine.

| Field | Type | Notes |
|---|---|---|
| `truth_line` | `{station: line_id}` | which line's platform a documented depth belongs to (differs per line at interchanges) |
| `notes` | `{station: text}` | shown in the station card (e.g. the 东大桥 pit-depth caveat) |
| `line_default_depth` | `{line_id: m}` | default depth closing interpolation gaps at line ends |
| `depth_anchors` | `{line_id: [[station, m], …]}` | author's estimated anchors — **low confidence, not sourced** |
| `offsets` | `{laying: m}` | above-ground visual offsets: 高架 `8.0`, 地面 `1.2`, 半地下 `-3.5` |
| `tram_ground_offset` | number | `0.4` for tram lines at grade |
| `tram_lines` | string[] | line ids treated as tram |
| `wiki_alias` | `{line_name: [source_table_name, …]}` | dataset line name → per-line attribute table name(s) |
| `fallback_colour` | `{line_id: #RRGGBB}` | used when the dataset has no colour |
| `measure_cn` | `{measure: label}` | UI labels for depth measures |

## Optional files

Everything except `city.json` is optional; the build degrades gracefully.

| File | If provided | If missing |
|---|---|---|
| `build_config.json` | depth model parameters (above) | defaults: no documented depths, 20 m line default |
| `terrain_grid.csv` (`lat,lon,elevation_m,dataset`) | bilinear ground sampling + terrain mesh | ground elevation = 0 (flat terrain) |
| `wiki_line_stations.csv` (`line,seq,name,name_en,district,open_date,laying,platform,transfers`) | per-line station attributes | falls back to the merged `stations[]` values |
| `manual/` | hand-curated corrections (Beijing collection only) | not used by the build |

## Derived runtime data (build output)

`scripts/build_data.py` writes `build/<city>_data.js` (`window.METRO_DATA`)
and `build/<city>_summary.json` (counts + display name, used by
`build_html.py` and the generated city index):

- `meta` — projection origin (`lat0`, `lon0`), `ref_alt`, terrain subset,
  palette, line names, credits, counts
- `lines[]` — `geometry` becomes `[lon, lat, ground, track]` 4-tuples;
  stations gain `g` (ground) `t` (track) `dep` (depth) `dk`
  (`truth|est|above`) `lab` (label-dedup flag) `src` / `conf` / `meas`

The viewer reads only this file. Interpolation rule:
`track = ground + signed_offset`, linear in arc length; underground stations
are interpolated **using underground control points only**, so at-grade
neighbours cannot pull them toward the surface.
