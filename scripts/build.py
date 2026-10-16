# -*- coding: utf-8 -*-
"""Metro-3D · 一键构建：城市数据 → 单文件 HTML

Pipeline runner: build_data.py + build_html.py for one city.

用法 / Usage:
    python scripts/build.py --city beijing
输出 / Output:
    build/<city>_data.js  （中间产物）
    dist/<city>.html      （单文件查看器，双击即可打开）
"""
import argparse
import os
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description="Build the single-file viewer for a city")
    ap.add_argument("--city", default="beijing", help="cities/ 下的城市 id")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    for step in ("build_data.py", "build_html.py"):
        print(f"== {step} ==")
        subprocess.run([sys.executable, os.path.join(here, step), "--city", args.city], check=True)
    print("完成 / Done.")


if __name__ == "__main__":
    main()
