# -*- coding: utf-8 -*-
"""抓取地面高程：① 全部车站点高程；② 北京地铁覆盖范围地形网格。

数据源：OpenTopoData 公共 API（SRTM 30m)，100 点/请求，请求间隔约 1.2s。
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
RAW = os.path.join(BASE, "data", "raw", "elevation")
OUT = os.path.join(BASE, "data", "processed")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

UA = "BeijingMetroMap/0.1 (personal research; elevation data)"
PROXIES = ["http://127.0.0.1:7897", None]
API = "https://api.opentopodata.org/v1/srtm30m"
DATASET = "srtm30m"

# 地形网格范围（覆盖全部线路）+ 分辨率
GRID_BBOX = (39.40, 115.85, 40.40, 117.05)  # south, west, north, east
GRID_STEP = 0.01  # 约 1.1 km


def query(locations):
    """locations: [(lat, lon), ...] 最多 100 个。"""
    loc_str = "|".join(f"{la:.6f},{lo:.6f}" for la, lo in locations)
    url = f"{API}?locations={urllib.parse.quote(loc_str)}&interpolation=cubic"
    last = None
    for _ in range(3):
        for proxy in PROXIES:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                if proxy:
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler({"http": proxy, "https": proxy})
                    )
                else:
                    opener = urllib.request.build_opener()
                with opener.open(req, timeout=60) as resp:
                    d = json.loads(resp.read())
                if d.get("status") == "OK":
                    return d["results"]
                last = d.get("error", d)
            except Exception as exc:  # noqa: BLE001
                last = repr(exc)
        time.sleep(5)
    raise RuntimeError(f"elevation api failed: {last}")


def fetch_stations():
    stations = json.load(open(os.path.join(OUT, "stations.json"), encoding="utf-8"))
    raw_path = os.path.join(RAW, "stations_elevation_raw.json")
    if os.path.exists(raw_path):
        print("stations elevation exists, skip")
        return
    all_res = []
    batch = 100
    for i in range(0, len(stations), batch):
        chunk = stations[i : i + batch]
        locs = [(s["lat"], s["lon"]) for s in chunk]
        res = query(locs)
        all_res.extend(res)
        print(f"stations {i + len(chunk)}/{len(stations)}")
        time.sleep(1.2)
    json.dump(all_res, open(raw_path, "w", encoding="utf-8"), ensure_ascii=False)

    with open(os.path.join(OUT, "station_elevation.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "lat", "lon", "elevation_m", "dataset"])
        for s, r in zip(stations, all_res):
            w.writerow([s["name"], s["lat"], s["lon"], r["elevation"], DATASET])
    print(f"station elevations saved: {len(all_res)}")


def fetch_grid():
    raw_path = os.path.join(RAW, "terrain_grid_raw.json")
    if os.path.exists(raw_path):
        print("terrain grid exists, skip")
        return
    s, w_, n, e = GRID_BBOX
    lats = []
    la = s
    while la <= n + 1e-9:
        lats.append(round(la, 4))
        la += GRID_STEP
    lons = []
    lo = w_
    while lo <= e + 1e-9:
        lons.append(round(lo, 4))
        lo += GRID_STEP
    points = [(la, lo) for la in lats for lo in lons]
    print(f"grid: {len(lats)} x {len(lons)} = {len(points)} points")

    all_res = []
    batch = 100
    for i in range(0, len(points), batch):
        res = query(points[i : i + batch])
        all_res.extend(res)
        if (i // batch) % 10 == 0:
            print(f"grid {i + len(res)}/{len(points)}")
        time.sleep(1.2)
    json.dump(all_res, open(raw_path, "w", encoding="utf-8"), ensure_ascii=False)

    with open(os.path.join(OUT, "terrain_grid.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["lat", "lon", "elevation_m", "dataset"])
        for r in all_res:
            wtr.writerow([r["location"]["lat"], r["location"]["lng"], r["elevation"], DATASET])
    print(f"terrain grid saved: {len(all_res)}")


if __name__ == "__main__":
    fetch_stations()
    fetch_grid()
    print("done")
