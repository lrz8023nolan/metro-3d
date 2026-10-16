# 数据采集脚本（北京）· Beijing collection scripts

These are the original scripts used to build the Beijing dataset shipped in
`cities/beijing/`. They are kept **for provenance** — the viewer itself does
not need them. Re-running them lets you regenerate or extend the data.

运行前提 / Requirements:

- Python 3.10+（仅标准库 / stdlib only）
- 可访问 Overpass API（OSM）；Overpass 主站忙时会自动退避重试
- 访问维基百科：大陆网络需本机 HTTP 代理（默认 `127.0.0.1:7897`，
  可用环境变量 `METRO3D_PROXY` 覆盖，置空则直连）；海外网络直接设
  `METRO3D_PROXY=` 即可
- 访问 OpenTopoData（高程，直连可用）

所有输出写入仓库根目录下的 `data/`（已 gitignore），中间文件可重复生成。

## 管线顺序 / Pipeline order

| # | 脚本 | 作用 | 主要产出 |
|---|------|------|----------|
| 0 | （手工一次） | Overpass 取线路关系清单 | `data/raw/osm/beijing_routes_tags.json` |
| 1 | `01_fetch_osm.py` | 线路几何（`out geom`）+ 车站节点 | `data/raw/osm/beijing_routes_geom.json` 等 |
| 2 | `02_fetch_stop_nodes.py` | 补抓站点成员节点标签 | `data/raw/osm/beijing_stop_nodes.json` |
| 3 | `03_build_network.py` | 双端链式拼接几何、整理站序 | `data/processed/lines.json`、`stations.json` |
| 4 | `04_fetch_wikipedia.py` | 分线路批量抓维基条目正文 | `data/raw/wikipedia/pages/*.json` |
| 5 | `05_extract_depth.py` | 从条目正文/信息框提取埋深证据 | `data/processed/depth_evidence_wiki.csv` |
| 6 | `06_parse_wiki_tables.py` | 解析《北京地铁车站列表》表格 | `data/processed/wiki_line_stations.csv` |
| 7 | `07_fetch_elevation.py` | 站点高程 + 地形网格（SRTM 30m） | `data/processed/station_elevation.csv`、`terrain_grid.csv` |
| 8 | `08_build_final.py` | 合并全部来源为统一数据集 | `data/processed/beijing_metro.json` |

第 0 步查询（响应保存为 `data/raw/osm/beijing_routes_tags.json`）：

```
[out:json][timeout:120];
relation["route"~"^(subway|light_rail|monorail|tram)$"](39.4,115.8,40.6,117.1);
out tags;
```

## 采集完成后 / After collection

把下列文件复制进城市数据包（构建查看器所需）：

| 采集输出 | → 城市数据包 |
|---|---|
| `data/processed/beijing_metro.json` | `cities/beijing/city.json` |
| `data/processed/terrain_grid.csv` | `cities/beijing/terrain_grid.csv` |
| `data/processed/wiki_line_stations.csv` | `cities/beijing/wiki_line_stations.csv` |
| `cities/beijing/manual/*.json`（人工修正） | → `data/manual/`（08 脚本读取） |

埋深估算所用的锚点与线路缺省值在 `cities/beijing/build_config.json`，
属人工整理，不在采集脚本内。
