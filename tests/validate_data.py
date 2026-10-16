# -*- coding: utf-8 -*-
"""Metro-3D · city data validation（数据集静态校验，仅用标准库）

用法 / Usage:  python tests/validate_data.py
退出码非 0 表示存在错误。
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITY_DIR = os.path.join(ROOT, "cities", "beijing")

# 合理范围（北京）
BBOX = (115.8, 117.2, 39.4, 40.7)          # lon_min, lon_max, lat_min, lat_max
LAID = {"地下", "高架", "地面", "半地下"}
STATUS = {"operational", "suspended", "closed", "under_construction"}
CONF = {"high", "medium", "low"}
COLOUR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

errors = []
warns = []


def err(msg):
    errors.append(msg)


def main():
    city = json.load(open(os.path.join(CITY_DIR, "city.json"), encoding="utf-8"))
    lines = city.get("lines", [])
    stations = city.get("stations", [])
    meta = city.get("meta", {})

    # ---- meta ----
    for k in ("city", "name", "generated", "counts"):
        if k not in meta:
            err(f"meta 缺字段: {k}")

    # ---- lines ----
    line_ids, line_seq = set(), {}
    for l in lines:
        lid = l.get("id")
        if not lid:
            err("line 缺 id")
            continue
        if lid in line_ids:
            err(f"line id 重复: {lid}")
        line_ids.add(lid)
        for k in ("name", "colour", "geometry", "station_sequence", "length_km"):
            if k not in l:
                err(f"line {lid} 缺字段 {k}")
        if l.get("colour") and not COLOUR_RE.match(l["colour"]):
            err(f"line {lid} colour 非法: {l['colour']}")
        if len(l.get("geometry") or []) < 2:
            err(f"line {lid} 几何点不足")
        seq = l.get("station_sequence") or []
        if len(seq) < 2:
            err(f"line {lid} 站序不足")
        line_seq[lid] = set(seq)
        for nm in seq:
            if nm not in {s.get("name") for s in stations}:
                err(f"line {lid} 站序含未收录车站: {nm}")
        for p in l.get("geometry") or []:
            if len(p) < 2 or not (BBOX[0] <= p[0] <= BBOX[1] and BBOX[2] <= p[1] <= BBOX[3]):
                err(f"line {lid} 几何点越界/非法: {p}")

    # ---- stations ----
    master = {s.get("name"): s for s in stations}
    if len(master) != len(stations):
        err("station 存在重名")
    n_depth = n_elev = n_lay = 0
    for s in stations:
        nm = s.get("name")
        for k in ("id", "lat", "lon", "lines", "status"):
            if k not in s:
                err(f"station {nm} 缺字段 {k}")
        if not (BBOX[0] <= s.get("lon", 0) <= BBOX[1] and BBOX[2] <= s.get("lat", 0) <= BBOX[3]):
            err(f"station {nm} 坐标越界: {s.get('lat')},{s.get('lon')}")
        if s.get("status") not in STATUS:
            err(f"station {nm} status 非法: {s.get('status')}")
        for lid in s.get("lines", []):
            if lid not in line_ids:
                err(f"station {nm} 引用未知线路: {lid}")
        if s.get("laying") is not None:
            if s["laying"] not in LAID:
                err(f"station {nm} laying 非法: {s['laying']}")
            else:
                n_lay += 1
        if s.get("elevation_m") is not None:
            n_elev += 1
        dep = s.get("depth_m")
        if dep is not None:
            n_depth += 1
            if not (0 < dep <= 60):
                err(f"station {nm} depth 超出合理范围: {dep}")
            if s.get("depth_conf") not in CONF:
                err(f"station {nm} depth_conf 非法: {s.get('depth_conf')}")
            if not s.get("depth_source"):
                warns.append(f"station {nm} 有埋深但缺来源")

    # ---- counts 一致性 ----
    counts = meta.get("counts", {})
    if counts.get("lines") != len(lines):
        err(f"meta.counts.lines={counts.get('lines')} 与实际 {len(lines)} 不符")
    if counts.get("stations") != len(stations):
        err(f"meta.counts.stations={counts.get('stations')} 与实际 {len(stations)} 不符")
    if counts.get("stations_with_depth") != n_depth:
        err(f"meta.counts.stations_with_depth={counts.get('stations_with_depth')} 与实际 {n_depth} 不符")

    # ---- build_config 引用完整性 ----
    cfg = json.load(open(os.path.join(CITY_DIR, "build_config.json"), encoding="utf-8"))
    for nm, lid in cfg.get("truth_line", {}).items():
        if nm not in master:
            err(f"build_config.truth_line 车站不在主表: {nm}")
        elif lid not in master[nm].get("lines", []):
            err(f"build_config.truth_line {nm}→{lid} 与 station.lines 不符")
    for lid, pairs in cfg.get("depth_anchors", {}).items():
        if lid not in line_ids:
            err(f"build_config.depth_anchors 引用未知线路: {lid}")
            continue
        for nm, _dep in pairs:
            if nm not in master:
                err(f"build_config.depth_anchors {lid} 车站不在主表: {nm}")
            elif nm not in line_seq[lid]:
                err(f"build_config.depth_anchors {lid} 车站不在该线站序: {nm}")
    for lid in cfg.get("line_default_depth", {}):
        if lid not in line_ids:
            err(f"build_config.line_default_depth 引用未知线路: {lid}")

    # ---- 附属数据文件 ----
    tpath = os.path.join(CITY_DIR, "terrain_grid.csv")
    terrain_rows = list(csv.DictReader(open(tpath, encoding="utf-8-sig")))
    if len(terrain_rows) < 1000:
        err(f"terrain_grid.csv 行数异常: {len(terrain_rows)}")
    if terrain_rows and not {"lat", "lon", "elevation_m"} <= set(terrain_rows[0].keys()):
        err("terrain_grid.csv 缺列（需 lat/lon/elevation_m）")
    wpath = os.path.join(CITY_DIR, "wiki_line_stations.csv")
    wrows = list(csv.DictReader(open(wpath, encoding="utf-8-sig")))
    if wrows and not {"line", "name", "laying"} <= set(wrows[0].keys()):
        err("wiki_line_stations.csv 缺列（需 line/name/laying）")

    # ---- 汇总 ----
    print("校验 / validate: cities/beijing")
    print(f"  线路 {len(lines)} | 车站 {len(stations)} | "
          f"埋深真值 {n_depth} ({n_depth / max(len(stations), 1) * 100:.1f}%) | "
          f"高程 {n_elev}/{len(stations)} | 敷设 {n_lay}/{len(stations)}")
    print(f"  地形网格 {len(terrain_rows)} 点 | 逐线站表 {len(wrows)} 行")
    for w in warns:
        print("  [warn]", w)
    if errors:
        print(f"  错误 {len(errors)}:")
        for e in errors:
            print("  [ERROR]", e)
        sys.exit(1)
    print("  OK：未发现错误")


if __name__ == "__main__":
    main()
