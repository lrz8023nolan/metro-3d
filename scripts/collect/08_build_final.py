# -*- coding: utf-8 -*-
"""构建最终整合数据集 data/processed/beijing_metro.json（统一 schema）。

合并：OSM 基线 + 维基车站列表 + 维基埋深证据 + 新闻埋深 + 高程 + 楼层 + 人工修正。
"""
import csv
import json
import os
import re
import sys
from collections import OrderedDict

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
P = os.path.join(BASE, "data", "processed")
M = os.path.join(BASE, "data", "manual")
RAW = os.path.join(BASE, "data", "raw")

LINE_NAMES = {
    "1": "1号线（含八通线）", "2": "2号线", "3": "3号线", "4": "4号线", "dx": "大兴线",
    "5": "5号线", "6": "6号线", "7": "7号线", "8": "8号线", "9": "9号线", "10": "10号线",
    "11": "11号线", "12": "12号线", "13": "13号线", "14": "14号线", "15": "15号线",
    "16": "16号线", "17": "17号线", "18": "18号线", "19": "19号线", "yz": "亦庄线",
    "fs": "房山线", "yf": "燕房线", "cp": "昌平线", "s1": "S1线", "t1": "亦庄T1线",
    "xj": "西郊线", "jc": "首都机场线", "dxjc": "大兴机场线",
}
# Module:Adjacent stations/北京地铁 中的键名 -> 本数据集线路 id
MODULE_KEYS = {
    "1": "1", "2": "2", "3": "3", "4": "4", "大兴": "dx", "5": "5", "6": "6", "7": "7",
    "8": "8", "9": "9", "10": "10", "11": "11", "12": "12", "13": "13", "14": "14",
    "15": "15", "16": "16", "17": "17", "18": "18", "19": "19", "亦庄": "yz", "房山": "fs",
    "燕房": "yf", "昌平": "cp", "S1": "s1", "西郊": "xj", "首都机场": "jc", "大兴机场": "dxjc",
}
# 模块内日期笔误/格式覆盖
OPEN_DATE_OVERRIDES = {"8": "2008-07-19"}
PRIORITY = {"轨面": 1, "底板": 1, "埋深范围": 1.8, "信息框": 2, "最大深度": 2.2, "埋深未注": 2.5, "地下X米": 3}
NEWS_PRIORITY = 1.5


def norm_date(d):
    if not d:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", d)
    if not m:
        return d
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def load_module_meta():
    """从 Module:Adjacent stations/北京地铁 提取颜色与开通日期（lines 区段）。"""
    path = os.path.join(RAW, "wikipedia", "landing", "module_adjacent.txt")
    wt = open(path, encoding="utf-8").read()
    out = {}
    for mkey, lid in MODULE_KEYS.items():
        m = re.search(r'\["' + re.escape(mkey) + r'"\]\s*=\s*\{', wt)
        if not m:
            continue
        chunk = wt[m.start() : m.start() + 1200]
        c = re.search(r'\[["\']color["\']\]\s*=\s*"([0-9A-Fa-f]{6})"', chunk)
        d = re.search(r'\[["\']open date["\']\]\s*=\s*"([0-9\-]+)"', chunk)
        if c:
            out.setdefault(lid, {})["colour"] = "#" + c.group(1)
        if d:
            out.setdefault(lid, {})["open_date"] = norm_date(d.group(1))
    for lid, d in OPEN_DATE_OVERRIDES.items():
        if lid in out:
            out[lid]["open_date"] = d
            out[lid]["open_date_note"] = "模块内日期笔误，已按一期开通日期修正"
    return out


def infobox_depths(station_names):
    """从维基页面直接提取信息框 depth 值。"""
    pages_dir = os.path.join(RAW, "wikipedia", "pages")
    out = {}
    for fn in os.listdir(pages_dir):
        p = json.load(open(os.path.join(pages_dir, fn), encoding="utf-8"))
        wt = p["wikitext"]
        m = re.search(r"\|\s*(?:depth|深度)\s*=\s*([^\n|}]*)", wt)
        if not m:
            continue
        num = re.search(r"([0-9]+(?:\.[0-9]+)?)", m.group(1))
        if not num:
            continue
        nm = re.search(r"\|\s*name\s*=\s*([^\n|}]+)", wt)
        cand = re.sub(r"<[^>]+>", "", nm.group(1)).strip() if nm else ""
        cands = [cand, p["title"], re.sub(r"[（(][^（）()]*[）)]\s*$", "", p["title"]).strip()]
        for c in cands:
            if c in station_names:
                out.setdefault(c, {"value": float(num.group(1)), "title": p["title"], "revid": p.get("revid")})
                break
    return out


def snorm(n):
    """站名归一：去语言转换标记 -{}-，去尾部括号注释。"""
    n = re.sub(r"-{[^}]*}-", "", n)
    n = re.sub(r"[（(][^（）()]*[）)]\s*$", "", n)
    return n.strip()


def main():
    lines = json.load(open(os.path.join(P, "lines.json"), encoding="utf-8"))
    stations = json.load(open(os.path.join(P, "stations.json"), encoding="utf-8"))
    corrections = json.load(open(os.path.join(M, "corrections.json"), encoding="utf-8"))
    news = json.load(open(os.path.join(M, "depth_news.json"), encoding="utf-8"))["items"]
    module_meta = load_module_meta()

    # ---- wiki 车站列表属性 ----
    TRANSFER_MAP = {"昌": "昌平线", "房": "房山线", "燕": "燕房线", "亦": "亦庄线", "大": "大兴线", "S1": "S1线"}
    wiki_attrs = {}
    for r in csv.DictReader(open(os.path.join(P, "wiki_line_stations.csv"), encoding="utf-8-sig")):
        nm = snorm(r["name"])
        a = wiki_attrs.setdefault(nm, {"laying": "", "open_date": "", "district": "", "platform": "", "transfers": "", "name_en": ""})
        for k in ("laying", "open_date", "district", "platform", "transfers", "name_en"):
            if not a[k] and r.get(k):
                v = r[k]
                if k == "transfers":
                    v = re.sub(r"[\"']", "", v)
                    v = re.sub(r"转([昌房燕亦大])", lambda m: "转" + TRANSFER_MAP[m.group(1)], v)
                a[k] = v

    # ---- 埋深证据 ----
    depth_rows = list(csv.DictReader(open(os.path.join(P, "depth_evidence_wiki.csv"), encoding="utf-8-sig")))
    for r in depth_rows:
        r["value_m"] = float(r["value_m"])
        r["value2_m"] = float(r["value2_m"]) if r["value2_m"] else None
    infobox = infobox_depths({s["name"] for s in stations})

    # ---- 高程 / 楼层 ----
    elev = {}
    for r in csv.DictReader(open(os.path.join(P, "station_elevation.csv"), encoding="utf-8-sig")):
        elev[r["name"]] = float(r["elevation_m"])
    floors = json.load(open(os.path.join(P, "station_floors_wiki.json"), encoding="utf-8"))

    # ---- 应用修正 ----
    renames = corrections.get("station_renames", {})
    for old, new in renames.items():
        if old in elev:
            elev[new] = elev[old]
        if old in floors:
            floors[new] = floors[old]
    rings = set(corrections.get("ring_dedupe", []))
    for l in lines:
        seq = [renames.get(n, n) for n in l["station_sequence"]]
        if l["id"] in rings and len(seq) > 1 and seq[0] == seq[-1]:
            seq = seq[:-1]
        l["station_sequence"] = seq
    line_by_id = {l["id"]: l for l in lines}
    add_problems = []
    for add in corrections["station_additions"]:
        for lid in add["lines"]:
            l = line_by_id[lid]
            seq = l["station_sequence"]
            if add["name"] in seq:
                continue
            anchor = add["insert_before"]
            if anchor not in seq:
                add_problems.append(f"{add['name']}: 锚点 {anchor} 不在 {lid} 站序中")
                continue
            seq.insert(seq.index(anchor), add["name"])

    st_by_name = {s["name"]: s for s in stations}
    # 重命名站
    for old, new in renames.items():
        if old in st_by_name:
            st = st_by_name.pop(old)
            st["name"] = new
            st["id"] = new
            st.setdefault("notes", []).append(f"原始 OSM 站名：{old}（已规范化）")
            st_by_name[new] = st
    # 新增站
    for add in corrections["station_additions"]:
        nm = add["name"]
        if nm in st_by_name:
            continue
        st_by_name[nm] = {
            "id": nm, "name": nm, "name_en": add.get("name_en"), "lat": add["lat"], "lon": add["lon"],
            "lines": [], "osm_node_ids": [], "depth_m": None, "depth_src": None, "depth_conf": None,
            "status": add.get("status", "operational"), "notes": [add.get("note", "")],
        }
    # 重建站点归属线路
    for st in st_by_name.values():
        st["lines"] = []
    for l in lines:
        for nm in l["station_sequence"]:
            if nm in st_by_name:
                st_by_name[nm]["lines"].append(l["id"])
            else:
                add_problems.append(f"站序中的站不存在于站点表：{l['id']}/{nm}")

    # ---- 组装输出 ----
    lines_out = []
    for l in sorted(lines, key=lambda x: x["id"]):
        meta_l = module_meta.get(l["id"], {})
        seq = l["station_sequence"]
        line_notes = list(l.get("notes", []))
        if meta_l.get("open_date_note"):
            line_notes.append(meta_l["open_date_note"])
        lines_out.append({
            "id": l["id"], "name": LINE_NAMES.get(l["id"], l["name"]),
            "type": l["type"], "colour": meta_l.get("colour") or l["colour"],
            "open_date": meta_l.get("open_date"),
            "length_km": l["length_km"], "station_count": len(seq),
            "station_sequence": seq,
            "from": seq[0] if seq else None, "to": seq[-1] if seq else None,
            "geometry": l["geometry"],
            "direction_relations": [d["rel_id"] for d in l["directions"]],
            "notes": line_notes,
        })

    stations_out = []
    for nm, st in sorted(st_by_name.items()):
        wa = wiki_attrs.get(snorm(nm), {})
        d = {
            "id": nm, "name": nm, "name_en": st.get("name_en") or wa.get("name_en") or None,
            "lat": round(st["lat"], 6), "lon": round(st["lon"], 6),
            "lines": sorted(st["lines"]),
            "status": st.get("status", "operational"),
            "elevation_m": elev.get(nm),
            "floors": floors.get(nm) or floors.get(snorm(nm)),
            "laying": wa.get("laying") or None,
            "open_date": wa.get("open_date") or None,
            "district": wa.get("district") or None,
            "platform": wa.get("platform") or None,
            "transfers": wa.get("transfers") or None,
            "depth_m": None, "depth_min_m": None, "depth_max_m": None,
            "depth_measure": None, "depth_source": None, "depth_conf": None,
            "depth_alt": [], "notes": st.get("notes", []),
        }
        # — 深度选择 —
        cands = []
        for r in depth_rows:
            if r["station"] != nm:
                continue
            if r["type"] in ("覆土", "顶板", "基坑"):
                d["depth_alt"].append(f"{r['type']}={r['value_m']}m（非站体口径，仅供参考）")
                continue
            cands.append({
                "prio": PRIORITY.get(r["type"], 9), "value": r["value_m"], "value2": r["value2_m"],
                "type": r["type"], "src": f"zh.wikipedia:{r['title']}", "ev": r["evidence"],
                "conf": "high" if r["type"] in ("轨面", "底板") else ("medium" if r["type"] in ("埋深范围", "埋深未注") else "low"),
            })
        if nm in infobox:
            cands.append({"prio": PRIORITY["信息框"], "value": infobox[nm]["value"], "value2": None,
                          "type": "信息框", "src": f"zh.wikipedia:{infobox[nm]['title']}（信息框）",
                          "ev": "信息框 depth 字段", "conf": "high"})
        for n in news:
            if n["station"] != nm:
                continue
            cands.append({
                "prio": NEWS_PRIORITY, "value": n["depth_m"], "value2": None,
                "type": n["measure"], "src": n["source"], "ev": n.get("note", ""),
                "conf": n.get("conf", "medium"),
                "min": n.get("depth_min_m"), "max": n.get("depth_max_m"),
            })
        if cands:
            cands.sort(key=lambda c: c["prio"])
            best = cands[0]
            same = [c for c in cands if c["prio"] == best["prio"]]
            if len(same) > 1:
                best = max(same, key=lambda c: c["value"])  # 同口径取最深（站体分层）
            d["depth_m"] = best["value"]
            if best.get("min") or best.get("max"):
                d["depth_min_m"] = best.get("min")
                d["depth_max_m"] = best.get("max")
            elif best["value2"]:
                d["depth_min_m"] = min(best["value"], best["value2"])
                d["depth_max_m"] = max(best["value"], best["value2"])
            d["depth_measure"] = best["type"]
            d["depth_source"] = best["src"]
            d["depth_conf"] = best["conf"]
            for c in cands:
                if c is best:
                    continue
                d["depth_alt"].append(f"{c['type']}={c['value']}m（{c['src']}）")
        stations_out.append(d)

    meta = {
        "city": "beijing",
        "name": "北京地铁",
        "generated": "2026-10-14",
        "crs": "WGS-84（OSM）；GCJ-02 底图叠加时需转换",
        "sources": [
            "OpenStreetMap（ODbL）线路关系与车站节点，截取 2026-10-14",
            "中文维基百科（CC BY-SA）车站条目与车站列表，截取 2026-10-14",
            "新闻/公开报道（见各站 depth_source）",
            "OpenTopoData srtm30m 地面高程",
        ],
        "counts": {
            "lines": len(lines_out),
            "stations": len(stations_out),
            "stations_with_depth": sum(1 for s in stations_out if s["depth_m"] is not None),
            "stations_with_elevation": sum(1 for s in stations_out if s["elevation_m"] is not None),
            "stations_with_laying": sum(1 for s in stations_out if s["laying"]),
        },
        "disclaimers": [
            "埋深数据为公开资料汇编，口径不一（底板/轨面/报道口径），置信度见 depth_conf；插值补齐见后续流程。",
            "八角游乐园站封站改造中（通过不停车），status=suspended。",
        ],
    }
    out = {"meta": meta, "lines": lines_out, "stations": stations_out}
    json.dump(out, open(os.path.join(P, "beijing_metro.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # CSV 审阅表
    with open(os.path.join(P, "stations_final.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "lines", "lat", "lon", "elevation_m", "floors", "laying", "open_date",
                    "depth_m", "depth_measure", "depth_conf", "depth_source", "status", "transfers"])
        for s in stations_out:
            w.writerow([s["name"], "/".join(s["lines"]), s["lat"], s["lon"], s["elevation_m"], s["floors"],
                        s["laying"], s["open_date"], s["depth_m"], s["depth_measure"], s["depth_conf"],
                        s["depth_source"], s["status"], s["transfers"]])

    # ---- 摘要 ----
    print("== 汇总 ==")
    print(f"线路 {meta['counts']['lines']}，车站 {meta['counts']['stations']}")
    print(f"有埋深: {meta['counts']['stations_with_depth']}  有高程: {meta['counts']['stations_with_elevation']}  "
          f"有敷设方式: {meta['counts']['stations_with_laying']}")
    print()
    print("== 每线站数 ==")
    for l in lines_out:
        print(f"  {l['id']:>4} {l['name']:<14} {l['station_count']:>3} 站  {l['length_km']:>6.1f}km  色={l['colour']}  开通={l['open_date']}")
    print()
    print("== 有埋深的车站 ==")
    for s in stations_out:
        if s["depth_m"] is not None:
            extra = f" ({'/'.join(s['depth_alt'])})" if s["depth_alt"] else ""
            print(f"  {s['name']:<10} {s['depth_m']:>6}m [{s['depth_measure']}/{s['depth_conf']}]{extra}")
    if add_problems:
        print()
        print("== 修正问题 ==")
        for p in add_problems:
            print("  ", p)


if __name__ == "__main__":
    main()
