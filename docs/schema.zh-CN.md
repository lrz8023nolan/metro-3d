# 城市数据格式（schema）

[English](schema.md) | **中文**

查看器渲染的一切都来自 `cities/<city-id>/` 下的**城市数据包**：

| 文件 | 必需 | 作用 |
|---|---|---|
| `city.json` | **是** | 规范数据集（线路 + 车站 + 界面文案） |
| `build_config.json` | 否 | 纵向/埋深模型的构建参数 |
| `terrain_grid.csv` | 否 | 地面高程网格：`lat,lon,elevation_m`（0.01° 步长） |
| `wiki_line_stations.csv` | 否 | 逐线车站属性（敷设/开通/站台等） |
| `manual/` | 否 | 人工修正与带来源的新闻数据（北京采集产物） |

### 最小城市数据包

只提供 `city.json` 就能构建出查看器，其余文件缺省时自动降级。

```json
{
  "meta": { "city": "yourcity", "name": "某市地铁", "generated": "2026-10-01" },
  "lines": [
    { "id": "1", "name": "1号线", "colour": "#E4002B", "length_km": 30.0,
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

构建：`python scripts/build.py --city yourcity` → `dist/yourcity.html`。

`tests/validate_data.py` 校验下述各项不变量。枚举值保留中文原文
（地下/高架/…），因为上游来源即为中文，界面直接使用。

## `city.json`

### `meta`

| 字段 | 类型 | 说明 |
|---|---|---|
| `city` / `name` | string | 城市 id（目录名）/ 显示名 |
| `generated` | string | 快照日期 `YYYY-MM-DD` |
| `crs` | string | 坐标说明——**WGS-84**；与 GCJ-02 底图混用前需转换 |
| `sources` | string[] | 可读的来源清单 |
| `bbox` | `[lon_min, lon_max, lat_min, lat_max]` | 可选；校验脚本用于地理范围检查 |
| `counts` | object | 可选；`{lines, stations, stations_with_depth, …}`，提供时与数组实际值相互校验 |
| `disclaimers` | string[] | 已知注意点 |
| `ui` | object | 可选的界面文案，见下 |

### `meta.ui`（可选，界面文案）

| 字段 | 用途 | 占位符 |
|---|---|---|
| `title` | 面板标题 | — |
| `page_title` | 网页 `<title>` | — |
| `subtitle` | 标题下方一行 | `{lines}` `{stations}` `{instances}` `{truth}` |
| `footer_html` | 面板页脚（允许少量 HTML） | 同上 |
| `credits` | 站点信息卡页脚署名 | — |

缺省时回退到 `meta.name` + 通用中文文案。

### `lines[]`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 全库通用的稳定键（`"1"`、`"cp"`、`"dxjc"`…） |
| `name` | string | 显示名 |
| `type` | enum | `metro` / `express` / `maglev` / `tram` |
| `colour` | string | `#RRGGBB` |
| `open_date` | string | 首次开通（日期精度不一） |
| `length_km` / `station_count` | number | |
| `station_sequence` | string[] | 有序站名；每个都必须存在于 `stations[]` |
| `from` / `to` | string | 两端终点 |
| `geometry` | `[lon, lat][]` | 折线，WGS-84，5 位小数 |
| `direction_relations` | number[] | 来源 OSM 关系 id |
| `notes` | string[] | 数据出处说明 |

### `stations[]`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` / `name` | string | 车站名——唯一，是全库的连接键（当前 `id` 同 `name`） |
| `name_en` | string? | 英文名 |
| `lat` / `lon` | number | WGS-84 |
| `lines` | string[] | 经过本站的线路 id |
| `status` | enum | `operational` / `suspended`（`closed` 保留） |
| `elevation_m` | number? | 地面高程（SRTM 30 m） |
| `floors` | number? | 地下层数（信息框解析，较少） |
| `laying` | enum | `地下` / `高架` / `地面` / `半地下`——多线合并值 |
| `open_date` | string | |
| `district` / `platform` / `transfers` | string | 按来源原文 |
| `depth_m` | number? | 公开埋深（米） |
| `depth_min_m` / `depth_max_m` | number? | 来源给区间时使用 |
| `depth_measure` | string? | 口径：`底板`、`轨面`、`站体深度`、`基坑深度`、`埋深`（未注明）、`信息框` 等 |
| `depth_source` | string? | 引用键，如 `zh.wikipedia:东四站`、`北京日报（2023-11）` |
| `depth_conf` | enum? | `high` / `medium` / `low` |
| `depth_alt` | string[] | 备选口径数字（留档） |
| `notes` | string[] | |

## `build_config.json`（可选）

所有键都可省略，缺省值取内置默认（无实测埋深、线路缺省 20 m、标准地面偏移、
无有轨电车线路）。只提供 `city.json` 的城市包也能正常构建。

| 字段 | 类型 | 说明 |
|---|---|---|
| `truth_line` | `{车站: line_id}` | 该站公开埋深归属于哪条线的站台层（换乘站逐线不同） |
| `notes` | `{车站: 文本}` | 站点卡片备注（如东大桥的基坑口径说明） |
| `line_default_depth` | `{line_id: 米}` | 线路缺省埋深，用于两端插值封口 |
| `depth_anchors` | `{line_id: [[车站, 米], …]}` | 作者估算锚点——**低置信度、无出处** |
| `offsets` | `{敷设: 米}` | 地上视觉偏移：高架 `8.0`、地面 `1.2`、半地下 `-3.5` |
| `tram_ground_offset` | number | 有轨电车贴地偏移 `0.4` |
| `tram_lines` | string[] | 按有轨电车处理的车线 id |
| `wiki_alias` | `{线路名: [来源表名, …]}` | 数据集线路名 → 逐线属性表名 |
| `fallback_colour` | `{line_id: #RRGGBB}` | 数据集缺色时的兜底 |
| `measure_cn` | `{口径: 标签}` | 口径的界面标签 |

## 可选文件

除 `city.json` 外全部可选，缺省时构建自动降级。

| 文件 | 提供时 | 缺省时 |
|---|---|---|
| `build_config.json` | 埋深模型参数（见上） | 使用默认值：无实测埋深、线路缺省 20 m |
| `terrain_grid.csv`（`lat,lon,elevation_m,dataset`） | 双线性地面采样 + 地形网格 | 地面高程按 0 处理（平面地形） |
| `wiki_line_stations.csv`（`line,seq,name,name_en,district,open_date,laying,platform,transfers`） | 逐线车站属性 | 回退为 `stations[]` 的合并值 |
| `manual/` | 人工修正（仅北京采集流程使用） | 构建时不读取 |

## 运行时数据（构建产物）

`scripts/build_data.py` 生成 `build/<city>_data.js`（`window.METRO_DATA`）与
`build/<city>_summary.json`（计数与显示名，供 `build_html.py` 和城市索引页使用）：

- `meta` —— 投影原点（`lat0`、`lon0`）、`ref_alt`、地形子集、色板、线路名、署名、计数
- `lines[]` —— `geometry` 变为 `[lon, lat, ground, track]` 四元组；
  站点增加 `g`（地面）、`t`（轨面）、`dep`（埋深）、`dk`
  （`truth|est|above`）、`lab`（标注去重标记）、`src` / `conf` / `meas`

查看器只读这一个文件。插值规则：`轨面 = 地面 + 带符号偏移`，沿弧长线性；
**地下站只用地下控制点插值**，避免被地面/高架邻站拉向地表。
