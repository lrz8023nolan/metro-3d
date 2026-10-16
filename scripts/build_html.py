# -*- coding: utf-8 -*-
"""Metro-3D · inline viewer + data → single-file HTML.

把 three.min.js + 运行时数据 + 应用代码内联进模板，产出单文件 HTML。
Reads:   viewer/{template.html, app.js}, viewer/vendor/three.min.js, build/<city>_data.js
Writes:  dist/<city>.html

用法 / Usage:  python scripts/build_html.py --city beijing
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser(description="Inline everything into a single-file HTML viewer")
    ap.add_argument("--city", default="beijing", help="cities/ 下的城市 id")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    three = open(os.path.join(root, "viewer", "vendor", "three.min.js"), encoding="utf-8").read()
    data = open(os.path.join(root, "build", f"{args.city}_data.js"), encoding="utf-8").read()
    app = open(os.path.join(root, "viewer", "app.js"), encoding="utf-8").read()
    tpl = open(os.path.join(root, "viewer", "template.html"), encoding="utf-8").read()

    out = tpl.replace("/*__THREE__*/", three).replace("/*__DATA__*/", data).replace("/*__APP__*/", app)
    dist_dir = os.path.join(root, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    dest = os.path.join(dist_dir, f"{args.city}.html")
    open(dest, "w", encoding="utf-8").write(out)
    print(f"[{args.city}] 输出: {dest}")
    print(f"体积: {len(out)/1024:.0f} KB (three {len(three)/1024:.0f} + data {len(data)/1024:.1f} + app {len(app)/1024:.1f})")


if __name__ == "__main__":
    main()
