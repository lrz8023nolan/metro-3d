# -*- coding: utf-8 -*-
"""从线路关系中提取全部成员节点 id，并抓取其标签（名称等）。"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
RAW = os.path.join(BASE, "data", "raw", "osm")
UA = "BeijingMetroMap/0.1 (personal research; OSM data collection)"
PROXIES = ["http://127.0.0.1:7897", None]


def post_overpass(query: str, timeout: int = 180):
    data = urllib.parse.urlencode({"data": query}).encode()
    last_err = None
    for _ in range(3):
        for proxy in PROXIES:
            try:
                req = urllib.request.Request(
                    "https://overpass-api.de/api/interpreter",
                    data=data,
                    headers={"User-Agent": UA},
                )
                if proxy:
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler({"http": proxy, "https": proxy})
                    )
                else:
                    opener = urllib.request.build_opener()
                with opener.open(req, timeout=timeout) as resp:
                    body = resp.read()
                if body.lstrip().startswith(b"{"):
                    return json.loads(body)
                last_err = body[:200].decode("utf-8", "replace")
            except Exception as exc:  # noqa: BLE001
                last_err = repr(exc)
        time.sleep(8)
    raise RuntimeError(f"overpass failed: {last_err}")


def main():
    geom = json.load(open(os.path.join(RAW, "beijing_routes_geom.json"), encoding="utf-8"))
    refs = set()
    for rel in geom["elements"]:
        for m in rel.get("members", []):
            if m["type"] == "node":
                refs.add(m["ref"])
    refs = sorted(refs)
    print(f"unique member nodes: {len(refs)}")

    out = os.path.join(RAW, "beijing_stop_nodes.json")
    existing = []
    if os.path.exists(out):
        existing = json.load(open(out, encoding="utf-8"))["elements"]
    have = {e["id"] for e in existing}
    todo = [r for r in refs if r not in have]
    if not todo:
        print(f"all {len(refs)} nodes already fetched")
        return

    chunk = 250
    parts = []
    for i in range(0, len(todo), chunk):
        ids = ",".join(map(str, todo[i : i + chunk]))
        parts.append(f"node(id:{ids});")
    q = f"[out:json][timeout:120];({' '.join(parts)});out body;"
    print(f"querying {len(todo)} nodes…")
    d = post_overpass(q)
    merged = {e["id"]: e for e in existing}
    for e in d["elements"]:
        merged[e["id"]] = e
    out_d = {"version": 0.6, "elements": sorted(merged.values(), key=lambda e: e["id"])}
    json.dump(out_d, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    named = sum(1 for e in out_d["elements"] if e.get("tags", {}).get("name"))
    print(f"saved {len(out_d['elements'])} nodes, {named} with name tag")


if __name__ == "__main__":
    main()
