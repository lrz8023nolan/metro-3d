# -*- coding: utf-8 -*-
"""从 Overpass API 抓取北京地铁线路几何与车站节点（原始数据）。"""
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
BBOX = "39.4,115.8,40.6,117.1"
PROXIES = ["http://127.0.0.1:7897", None]  # 先试本地代理，再试环境默认


def post_overpass(query: str, timeout: int = 300):
    data = urllib.parse.urlencode({"data": query}).encode()
    last_err = None
    for attempt in range(3):
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
                last_err = body[:300].decode("utf-8", "replace")
            except Exception as exc:  # noqa: BLE001
                last_err = repr(exc)
        time.sleep(10)
    raise RuntimeError(f"overpass failed after retries: {last_err}")


def main():
    tags_file = os.path.join(RAW, "beijing_routes_tags.json")
    tags = json.load(open(tags_file, encoding="utf-8"))
    ids = [e["id"] for e in tags["elements"]]
    print(f"relations from tags file: {len(ids)}")

    # 1) 线路几何：一次性取全部关系（含成员几何）
    out = os.path.join(RAW, "beijing_routes_geom.json")
    if not os.path.exists(out):
        q = f'[out:json][timeout:300];rel(id:{",".join(map(str, ids))});out geom;'
        d = post_overpass(q)
        json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"routes geom saved: {len(d['elements'])} relations, "
              f"{os.path.getsize(out) / 1e6:.1f} MB")
    else:
        print("routes geom exists, skip")

    # 2) 车站节点（地铁/轻轨/磁浮站点）
    out2 = os.path.join(RAW, "beijing_stations_osm.json")
    if not os.path.exists(out2):
        q = (
            f'[out:json][timeout:180];'
            f'('
            f'nwr["station"~"^(subway|light_rail|monorail)$"]({BBOX});'
            f'nwr["railway"="station"]["subway"="yes"]({BBOX});'
            f');'
            f'out center;'
        )
        d2 = post_overpass(q)
        json.dump(d2, open(out2, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"stations saved: {len(d2['elements'])} elements")
    else:
        print("stations exist, skip")


if __name__ == "__main__":
    main()
