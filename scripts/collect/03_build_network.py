# -*- coding: utf-8 -*-
"""把 OSM 原始数据整理成结构化线路/车站数据（data/processed）。"""
import json
import math
import os
import re
import sys
from collections import OrderedDict

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
RAW = os.path.join(BASE, "data", "raw", "osm")
OUT = os.path.join(BASE, "data", "processed")
os.makedirs(OUT, exist_ok=True)

LINE_MAP = {
    "1": ("1", "1号线（含八通线）", "metro"),
    "2": ("2", "2号线", "metro"),
    "3": ("3", "3号线", "metro"),
    "4": ("4", "4号线", "metro"),
    "4S": ("dx", "大兴线", "metro"),
    "5": ("5", "5号线", "metro"),
    "6": ("6", "6号线", "metro"),
    "7": ("7", "7号线", "metro"),
    "8": ("8", "8号线", "metro"),
    "9": ("9", "9号线", "metro"),
    "10": ("10", "10号线", "metro"),
    "11": ("11", "11号线", "metro"),
    "12": ("12", "12号线", "metro"),
    "13": ("13", "13号线", "metro"),
    "14": ("14", "14号线", "metro"),
    "15": ("15", "15号线", "metro"),
    "16": ("16", "16号线", "metro"),
    "17": ("17", "17号线", "metro"),
    "18": ("18", "18号线", "metro"),
    "19": ("19", "19号线", "metro"),
    "24;L2": ("yz", "亦庄线", "metro"),
    "25N": ("fs", "房山线", "metro"),
    "25S": ("yf", "燕房线", "metro"),
    "27": ("cp", "昌平线", "metro"),
    "S1;26": ("s1", "S1线", "maglev"),
    "T1": ("t1", "亦庄T1线", "tram"),
    "西郊": ("xj", "西郊线", "tram"),
    "L1": ("jc", "首都机场线", "express"),
}
NAME_MAP = [
    ("大兴机场线", ("dxjc", "大兴机场线", "express")),
    ("12号线", ("12", "12号线", "metro")),
]
EXCLUDE_REFS = {"1E"}
EXCLUDE_NAME_KEYWORDS = ["八达岭", "前门大街有轨电车", "雄安R1", "4号线/大兴线"]
# 人工修补：OSM 缺口（见 reports/data_inventory.md 说明）
SEQ_PATCHES = {
    "13": {"append": ["西直门"], "note": "OSM 双向关系均缺西直门站节点（几何已覆盖该段），站序由人工补齐"},
}


def norm_name(tags: dict):
    """规范化站名：优先 name，缺则用 name:zh；去掉尾部括号消歧后缀。"""
    nm = tags.get("name") or tags.get("name:zh")
    if nm:
        nm = re.sub(r"[（(][^（）()]*[）)]\s*$", "", nm).strip()
    return nm


def hav(a, b):
    dx = (b[0] - a[0]) * 111320 * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = (b[1] - a[1]) * 110540
    return math.hypot(dx, dy)


def way_len(g):
    return sum(hav(a, b) for a, b in zip(g, g[1:]))


def dedupe(pts):
    out = [pts[0]] if pts else []
    for p in pts[1:]:
        if hav(out[-1], p) > 0.5:
            out.append(p)
    return out


def stitch_in_order(ways):
    pts, jumps = [], []
    for g in ways:
        if not g:
            continue
        if not pts:
            pts.extend(g)
            continue
        d1, d2 = hav(pts[-1], g[0]), hav(pts[-1], g[-1])
        if d1 < 5:
            pts.extend(g[1:])
        elif d2 < 5:
            pts.extend(g[-2::-1] if len(g) > 1 else g)
        else:
            jumps.append(min(d1, d2))
            pts.extend(g if d1 <= d2 else g[::-1])
    return dedupe(pts), jumps, []


def stitch_bidir(ways):
    """双端可延伸的贪心链：任一方式接入链首或链尾。

    短小闭合环（起终点同位置）若无法就近接入链端，视为映射痕迹单独记录。
    """
    rem = [list(w) for w in ways if w]
    if not rem:
        return [], [], []
    rem.sort(key=len, reverse=True)
    chain = rem.pop(0)
    jumps, detached = [], []
    while rem:
        best = None  # (d, idx, side, mode)
        for i, w in enumerate(rem):
            cands = [
                (hav(chain[-1], w[0]), "end", "fw"),
                (hav(chain[-1], w[-1]), "end", "rv"),
                (hav(chain[0], w[-1]), "start", "fw"),
                (hav(chain[0], w[0]), "start", "rv"),
            ]
            for d, side, mode in cands:
                if best is None or d < best[0]:
                    best = (d, i, side, mode)
        d, i, side, mode = best
        w = rem.pop(i)
        if d > 300:
            closed = hav(w[0], w[-1]) < 50
            short = way_len(w) < 2000
            if closed and short:
                detached.append(w)
                continue
            jumps.append(d)
        seq = w if mode == "fw" else w[::-1]
        if side == "end":
            chain.extend(seq[1:])
        else:
            chain = seq[:-1] + chain
    return dedupe(chain), jumps, detached


def pick_geometry(way_geoms):
    sum_len = sum(way_len(w) for w in way_geoms)
    candidates = [stitch_in_order(way_geoms), stitch_bidir(way_geoms)]
    best = min(candidates, key=lambda c: (len(c[1]), max(c[1]) if c[1] else 0))
    return best, sum_len


def get_line_key(rel):
    t = rel["tags"]
    ref = t.get("ref") or ""
    name = t.get("name") or ""
    if ref in LINE_MAP:
        return LINE_MAP[ref]
    for kw, val in NAME_MAP:
        if kw in name:
            return val
    m = re.search(r"(\d+)号线", name)
    if m and m.group(1) in LINE_MAP:
        return LINE_MAP[m.group(1)]
    return None


def merge_terminus(main_names, other_names):
    """把 other 中相对 main 缺失的端点站补入主站序。"""
    merged = list(main_names)
    for cand in (other_names, list(reversed(other_names))):
        if len(cand) < 2 or len(merged) < 2:
            continue
        if cand[0] not in merged and cand[1] == merged[0]:
            merged.insert(0, cand[0])
        if cand[-1] not in merged and cand[-2] == merged[-1]:
            merged.append(cand[-1])
    return merged


def main():
    geom = json.load(open(os.path.join(RAW, "beijing_routes_geom.json"), encoding="utf-8"))
    nodes = {
        e["id"]: e
        for e in json.load(open(os.path.join(RAW, "beijing_stop_nodes.json"), encoding="utf-8"))["elements"]
    }

    lines = OrderedDict()
    excluded = []
    for rel in geom["elements"]:
        t = rel["tags"]
        name = t.get("name", "")
        if t.get("ref") in EXCLUDE_REFS or any(k in name for k in EXCLUDE_NAME_KEYWORDS):
            excluded.append({"rel_id": rel["id"], "name": name, "reason": "非地铁/已合并/未开通"})
            continue
        key = get_line_key(rel)
        if key is None:
            excluded.append({"rel_id": rel["id"], "name": name, "reason": "未识别"})
            continue
        lid, disp, ltype = key

        way_geoms = [
            [(p["lon"], p["lat"]) for p in m["geometry"]]
            for m in rel["members"]
            if m["type"] == "way" and m.get("geometry")
        ]
        (chain, jumps, detached), sum_len = pick_geometry(way_geoms)
        stops = [
            m["ref"]
            for m in rel["members"]
            if m["type"] == "node" and m.get("role") == "stop" and m["ref"] in nodes
        ]

        e = lines.setdefault(lid, {"id": lid, "name": disp, "type": ltype, "colour": None, "directions": [], "_seqs": []})
        if t.get("colour"):
            e["colour"] = t["colour"]
        e["directions"].append({
            "rel_id": rel["id"], "from": t.get("from"), "to": t.get("to"), "name": name,
            "stops": len(stops), "points": len(chain),
            "jumps": [round(j) for j in jumps], "way_sum_km": round(sum_len / 1000, 2),
            "detached": [round(way_len(w) / 1000, 3) for w in detached],
        })
        e["_seqs"].append({"rel_id": rel["id"], "stops": stops, "geometry": chain, "sum_len": sum_len,
                           "from": t.get("from"), "to": t.get("to")})

    lines_out, problems = [], []
    for lid, e in lines.items():
        seqs = e["_seqs"]

        def names_of(s):
            return [norm_name(nodes[x]["tags"]) or "?" for x in s["stops"]]

        main = max(seqs, key=lambda s: (len(s["stops"]), len(s["geometry"])))
        main_names = names_of(main)
        for other in seqs:
            if other is main:
                continue
            merged = merge_terminus(main_names, names_of(other))
            if len(merged) > len(main_names):
                main_names = merged
        notes = []
        patch = SEQ_PATCHES.get(lid)
        if patch:
            for nm in patch.get("append", []):
                if nm not in main_names:
                    main_names = main_names + [nm]
            if patch.get("note"):
                notes.append(patch["note"])
        union_names = set().union(*[set(names_of(s)) for s in seqs])
        miss = union_names - set(main_names)
        if miss:
            problems.append(f"{lid}: 主站序缺 {sorted(miss)}")
        if main["sum_len"] < 1:
            problems.append(f"{lid}: 主方向几何为空")

        lines_out.append({
            "id": e["id"], "name": e["name"], "type": e["type"], "colour": e["colour"],
            "length_km": round(max(s["sum_len"] for s in seqs) / 1000, 2),
            "directions": e["directions"],
            "station_sequence": main_names,
            "rel_id_main": main["rel_id"], "from": main["from"], "to": main["to"],
            "geometry": [[round(x, 7), round(y, 7)] for x, y in main["geometry"]],
            "notes": notes,
        })

    # 车站主表：两个方向的站并集（按规范化名称）
    stations = OrderedDict()
    for lid, e in lines.items():
        for seq in e["_seqs"]:
            for s in seq["stops"]:
                nd = nodes[s]
                nm = norm_name(nd["tags"])
                if not nm:
                    continue
                st = stations.setdefault(nm, {"coords": [], "lines": set(), "name_en": None, "node_ids": []})
                st["coords"].append((nd["lon"], nd["lat"]))
                st["lines"].add(e["id"])
                st["node_ids"].append(nd["id"])
                if nd["tags"].get("name:en"):
                    st["name_en"] = st["name_en"] or nd["tags"]["name:en"]

    stations_out = []
    for nm, st in stations.items():
        lons = [c[0] for c in st["coords"]]
        lats = [c[1] for c in st["coords"]]
        stations_out.append({
            "id": nm, "name": nm, "name_en": st["name_en"],
            "lat": round(sum(lats) / len(lats), 7), "lon": round(sum(lons) / len(lons), 7),
            "lines": sorted(st["lines"]), "osm_node_ids": st["node_ids"],
            "depth_m": None, "depth_src": None, "depth_conf": None,
        })

    json.dump(lines_out, open(os.path.join(OUT, "lines.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(stations_out, open(os.path.join(OUT, "stations.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("== 线路 ==")
    for l in sorted(lines_out, key=lambda x: x["id"]):
        jumps = "; ".join(f"{len(d['jumps'])}跳({max(d['jumps']) if d['jumps'] else 0}m)" for d in l["directions"])
        print(f"  {l['id']:>4} {l['name']:<12} {l['length_km']:>6.1f}km 站={len(l['station_sequence']):>3} "
              f"色={str(l['colour']):<8} 几何断裂: {jumps}")
    print(f"\n线路: {len(lines_out)}  车站(去重): {len(stations_out)}")
    if problems:
        print("\n== 需注意 ==")
        for p in problems:
            print("  ", p)
    if excluded:
        print("\n== 排除 ==")
        for x in excluded:
            print("  ", x["rel_id"], x["name"], "|", x["reason"])


if __name__ == "__main__":
    main()
