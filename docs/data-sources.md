# Data sources, confidence & caveats (Beijing)

[English](data-sources.md) | [中文](data-sources.zh-CN.md)

Snapshot date of the shipped dataset: **2026-10-14**. Raw downloads are not
stored in this repository (size); the `scripts/collect/` pipeline re-fetches
them.

## Sources

| # | Source | Used for | License |
|---|---|---|---|
| 1 | OpenStreetMap via Overpass API | line geometry, station nodes, stop sequences | ODbL 1.0 |
| 2 | Chinese Wikipedia (`zh.wikipedia.org`) | station attributes (per-line laying, opening dates, districts, platforms), depth evidence, line colours (`Module:Adjacent stations`) | CC BY-SA 4.0 |
| 3 | OpenTopoData · SRTM 30 m | ground elevation per station + terrain grid (0.01°) | public domain (NASA/USGS) |
| 4 | News & engineering reports | depth figures for specific stations (cited per value) | quotes, see below |
| 5 | Official metro map (2025 edition) | cross-checking line colours and termini | reference only, not redistributed |

## Documented depths (top values)

37 of 424 stations carry a documented depth. The 12 deepest:

| Station | Line(s) | Depth | Measure | Conf. | Source |
|---|---|---|---|---|---|
| 东大桥 * | 17/6 | 46.8 m | 基坑深度 pit | high | China Railway Construction News (2026-02) |
| 工人体育场 | 17/3 | 39 m | 埋深 | medium | People.cn (2020-11); CNR (2018-11) |
| 六道口 | 15/cp | 35.25 m | 埋深 | medium | Beijing Daily (2023-11) |
| 东四 | 5/6 | 34.0 m | 底板 slab | high | zh.wikipedia:东四站 |
| 永定门外 | 14/8 | 34 m | 站体结构深度 | low | China Economic Net (2016-02) |
| 清河小营桥 | cp | 34.0 m | 信息框 infobox | high | zh.wikipedia:清河小营桥站 |
| 安华桥 | 12/8 | 33.19 m | 底板 slab | high | zh.wikipedia:安华桥站 |
| 磁器口 | 5/7 | 32.5 m | 底板埋深 | high | CREC Engineering Group (2014-12) |
| 甘家口 | 16 | 31.2 m | 信息框 infobox | high | zh.wikipedia:甘家口站 |
| 军事博物馆 | 1/9 | 31 m | 埋深范围, non-primary source | low | Baike mirror |
| 丰台站 | 10/16 | 30.7 m | 站体深度 | low | zh.wikipedia:丰台站 (地铁) |
| 西坝河 | 12/17 | 30.51 m | 底板 slab | high | zh.wikipedia:西坝河站 |

\* 东大桥 is **excluded from the depth model**: 46.8 m is the pit depth of an
under-construction interchange (6/17/22/28), not an operating station body. It
is kept as a note on the station card. The other 36 values feed the model as
anchors. Overall confidence split: 26 high / 4 medium / 7 low.

Full per-value data (including alternative figures) lives in
`cities/beijing/city.json` (`depth_m`, `depth_measure`, `depth_source`,
`depth_conf`, `depth_alt`) and is shown in the viewer's station cards.

## Confidence framework

The viewer labels every underground station instance with one of three kinds:

| Kind | Meaning | UI |
|---|---|---|
| `truth` | documented value from the curated chain above | `34m`, with measure + source in the card |
| `est` | simulated: anchors + per-line defaults, linearly interpolated | `~31m`, card says *estimated, low confidence* |
| `above` | elevated / at-grade — no depth; small offsets (+8.0 / +1.2 / +0.4 m) only stack the line visually | no number |

Even within `truth`, figures are not uniform: measures differ (slab vs station
structure vs pit vs unspecified 埋深), some come from a single news report.
`depth_conf` records this. Treat `low` figures accordingly.

## Known caveats

- **Coverage**: 37/424 stations have documented depths (≈9%); everything else
  is interpolated. Improve coverage via sourced PRs — that's the main data gap.
- **Anchors are estimates**: `build_config.json → depth_anchors` are the
  author's approximations derived from line age/depth patterns. They are **not**
  sourced values.
- **Selection**: 6 unopened stations excluded (福寿岭, 53号, 陶然桥, 高家园
  〔14号线〕, 广渠门外, 老观里). Lines under construction (22, 28, 13 split,
  1 branch, M101, R1…) are not included.
- **Status**: 八角游乐园 is suspended (renovation, passes without stopping);
  苹果园 / 古城 / 八宝山 returned to service on 2026-05-16 with 苹果园 as a
  three-line interchange.
- **Snapping**: interchange nodes in OSM can sit up to ~240 m from the track
  (entrances vs platforms); the build snaps stations onto the polyline, so
  positions are network-accurate rather than entrance-accurate.
- **Display**: mountains west of 金安桥 (up to 781 m) are soft-compressed in
  rendering only; data is untouched.
- **Version**: the network reflects 2026-10; later openings/changes are not
  reflected.

## Reproducing / extending

See [`scripts/collect/README.md`](../scripts/collect/README.md). Note: the
Chinese Wikipedia requires a local HTTP proxy from mainland networks
(`METRO3D_PROXY`, default `http://127.0.0.1:7897`).
