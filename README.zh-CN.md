# metro-3d · 立体地铁线路图生成器

[**English**](README.md) | **中文**

> 把地铁线网按“真实地下姿态”画出来的交互式三维地图：垂直夸张显示埋深，叠加地形，单文件、离线可用。
> **通用**：任何城市 = 一个数据包 + 一条命令。仓库内置 **北京** 示例（29 条线路 · 424 座车站 · 541 个站台层，数据截至 2026-10）。

![北京地铁立体线路图](docs/images/iso.jpg)

## 这是什么

- **单文件、完全离线** —— 构建产物 `dist/beijing.html`（约 1 MB）双击即开；three.js、数据与应用代码全部内联，无需网络、无需密钥。
- **真实数据、诚实标注** —— 几何与车站来自 OpenStreetMap，地面高程来自 SRTM，埋深从维基百科与公开报道逐条整理。每条实测值都带口径、来源与置信度；插值补齐的埋深一律标 `~`，信息卡里写明“估算”。
- **可交互** —— 拖动旋转 / 滚轮缩放 / 右键平移 · 垂直夸张滑块 · 埋深强化滑块 · 线路开关 · 站点信息卡 · 三个视角（斜视 / 剖面 / 俯视）· 站名防重叠。
- **与城市无关** —— 渲染层只认统一数据格式；加一座城市就是加一个数据包，不需要改代码。

| 剖面视角 | 垂直夸张 ×80 | 站点信息卡 |
|---|---|---|
| ![剖面](docs/images/side.jpg) | ![夸张](docs/images/depth.jpg) | ![卡片](docs/images/card.jpg) |

## 快速开始（选一种）

| 我想… | 怎么做 |
|---|---|
| **先看看效果** | 双击 [`dist/beijing.html`](dist/beijing.html)（约 1 MB，离线可用）；或在 GitHub Pages 打开城市索引 `dist/index.html` |
| **本地构建** | `python scripts/build.py --all`；Windows 也可以直接双击 [`build.cmd`](build.cmd)（构建完成后自动打开城市索引） |
| **做自己城市的图** | 准备 `cities/<城市>/city.json` → `python scripts/build.py --city <城市>`；最小数据格式见 [数据格式](docs/schema.zh-CN.md)，完整步骤见 [使用说明](docs/usage.zh-CN.md) |

环境要求：Python 3.10+（仅标准库）。渲染自检需要 Node.js + 本机 Edge/Chrome（可选）。

## 使用说明（摘要）

- **面板**：垂直夸张（5–150×）、埋深强化（1–6×，只放大地下段的相对深度）、地形 / 站名 / 自动旋转开关、线路开关（全显 / 全隐）、三个视角预设。
- **鼠标**：拖动旋转、滚轮缩放、右键（或 Shift + 拖动）平移、点击站点查看信息卡。
- **读图**：`34m` = 实测（卡片里给出口径与来源）；`~31m` = 估算（低置信度）；地面 / 高架站不标数字。
- 完整说明（含埋深口径、常见问题）：[docs/usage.zh-CN.md](docs/usage.zh-CN.md)。

## 仓库结构

```
viewer/     渲染层（与城市无关）：app.js、template.html、vendor/three.js
cities/     数据层：一城一包
            city.json（必需）· build_config.json / terrain_grid.csv / wiki_line_stations.csv（可选）
scripts/    build.py（--city 单城 / --all 全部 + 城市索引）
            build_data.py · build_html.py · collect/（北京采集管线，留档）
dist/       构建产物：dist/beijing.html、dist/index.html
docs/       使用说明、数据格式、数据来源、图片
tests/      数据校验（--city/--all）+ 无头渲染验证（可选城市参数）
build.cmd   Windows 一键构建并打开
```

## 数据模型（简版）

每个城市数据包由两部分驱动：

- **`city.json`** —— 规范数据集：`lines[]`（线色、几何、站序）与 `stations[]`（坐标、高程、敷设方式、开通日期、埋深＋口径＋来源＋置信度）。完整字段见 [docs/schema.zh-CN.md](docs/schema.zh-CN.md)。
- **`build_config.json`（可选）** —— 埋深模型的构建参数：真值映射、估算锚点、线路缺省值、地面 / 高架偏移。缺省时使用内置默认值。

构建流程：推导线剖面（`轨面 = 地面 + 带符号偏移`）→ 沿弧长插值 → 站点吸附到折线 → 全部内联进单个 HTML。

## 数据来源与许可

| 数据 | 来源 | 许可 |
|---|---|---|
| 线路几何、车站、站序 | OpenStreetMap（Overpass API） | ODbL 1.0 |
| 车站属性与埋深证据 | 中文维基百科 | CC BY-SA 4.0 |
| 地面高程 / 地形网格 | SRTM 30 m（经 OpenTopoData） | 公有领域 |
| 具体车站埋深 | 新闻与工程报道（逐条注来源） | — |

逐条引用、置信度框架与已知注意点见 [docs/data-sources.zh-CN.md](docs/data-sources.zh-CN.md)；北京数据集的完整构建记录见 [docs/data-inventory.zh-CN.md](docs/data-inventory.zh-CN.md)。

**许可**：代码（查看器与脚本）为 MIT —— 见 [LICENSE](LICENSE)；数据集沿用上表各自的上游许可，复用时请保留署名。

## 路线图

- [ ] 起点-终点路径检索与高亮
- [ ] 时间轴（看线网逐年生长）
- [ ] 可选的合规底图（通过自定义三维图层接入）
- [ ] 更多城市（欢迎按数据格式提交数据包）

欢迎参与贡献 —— 见 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

## 致谢

- 概念来源：康斯坦丁·多布罗夫的莫斯科地铁 3D 深度图；叶夫根尼·瓦尔福洛梅耶夫 2013 年原版。
- 使用 [three.js](https://threejs.org/) r149（MIT）构建。
- 数据：© OpenStreetMap 贡献者（ODbL）· 中文维基百科（CC BY-SA）· NASA/USGS SRTM。
