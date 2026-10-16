# -*- coding: utf-8 -*-
"""从维基百科 wikitext 中提取车站埋深证据。

输出：
- data/processed/depth_evidence_wiki.csv  原始证据（每条匹配一行，含上下文）
- 控制台摘要：多少站有深度信息、按测量口径分布
"""
import csv
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
PAGES = os.path.join(BASE, "data", "raw", "wikipedia", "pages")
OUT = os.path.join(BASE, "data", "processed")
STATIONS = os.path.join(OUT, "stations.json")

NUM = r"([0-9]+(?:\.[0-9]+)?)"
# 按特异性排序：先具体口径，后笼统口径
PATTERNS = [
    (re.compile(rf"埋深(?:达|为|约|至|在|共)?\s*{NUM}\s*(?:至|~|—|-)\s*{NUM}\s*(?:米|m)"), "埋深范围", 2),
    (re.compile(rf"轨面埋深(?:为|约|达)?\s*{NUM}\s*(?:米|m)"), "轨面", 1),
    (re.compile(rf"底板埋深(?:为|约|达)?\s*{NUM}\s*(?:米|m)"), "底板", 1),
    (re.compile(rf"底板最深处距地面\s*{NUM}\s*米"), "底板", 1),
    (re.compile(rf"(?:车站)?最大深度(?:达|为|约)?\s*{NUM}\s*(?:米|m)"), "最大深度", 1),
    (re.compile(rf"埋深(?:达|为|约|至|在)?\s*{NUM}\s*(?:米|m)"), "埋深未注", 1),
    (re.compile(rf"顶板(?:最深处)?距地面\s*{NUM}(?:\s*至\s*{NUM})?\s*米"), "顶板", 2),
    (re.compile(rf"覆土(?:厚度)?(?:约|为|达)?\s*{NUM}\s*米"), "覆土", 2),
    (re.compile(rf"基坑(?:深度)?(?:达|约|为)?\s*{NUM}\s*米"), "基坑", 2),
    (re.compile(rf"地下\s*{NUM}\s*米(?:处|深|深处)?"), "地下X米", 3),
    (re.compile(rf"挖深\s*{NUM}\s*米"), "挖深", 2.6),
    (re.compile(rf"[、，,]\s*深\s*{NUM}\s*米"), "站体深度", 2.4),
]
FLOORS = re.compile(r"地下(\d)层|地下共?(\d)层")
INFOBOX = re.compile(r"\|\s*(?:depth|深度)\s*=\s*([^\n|}]*)")
INFOBOX_NAME = re.compile(r"\|\s*name\s*=\s*([^\n|}]+)")


def clean_name(s: str) -> str:
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip().strip("'").strip()


def norm_title(t: str) -> str:
    t = re.sub(r"[（(][^（）()]*[）)]\s*$", "", t).strip()
    t = re.sub(r"站$", "", t).strip()
    return t


def match_name(title: str, wt: str, names: set):
    """返回匹配到的站名（在 names 中），失败返回 None。"""
    cands = []
    m = INFOBOX_NAME.search(wt)
    if m:
        cands.append(clean_name(m.group(1)))
    cands.append(title)
    t = re.sub(r"[（(][^（）()]*[）)]\s*$", "", title).strip()
    cands.append(t)
    cands.append(norm_title(title))
    if t.endswith("站"):
        cands.append(t[:-1].strip())
    for c in cands:
        if c and c in names:
            return c
    return None


def norm_title(t: str) -> str:
    t = re.sub(r"[（(][^（）()]*[）)]\s*$", "", t).strip()
    t = re.sub(r"站$", "", t).strip()
    return t


def clean(s: str) -> str:
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[([^\]|]*)\|?[^\]]*\]\]", r"\1", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def main():
    stations = json.load(open(STATIONS, encoding="utf-8"))
    names = {s["name"] for s in stations}
    rows = []
    floors = {}
    unmatched = []
    infobox_hits = []

    for fn in sorted(os.listdir(PAGES)):
        p = json.load(open(os.path.join(PAGES, fn), encoding="utf-8"))
        title = p["title"]
        wt = p["wikitext"]
        name = match_name(title, wt, names)
        matched = name is not None
        if not matched:
            unmatched.append(title)
            name = norm_title(title)

        # 楼层结构
        for m in FLOORS.finditer(wt):
            lv = m.group(1) or m.group(2)
            floors[name] = max(floors.get(name, 0), int(lv))

        # 信息框 depth 字段
        for m in INFOBOX.finditer(wt):
            v = m.group(1).strip()
            mm = re.search(NUM, v)
            if mm:
                infobox_hits.append((title, name, float(mm.group(1)), v[:40]))

        # 正文证据
        for pat, mtype, prio in PATTERNS:
            for m in pat.finditer(wt):
                if mtype in ("站体深度", "挖深"):
                    pre = wt[max(0, m.start() - 30) : m.start()]
                    if re.search(r"节点|通道|风道|竖井|降水井|围护|连续墙|桩", pre):
                        continue
                v1 = float(m.group(1))
                v2 = float(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else None
                start = max(0, m.start() - 60)
                ctx = clean(wt[start : m.end() + 40])
                rows.append({
                    "title": title,
                    "station": name if matched else "",
                    "value_m": v1,
                    "value2_m": v2 or "",
                    "type": mtype,
                    "priority": prio,
                    "evidence": ctx[:160],
                })

    # 去重（同站同值同类型）
    seen = set()
    dedup = []
    for r in rows:
        key = (r["title"], r["value_m"], r["type"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    out_csv = os.path.join(OUT, "depth_evidence_wiki.csv")
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["title", "station", "value_m", "value2_m", "type", "priority", "evidence"])
        w.writeheader()
        w.writerows(dedup)

    matched_rows = [r for r in dedup if r["station"]]
    by_station = {}
    for r in matched_rows:
        by_station.setdefault(r["station"], []).append(r)

    print(f"页面数: {len(os.listdir(PAGES))}")
    print(f"证据条数: {len(dedup)}（其中可匹配本站数据集的 {len(matched_rows)}）")
    print(f"覆盖车站数: {len(by_station)} / {len(stations)}")
    print(f"信息框 depth 字段有值: {len(infobox_hits)}")
    for t, n, v, raw in infobox_hits[:40]:
        print(f"   [infobox] {t} -> {v}m  ({raw})")
    print()
    print("== 按口径分布 ==")
    from collections import Counter
    print(Counter(r["type"] for r in matched_rows))
    print()
    print("== 样例（匹配站点）==")
    for s, rs in list(by_station.items())[:25]:
        info = "; ".join(f"{r['type']}={r['value_m']}" for r in rs)
        print(f"   {s}: {info}")
    print()
    print(f"未匹配标题 {len(unmatched)} 个（前 30）:")
    print("   " + "; ".join(unmatched[:30]))

    # 楼层信息另存
    json.dump(floors, open(os.path.join(OUT, "station_floors_wiki.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
