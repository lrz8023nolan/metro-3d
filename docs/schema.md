# City data schema

[English](schema.md) | [中文](schema.zh-CN.md)

Everything the viewer renders comes from a **city package** under
`cities/<city-id>/`:

| File | Role |
|---|---|
| `city.json` | canonical dataset (lines + stations) |
| `build_config.json` | build-time parameters for the vertical / depth model |
| `terrain_grid.csv` | ground elevation grid: `lat,lon,elevation_m` (0.01° step) |
| `wiki_line_stations.csv` | per-line station attributes (laying / opening / platform …) |
| `manual/` | hand-curated corrections & sourced figures (Beijing) |

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
| `counts` | object | `{lines, stations, stations_with_depth, stations_with_elevation, stations_with_laying}` — verified against the arrays |
| `disclaimers` | string[] | known caveats |

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

## `build_config.json`

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

## Auxiliary files

- **`terrain_grid.csv`** — `lat,lon,elevation_m,dataset`, 0.01° grid covering
  the network bbox (SRTM 30 m). The build samples it bilinearly.
- **`wiki_line_stations.csv`** — per-line station rows
  (`line,seq,name,name_en,district,open_date,laying,platform,transfers`).
  Per-line because attributes differ between lines of one interchange.
- **`manual/`** — `corrections.json` (renames, exclusions, status fixes) and
  `depth_news.json` (sourced media figures with URL + confidence).

## Derived runtime data (build output)

`scripts/build_data.py` writes `build/<city>_data.js` (`window.METRO_DATA`):

- `meta` — projection origin (`lat0`, `lon0`), `ref_alt`, terrain subset,
  palette, line names, counts
- `lines[]` — `geometry` becomes `[lon, lat, ground, track]` 4-tuples;
  stations gain `g` (ground) `t` (track) `dep` (depth) `dk`
  (`truth|est|above`) `lab` (label-dedup flag) `src` / `conf` / `meas`

The viewer reads only this file. Interpolation rule:
`track = ground + signed_offset`, linear in arc length; underground stations
are interpolated **using underground control points only**, so at-grade
neighbours cannot pull them toward the surface.
