# -*- coding: utf-8 -*-
"""Metro-3D · 城市数据集 → 运行时数据（window.METRO_DATA）

City dataset → runtime data.  Reads cities/<city>/ (city.json, terrain_grid.csv,
wiki_line_stations.csv, build_config.json) and writes build/<city>_data.js.

用法 / Usage:  python scripts/build_data.py --city beijing

高度模型
--------
每站取一个"轨道相对地面"的带符号值 v：
  v < 0  地下（= −埋深）；v > 0  高架/地面（= 轨面高出地面）
沿线按弧长分段线性插值，得到每个几何点的轨道海拔 track = ground + v。

埋深三级来源
------------
truth : 维基百科 / 媒体报道的工程数据（带口径、来源、置信度）
est   : 本项目估算 = 真值锚点 + 逐线估算锚点 + 线路缺省值，线性插值（低置信度）
above : 高架/地面站，无需埋深
"""
import argparse
import csv
import json
import math
import os


def load_terrain(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    lats, lons, grid = [], [], {}
    for r in rows:
        la, lo = round(float(r["lat"]), 2), round(float(r["lon"]), 2)
        grid[(la, lo)] = float(r["elevation_m"])
        if la not in lats:
            lats.append(la)
        if lo not in lons:
            lons.append(lo)
    lats.sort()
    lons.sort()
    return lats, lons, grid


def make_sampler(lats, lons, grid):
    def sample(lat, lon):
        la0 = max(lats[0], min(lats[-1], math.floor(lat * 100) / 100))
        lo0 = max(lons[0], min(lons[-1], math.floor(lon * 100) / 100))
        la1 = min(lats[-1], round(la0 + 0.01, 2))
        lo1 = min(lons[-1], round(lo0 + 0.01, 2))
        g = lambda a, o: grid.get((a, o), 0.0)
        tx = (lon - lo0) / 0.01 if lo1 > lo0 else 0.0
        ty = (lat - la0) / 0.01 if la1 > la0 else 0.0
        v = (g(la0, lo0) * (1 - tx) * (1 - ty) + g(la0, lo1) * tx * (1 - ty)
             + g(la1, lo0) * (1 - tx) * ty + g(la1, lo1) * tx * ty)
        return round(v, 1)
    return sample


def dist_m(a, b):
    dx = (b[0] - a[0]) * 111320 * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = (b[1] - a[1]) * 110540
    return math.hypot(dx, dy)


def interp_factory(points):
    """points: [(s, v)] 已排序 → 分段线性取值函数"""
    def f(sv):
        if sv <= points[0][0]:
            return points[0][1]
        if sv >= points[-1][0]:
            return points[-1][1]
        for (s0, v0), (s1, v1) in zip(points, points[1:]):
            if s0 <= sv <= s1:
                if s1 == s0:
                    return v0
                return v0 + (v1 - v0) * (sv - s0) / (s1 - s0)
        return points[-1][1]
    return f


def dedupe_pts(pts):
    pts = sorted(pts, key=lambda x: x[0])
    out = []
    for x in pts:
        if out and abs(x[0] - out[-1][0]) < 1e-6:
            out[-1] = x
        else:
            out.append(x)
    return out


def project_to_polyline(geom, s, lat, lon, lon0, lat0, KX, KY):
    """把站点投影到折线最近线段，返回 (距离m, 段索引, 段内比例, 投影 lon, 投影 lat, 投影弧长)。"""
    px = (lon - lon0) * KX
    py = (lat - lat0) * KY
    best = None
    for i in range(len(geom) - 1):
        ax = (geom[i][0] - lon0) * KX
        ay = (geom[i][1] - lat0) * KY
        bx = (geom[i + 1][0] - lon0) * KX
        by = (geom[i + 1][1] - lat0) * KY
        dx = bx - ax
        dy = by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        qx = ax + t * dx
        qy = ay + t * dy
        d2 = (px - qx) ** 2 + (py - qy) ** 2
        if best is None or d2 < best[0]:
            best = (d2, i, t, qx, qy)
    d2, i, t, qx, qy = best
    return (d2 ** 0.5, i, t, qx / KX + lon0, qy / KY + lat0,
            s[i] + t * (s[i + 1] - s[i]))


def main():
    ap = argparse.ArgumentParser(description="Build runtime data.js for a city")
    ap.add_argument("--city", default="beijing", help="cities/ 下的城市 id")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    city_dir = os.path.join(root, "cities", args.city)
    build_dir = os.path.join(root, "build")
    os.makedirs(build_dir, exist_ok=True)

    cfg = json.load(open(os.path.join(city_dir, "build_config.json"), encoding="utf-8"))
    truth_line = cfg["truth_line"]
    notes = cfg["notes"]
    line_default = cfg["line_default_depth"]
    est_anchors = {k: [tuple(x) for x in v] for k, v in cfg["depth_anchors"].items()}
    offset = cfg["offsets"]
    tram_ground_off = cfg["tram_ground_offset"]
    tram_lines = set(cfg["tram_lines"])
    wiki_alias = cfg["wiki_alias"]
    fallback_colour = cfg["fallback_colour"]
    meas_cn = cfg["measure_cn"]

    d = json.load(open(os.path.join(city_dir, "city.json"), encoding="utf-8"))
    lats, lons, grid = load_terrain(os.path.join(city_dir, "terrain_grid.csv"))
    sample = make_sampler(lats, lons, grid)
    master = {s["name"]: s for s in d["stations"]}

    # 全局投影基准（与前端一致）：全网 bbox 中心为原点
    allg = [p for ln in d["lines"] for p in ln["geometry"]]
    lon0 = round((min(p[0] for p in allg) + max(p[0] for p in allg)) / 2, 4)
    lat0 = round((min(p[1] for p in allg) + max(p[1] for p in allg)) / 2, 4)
    KX = 111320 * math.cos(math.radians(lat0))
    KY = 110540

    wiki = {}
    for r in csv.DictReader(open(os.path.join(city_dir, "wiki_line_stations.csv"), encoding="utf-8-sig")):
        wiki.setdefault(r["line"], {})[r["name"]] = r

    problems = []
    out_lines = []
    n_truth = n_est = n_above = 0

    for line in d["lines"]:
        lid, lname = line["id"], line["name"]
        geom = [(p[0], p[1]) for p in line["geometry"]]
        s = [0.0]
        for a, b in zip(geom, geom[1:]):
            s.append(s[-1] + dist_m(a, b))
        L = s[-1]
        seq = []
        for nm in line["station_sequence"]:
            if nm not in seq:
                seq.append(nm)

        # 站点吸附到折线（线段投影）：位置/弧长/离折线距离一次算好
        st_pos = {}
        for nm in seq:
            st = master[nm]
            dq, bi, tq, lon_q, lat_q, s_q = project_to_polyline(
                geom, s, st["lat"], st["lon"], lon0, lat0, KX, KY)
            st_pos[nm] = (bi, s_q, dq, tq, lon_q, lat_q)
        far = {nm: round(v[2]) for nm, v in st_pos.items() if v[2] > 120}
        if far:
            problems.append(f"{lid} {lname}: 站点离折线较远 {far}")

        # 逐线敷设（维基优先，回退数据集合并值）
        wikimaps = [wiki.get(wn, {}) for wn in wiki_alias.get(lname, [lname, lname.split("（")[0]])]

        def laying_of(nm):
            for wm in wikimaps:
                if nm in wm and wm[nm].get("laying"):
                    return wm[nm]["laying"]
            return master[nm].get("laying") or "地下"

        def open_of(nm):
            for wm in wikimaps:
                if nm in wm and wm[nm].get("open_date"):
                    return wm[nm]["open_date"].strip()
            return (master[nm].get("open_date") or "").strip()

        # ---- 站值 ----
        st_val = {}     # nm -> (value, kind, meas) 或 None（待插值）
        for nm in seq:
            lay = laying_of(nm)
            if lay in ("地下", "半地下"):
                if lay == "半地下":
                    st_val[nm] = (-abs(offset["半地下"]), "est", "半地下（估算）")
                elif truth_line.get(nm) == lid:
                    dep = master[nm]["depth_m"]
                    st_val[nm] = (-float(dep), "truth", master[nm].get("depth_measure"))
                else:
                    st_val[nm] = None
            else:
                off = tram_ground_off if (lid in tram_lines and lay == "地面") else offset.get(lay, 1.2)
                st_val[nm] = (off, "above", None)

        # 估算锚点
        anchors = est_anchors.get(lid, [])
        known = set(seq)
        for nm, dep in anchors:
            if nm not in known:
                problems.append(f"{lid} {lname}: 估算锚点站名未找到 {nm}")
                continue
            if st_val[nm] is None:
                st_val[nm] = (-float(dep), "est", "埋深（估算）")
            elif st_val[nm][0] >= 0:
                problems.append(f"{lid} {lname}: 估算锚点 {nm} 落在非地下站（{laying_of(nm)}），已忽略")

        # ---- 地下段独立插值 ----
        # 只用"地下类"控制点（真值/估算锚点/半地下 + 两端缺省封口），
        # 避免被地面/高架站拖拽（如 1 号线国贸曾被四惠的 +1.2 拉成 −2m）
        pads = [(0.0, -float(line_default[lid])), (L, -float(line_default[lid]))]
        ug_pts = dedupe_pts(pads + [(st_pos[nm][1], st_val[nm][0]) for nm in seq
                                    if st_val[nm] is not None and st_val[nm][0] < 0])
        ug_at = interp_factory(ug_pts)
        for nm in seq:
            if st_val[nm] is None:
                st_val[nm] = (min(ug_at(st_pos[nm][1]), -5.0), "est", "埋深（估算）")

        # ---- 全线控制点（含地面/高架站，用于几何采样）----
        val_at = interp_factory(dedupe_pts(pads + [(st_pos[nm][1], st_val[nm][0]) for nm in seq]))

        # ---- 几何点 ----
        g3 = []
        for i, (lo, la) in enumerate(geom):
            ground = sample(la, lo)
            v = val_at(s[i])
            g3.append([round(lo, 5), round(la, 5), round(ground), round(ground + v)])

        # ---- 站点输出 ----
        st_out = []
        for nm in seq:
            st = master[nm]
            v, kind, meas = st_val[nm]
            bi, s_q, dq, tq, lon_q, lat_q = st_pos[nm]
            # 位置吸附到折线；地面/轨道高度直接取折线插值，与管线共用同一组数值
            # （避免站点级高程与折线采样的错位——垂直夸张后圆点会浮离管线）
            g0, t0 = g3[bi][2], g3[bi][3]
            g1, t1 = g3[bi + 1][2], g3[bi + 1][3]
            obj = {
                "n": nm, "en": st.get("name_en"),
                "lon": round(lon_q, 5), "lat": round(lat_q, 5),
                "g": round(g0 + (g1 - g0) * tq, 2), "lay": laying_of(nm), "open": open_of(nm),
                "lines": st["lines"], "t": round(t0 + (t1 - t0) * tq, 2),
            }
            if kind == "above":
                obj.update(dep=None, dk="above", above=abs(v))
            elif kind == "truth":
                obj.update(dep=abs(round(v, 1)), dk="truth",
                           meas=meas_cn.get(meas or "", meas or "埋深"),
                           src=st.get("depth_source") or "", conf=st.get("depth_conf") or "high")
            else:
                obj.update(dep=abs(round(v, 1)), dk="est", meas=meas or "埋深（估算）",
                           src="本项目估算（真值锚点逐线插值 / 线路缺省，仅示意）", conf="low")
            if nm in notes:
                obj["note"] = notes[nm]
            if st.get("status") and st["status"] != "operational":
                obj["status"] = st["status"]
            st_out.append(obj)
            n_truth += kind == "truth"
            n_est += kind == "est"
            n_above += kind == "above"

        out_lines.append({
            "id": lid, "name": lname,
            "colour": line.get("colour") or fallback_colour.get(lid, "#8899AA"),
            "length_km": line["length_km"], "geometry": g3, "stations": st_out,
        })

    # ---- 标注去重：同名站只在"真值实例 / 最深实例"上出标签 ----
    by_name = {}
    for rec in out_lines:
        for st in rec["stations"]:
            by_name.setdefault(st["n"], []).append(st)
    for nm, ins in by_name.items():
        truth = [x for x in ins if x["dk"] == "truth"]
        pick = truth[0] if truth else max(ins, key=lambda x: (x["dep"] or -99))
        for x in ins:
            x["lab"] = 1 if x is pick else 0

    # ---- 地形子集 ----
    allp = [p for l in out_lines for p in l["geometry"]]
    lon_min = min(p[0] for p in allp); lon_max = max(p[0] for p in allp)
    lat_min = min(p[1] for p in allp); lat_max = max(p[1] for p in allp)
    lo0 = round(math.floor((lon_min - 0.03) * 100) / 100, 2)
    lo1 = round(math.ceil((lon_max + 0.03) * 100) / 100, 2)
    la0 = round(math.floor((lat_min - 0.03) * 100) / 100, 2)
    la1 = round(math.ceil((lat_max + 0.03) * 100) / 100, 2)
    cols = round((lo1 - lo0) / 0.01) + 1
    rows = round((la1 - la0) / 0.01) + 1
    elev = []
    for r in range(rows):
        for c in range(cols):
            elev.append(grid.get((round(la0 + r * 0.01, 2), round(lo0 + c * 0.01, 2)), 0.0))
    ref_alt = min(elev)

    # lat0/lon0/KX/KY 已在 main() 开头按原始几何计算，这里直接复用（前端同基准）
    data = {
        "meta": {
            "lat0": lat0, "lon0": lon0, "ref_alt": ref_alt,
            "terrain": {"lon0": lo0, "lat0": la0, "step": 0.01,
                        "cols": cols, "rows": rows, "elev": elev},
            "palette": {l["id"]: l["colour"] for l in out_lines},
            "line_names": {l["id"]: l["name"].split("（")[0] for l in out_lines},
            "counts": {"lines": len(out_lines),
                       "stations": len(by_name),
                       "instances": sum(len(l["stations"]) for l in out_lines),
                       "truth": n_truth, "est": n_est, "above": n_above},
        },
        "lines": out_lines,
    }
    js = "window.METRO_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    out = os.path.join(build_dir, args.city + "_data.js")
    open(out, "w", encoding="utf-8").write(js)

    print(f"[{args.city}] 输出: {out}  ({len(js)/1024:.0f} KB)")
    print(f"线路 {len(out_lines)} | 站位实例 {data['meta']['counts']['instances']} | "
          f"真值 {n_truth} | 估算 {n_est} | 地面/高架 {n_above}")
    for l in out_lines:
        und = [x for x in l["stations"] if x["dk"] != "above"]
        tr = [x for x in und if x["dk"] == "truth"]
        dep = [x["dep"] for x in und if x["dep"]]
        rng = f"{min(dep):.0f}~{max(dep):.0f}m" if dep else "-"
        print(f"  {l['id']:>4} {l['name'][:10]:<11} {len(l['stations']):>2} 站 "
              f"(地下 {len(und):>2}, 真值 {len(tr)}) 埋深 {rng} | {len(l['geometry'])} 点")
    print(f"地形子集 {cols}x{rows}={len(elev)} 点, {min(elev):.0f}~{max(elev):.0f}m, ref={ref_alt}")
    if problems:
        print("问题:")
        for p in problems:
            print(" -", p)


if __name__ == "__main__":
    main()
