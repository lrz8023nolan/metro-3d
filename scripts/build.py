# -*- coding: utf-8 -*-
"""Metro-3D · 一键构建：城市数据 → 单文件 HTML（单个或全部城市）

用法 / Usage:
    python scripts/build.py --city beijing     # 构建单个城市
    python scripts/build.py --all              # 构建 cities/ 下全部城市 + dist/index.html
输出 / Output:
    build/<city>_data.js、build/<city>_summary.json   （中间产物）
    dist/<city>.html、dist/index.html                （单文件查看器，双击即可打开）
"""
import argparse
import json
import os
import subprocess
import sys
from html import escape

INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>metro-3d · 立体地铁线路图</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{min-height:100vh;background:radial-gradient(1200px 700px at 70% 10%,rgba(42,60,88,.45),transparent 60%),#06080c;
    color:#e8edf4;font-family:"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,sans-serif;
    display:flex;flex-direction:column;align-items:center;padding:72px 20px 40px}
  h1{font-size:26px;font-weight:600;letter-spacing:.04em}
  .sub{margin-top:10px;color:#93a2b5;font-size:13px;line-height:1.8;text-align:center}
  .grid{margin-top:34px;display:grid;gap:14px;width:min(680px,100%)}
  a.card{display:block;padding:18px 20px;border-radius:14px;text-decoration:none;color:#e8edf4;
    background:rgba(13,18,26,.82);border:1px solid rgba(255,255,255,.09);transition:border-color .15s,background .15s}
  a.card:hover{border-color:rgba(244,218,64,.45);background:rgba(20,27,38,.9)}
  a.card b{font-size:16px;font-weight:600}
  a.card span{display:block;margin-top:6px;color:#8b9ab0;font-size:12px}
  .foot{margin-top:36px;color:#7c8ba0;font-size:11.5px}
  .foot a{color:#9db4d6;text-decoration:none;border-bottom:1px dotted rgba(157,180,214,.45)}
</style>
</head>
<body>
<h1>metro-3d · 立体地铁线路图</h1>
<div class="sub">用公开数据生成的地铁三维线路图：垂直夸张显示真实埋深，单文件、离线可用。<br>
Vertical-exaggerated metro maps built from open data — single file, works offline.</div>
<div class="grid">
{cards}
</div>
<div class="foot">开源项目 · <a href="{repo_url}">{repo_label}</a> · MIT</div>
</body>
</html>
"""


def build_city(here, city):
    for step in ("build_data.py", "build_html.py"):
        print(f"== {city}: {step} ==")
        subprocess.run([sys.executable, os.path.join(here, step), "--city", city], check=True)


def write_index(root, cities):
    cards = []
    for cid in cities:
        summary_path = os.path.join(root, "build", f"{cid}_summary.json")
        if os.path.exists(summary_path):
            summary = json.load(open(summary_path, encoding="utf-8"))
        else:
            summary = {"name": cid, "counts": {}}
        counts = summary.get("counts", {})
        desc = (f"{counts.get('lines', 0)} 条线路 · {counts.get('stations', 0)} 座车站 · "
                f"{counts.get('instances', 0)} 个站台层")
        cards.append(
            f'  <a class="card" href="./{escape(cid)}.html"><b>{escape(summary.get("name") or cid)}</b>'
            f'<span>{desc}</span></a>')
    pkg = json.load(open(os.path.join(root, "package.json"), encoding="utf-8"))
    repo_url = pkg.get("homepage", "")
    repo_label = repo_url.replace("https://", "").replace("http://", "").rstrip("/")
    html_out = (INDEX_HTML
                .replace("{cards}", "\n".join(cards))
                .replace("{repo_url}", escape(repo_url))
                .replace("{repo_label}", escape(repo_label)))
    dest = os.path.join(root, "dist", "index.html")
    open(dest, "w", encoding="utf-8").write(html_out)
    print(f"输出: {dest}")


def main():
    ap = argparse.ArgumentParser(description="Build the single-file viewer for one or all cities")
    ap.add_argument("--city", default="beijing", help="cities/ 下的城市 id")
    ap.add_argument("--all", action="store_true", help="构建 cities/ 下全部城市，并生成 dist/index.html")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    cities_dir = os.path.join(root, "cities")

    if args.all:
        cities = sorted(d for d in os.listdir(cities_dir)
                        if os.path.isdir(os.path.join(cities_dir, d)))
    else:
        cities = [args.city]

    for city in cities:
        build_city(here, city)

    if args.all:
        write_index(root, cities)
    print("完成 / Done.")


if __name__ == "__main__":
    main()
