# -*- coding: utf-8 -*-
"""Metro-3D · inline viewer + data → single-file HTML.

把 three.min.js + 运行时数据 + 应用代码内联进模板，并填入城市级文案
（标题 / 副标题 / 页脚 / 署名），产出单文件 HTML。

Reads:   viewer/{template.html, app.js}, viewer/vendor/three.min.js,
         build/<city>_data.js, build/<city>_summary.json,
         cities/<city>/city.json, package.json
Writes:  dist/<city>.html

用法 / Usage:  python scripts/build_html.py --city beijing
"""
import argparse
import json
import os
import re


def fill_counts(text, counts):
    """把文案里的 {lines} / {stations} / {instances} / {truth} 替换为实际数量。"""
    for key in ("lines", "stations", "instances", "truth"):
        text = text.replace("{" + key + "}", str(counts.get(key, 0)))
    return text


def main():
    ap = argparse.ArgumentParser(description="Inline everything into a single-file HTML viewer")
    ap.add_argument("--city", default="beijing", help="cities/ 下的城市 id")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    city_dir = os.path.join(root, "cities", args.city)
    build_dir = os.path.join(root, "build")

    city = json.load(open(os.path.join(city_dir, "city.json"), encoding="utf-8"))
    cmeta = city.get("meta", {})
    ui = cmeta.get("ui") or {}
    pkg = json.load(open(os.path.join(root, "package.json"), encoding="utf-8"))

    summary_path = os.path.join(build_dir, f"{args.city}_summary.json")
    if os.path.exists(summary_path):
        counts = json.load(open(summary_path, encoding="utf-8")).get("counts", {})
    else:
        counts = cmeta.get("counts", {})

    version = pkg.get("version", "")
    repo_url = pkg.get("homepage", "")
    repo_label = re.sub(r"^https?://", "", repo_url).rstrip("/")

    city_title = ui.get("title") or f"{cmeta.get('name', args.city)} · 立体线路图"
    page_title = ui.get("page_title") or f"{city_title} — metro-3d"
    city_sub = fill_counts(
        ui.get("subtitle") or "{lines} 条线路 · {stations} 座车站 · {instances} 个站台层", counts)
    footer_html = fill_counts(ui.get("footer_html") or "", counts)

    tpl = open(os.path.join(root, "viewer", "template.html"), encoding="utf-8").read()
    app = open(os.path.join(root, "viewer", "app.js"), encoding="utf-8").read()
    three = open(os.path.join(root, "viewer", "vendor", "three.min.js"), encoding="utf-8").read()
    data = open(os.path.join(build_dir, f"{args.city}_data.js"), encoding="utf-8").read()

    subs = {
        "PAGE_TITLE": page_title,
        "CITY_TITLE": city_title,
        "CITY_SUB": city_sub,
        "FOOTER_HTML": footer_html,
        "VERSION": version,
        "REPO_URL": repo_url,
        "REPO_LABEL": repo_label,
    }
    out = tpl
    for key, value in subs.items():
        out = out.replace("{{" + key + "}}", value)

    leftover = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", out)))
    if leftover:
        print("警告：模板中仍有未替换的占位符：", ", ".join(leftover))

    out = out.replace("/*__THREE__*/", three).replace("/*__DATA__*/", data).replace("/*__APP__*/", app)
    dist_dir = os.path.join(root, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    dest = os.path.join(dist_dir, f"{args.city}.html")
    open(dest, "w", encoding="utf-8").write(out)
    print(f"[{args.city}] 输出: {dest}")
    print(f"体积: {len(out)/1024:.0f} KB (three {len(three)/1024:.0f} + data {len(data)/1024:.1f} + app {len(app)/1024:.1f})")


if __name__ == "__main__":
    main()
