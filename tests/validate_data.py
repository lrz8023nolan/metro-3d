# -*- coding: utf-8 -*-
"""Metro-3D · city data validation（数据集静态校验，仅用标准库）

用法 / Usage:
    python tests/validate_data.py                 # 默认校验 cities/beijing
    python tests/validate_data.py --city <id>
    python tests/validate_data.py --all           # 校验全部城市
退出码非 0 表示存在错误。
"""
import argparse
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITIES = os.path.join(ROOT, "cities")

LAID = {"地下", "高架", "地面", "半地下"}
STATUS = {"operational", "suspended", "closed", "under_construction"}
CONF = {"high", "medium", "low"}
COLOUR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
DEPTH_MAX = 200.0          # 合理上限（米），跨城市通用


def validate_city(city_id):
    errors, warns = [], []
    err = errors.append

    city_dir = os.path.join(CITIES, city_id)
    if not os.path.isdir(city_dir):
        return [f"cities/{city_id} 不存在"], []

    city_path = os.path.join(city_dir, "city.json")
    if not os.path.exists(city_path):
        return [f"cities/{city_id}/city.json 不存在"], []
    city = json.load(open(city_path, encoding="utf-8"))
    lines = city.get("lines", [])
    stations = city.get("stations", [])
    meta = city.get("meta", {})

    # ---- meta ----
    for k in ("city", "name", "generated"):
        if k not in meta:
            err(f"meta 缺字段: {k}")
    bbox = meta.get("bbox")
    if bbox is not None and (not isinstance(bbox, list) or len(bbox) != 4):
        err("meta.bbox 格式非法（应为 [lon_min, lon_max, lat_min, lat_max]）")
        bbox = None
    if bbox is None:
        warns.append("meta.bbox 未提供：跳过地理范围检查")

    def in_range(lon, lat):
        if bbox:
            return bbox[0] <= lon <= bbox[1] and bbox[2] <= lat <= bbox[3]
        return -180 <= lon <= 180 and -90 <= lat <= 90

    # ---- lines ----
    line_ids, line_seq = set(), {}
    station_names = {s.get("name") for s in stations}
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
            if nm not in station_names:
                err(f"line {lid} 站序含未收录车站: {nm}")
        for p in l.get("geometry") or []:
            if len(p) < 2 or not in_range(p[0], p[1]):
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
        if not in_range(s.get("lon", 0), s.get("lat", 0)):
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
            if not (0 < dep <= DEPTH_MAX):
                err(f"station {nm} depth 超出合理范围: {dep}")
            if s.get("depth_conf") not in CONF:
                err(f"station {nm} depth_conf 非法: {s.get('depth_conf')}")
            if not s.get("depth_source"):
                warns.append(f"station {nm} 有埋深但缺来源")

    # ---- meta.counts（可选；提供则与实际一致）----
    counts = meta.get("counts")
    if counts is None:
        warns.append("meta.counts 未提供（可选，供构建脚本与索引页参考）")
    else:
        if counts.get("lines") != len(lines):
            err(f"meta.counts.lines={counts.get('lines')} 与实际 {len(lines)} 不符")
        if counts.get("stations") != len(stations):
            err(f"meta.counts.stations={counts.get('stations')} 与实际 {len(stations)} 不符")
        if counts.get("stations_with_depth") != n_depth:
            err(f"meta.counts.stations_with_depth={counts.get('stations_with_depth')} 与实际 {n_depth} 不符")

    # ---- build_config（可选）----
    cfg_path = os.path.join(city_dir, "build_config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, encoding="utf-8"))
    else:
        warns.append("未提供 build_config.json（可选）：埋深模型使用内置默认值")
    for nm, lid in (cfg.get("truth_line") or {}).items():
        if nm not in master:
            err(f"build_config.truth_line 车站不在主表: {nm}")
        elif lid not in master[nm].get("lines", []):
            err(f"build_config.truth_line {nm}→{lid} 与 station.lines 不符")
    for lid, pairs in (cfg.get("depth_anchors") or {}).items():
        if lid not in line_ids:
            err(f"build_config.depth_anchors 引用未知线路: {lid}")
            continue
        for nm, _dep in pairs:
            if nm not in master:
                err(f"build_config.depth_anchors {lid} 车站不在主表: {nm}")
            elif nm not in line_seq[lid]:
                err(f"build_config.depth_anchors {lid} 车站不在该线站序: {nm}")
    for lid in (cfg.get("line_default_depth") or {}):
        if lid not in line_ids:
            err(f"build_config.line_default_depth 引用未知线路: {lid}")

    # ---- 可选附属数据文件 ----
    terrain_rows = []
    tpath = os.path.join(city_dir, "terrain_grid.csv")
    if os.path.exists(tpath):
        terrain_rows = list(csv.DictReader(open(tpath, encoding="utf-8-sig")))
        if len(terrain_rows) < 100:
            err(f"terrain_grid.csv 行数异常: {len(terrain_rows)}")
        if terrain_rows and not {"lat", "lon", "elevation_m"} <= set(terrain_rows[0].keys()):
            err("terrain_grid.csv 缺列（需 lat/lon/elevation_m）")
    else:
        warns.append("未提供 terrain_grid.csv（可选）：构建时地面高程按 0 处理")

    wrows = []
    wpath = os.path.join(city_dir, "wiki_line_stations.csv")
    if os.path.exists(wpath):
        wrows = list(csv.DictReader(open(wpath, encoding="utf-8-sig")))
        if wrows and not {"line", "name", "laying"} <= set(wrows[0].keys()):
            err("wiki_line_stations.csv 缺列（需 line/name/laying）")
    else:
        warns.append("未提供 wiki_line_stations.csv（可选）：逐线属性回退为 station 合并值")

    # ---- 汇总 ----
    print(f"校验 / validate: cities/{city_id}")
    print(f"  线路 {len(lines)} | 车站 {len(stations)} | "
          f"埋深 {n_depth} ({n_depth / max(len(stations), 1) * 100:.1f}%) | "
          f"高程 {n_elev}/{len(stations)} | 敷设 {n_lay}/{len(stations)}")
    print(f"  地形网格 {len(terrain_rows)} 点 | 逐线站表 {len(wrows)} 行")
    return errors, warns


def main():
    ap = argparse.ArgumentParser(description="Validate metro-3d city data packages")
    ap.add_argument("--city", default="beijing", help="cities/ 下的城市 id")
    ap.add_argument("--all", action="store_true", help="校验全部城市")
    args = ap.parse_args()

    if args.all:
        ids = sorted(d for d in os.listdir(CITIES) if os.path.isdir(os.path.join(CITIES, d)))
    else:
        ids = [args.city]

    bad = 0
    for cid in ids:
        errors, warns = validate_city(cid)
        for w in warns:
            print(f"  [warn] {w}")
        if errors:
            bad += 1
            print(f"  错误 {len(errors)}:")
            for e in errors:
                print("  [ERROR]", e)
        else:
            print("  OK：未发现错误")

    if bad:
        print(f"\n{bad} 个城市存在错误")
        sys.exit(1)


if __name__ == "__main__":
    main()
