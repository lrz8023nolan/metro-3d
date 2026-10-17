# 参与贡献

[English](CONTRIBUTING.md) | **中文**

感谢你一起把地铁深度图画准确！

## 可以做什么

- **报数据错误**（埋深不对、缺站、线色不符、状态过时）——开 issue，
  附上来源链接。
- **补充埋深证据** —— 当前最大的缺口：北京多数地下站仍是估算值。
  任何带口径和来源的数字都有价值。
- **改进查看器** —— 保持轻依赖（除 three.js 外零依赖）与城市无关。
  较大的功能建议先开 issue 讨论。
- **新增一座城市** —— 见下。

## 新增城市

1. 创建 `cities/<city-id>/`，放入 **`city.json`** 即可（唯一的必需文件）；
   可选文件（`build_config.json`、`terrain_grid.csv`、逐线属性表）见
   [docs/schema.zh-CN.md](docs/schema.zh-CN.md)。
2. 校验：`python tests/validate_data.py --city <city-id>`。
3. 构建：`python scripts/build.py --city <city-id>` → `dist/<city-id>.html`；
   用 `--all` 可重建全部城市与索引页。
4. 有条件的话运行 `node tests/verify_render.js <city-id>` 做渲染自检。
5. 提交 PR，说明数据来源与许可。

## 数据质量规则

- 每个公开数值都要有 **数值 + 口径 + 来源 + 置信度** 四要素，不允许"裸数字"。
- 估算值必须在界面上明确标注为估算，不得与有出处的数值混列。
- 坐标一律 WGS-84，不得混入 GCJ-02。
- 不传播受版权保护的地图；官方线网图只能作为核对参照。

## 贡献内容的许可

代码：MIT（见 [LICENSE](LICENSE)）。
数据：提交即视为你确认其可按上游许可（ODbL / CC BY-SA / 公有领域，或你
明确声明的估算条款）分发，与
[docs/data-sources.zh-CN.md](docs/data-sources.zh-CN.md) 保持一致。
