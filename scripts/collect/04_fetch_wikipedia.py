# -*- coding: utf-8 -*-
"""抓取中文维基百科北京地铁车站条目的原始 wikitext（v2：generator 批量模式）。

结构：
  Category:北京地铁车站
    ├─ Category:北京地铁换乘车站            （条目直接挂在这里）
    ├─ Category:北京地铁车站 (按线路)       （容器，下挂各线路车站分类）
    └─ Category:北京地铁车站 (按行政区划)   （容器，下挂各区车站分类）

对每个叶子分类用 action=query&generator=categorymembers 一次取 50 条正文，
大幅减少请求数；429 时按 Retry-After 退避。可重复运行（已有文件跳过）。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
OUT_DIR = os.path.join(BASE, "data", "raw", "wikipedia")
PAGES_DIR = os.path.join(OUT_DIR, "pages")
os.makedirs(PAGES_DIR, exist_ok=True)

UA = "BeijingMetroMap/0.1 (personal research; data collection)"
# 大陆网络访问维基百科需本机代理；海外网络可置 METRO3D_PROXY= 直连
PROXY = os.environ.get("METRO3D_PROXY")
if PROXY is None:
    PROXY = "http://127.0.0.1:7897"
API = "https://zh.wikipedia.org/w/api.php"
MAIN_CAT = "Category:北京地铁车站"
CONTAINER_CATS = [
    "Category:北京地铁车站 (按线路)",
    "Category:北京地铁车站 (按行政区划)",
]
LANDING_TITLES = ["北京地铁", "北京地铁车站列表", "北京地铁线路列表"]

THROTTLE = 1.2
_last = [0.0]


def api(params: dict, retries: int = 6, post: bool = True):
    params = {**params, "format": "json", "formatversion": "2"}
    data = urllib.parse.urlencode(params).encode()
    last = None
    for attempt in range(retries):
        wait = THROTTLE - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(API, data=data, headers={"User-Agent": UA})
            opener = (urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
            ) if PROXY else urllib.request.build_opener())
            with opener.open(req, timeout=90) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                ra = exc.headers.get("Retry-After")
                s = min(float(ra), 90) if ra else min(20 * (attempt + 1), 90)
                print(f"    [429] 等待 {s:.0f}s…")
                time.sleep(s)
            else:
                time.sleep(5)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(5)
    raise RuntimeError(f"api failed: {last}")


def save_page(title, pageid, revid, content):
    path = os.path.join(PAGES_DIR, f"{pageid}.json")
    if not os.path.exists(path):
        json.dump(
            {"title": title, "pageid": pageid, "revid": revid, "wikitext": content},
            open(path, "w", encoding="utf-8"),
            ensure_ascii=False,
        )


def fetch_category_pages(cat: str, cat_of: dict):
    """用 generator 取一个分类下全部条目的正文。返回条目数。"""
    total = 0
    cont = {}
    while True:
        params = {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": cat,
            "gcmtype": "page",
            "gcmlimit": "50",
            "prop": "revisions",
            "rvprop": "ids|content",
            "rvslots": "main",
            "redirects": "1",
            **cont,
        }
        d = api(params)
        pages = d.get("query", {}).get("pages", [])
        got = 0
        for p in pages:
            if p.get("missing"):
                continue
            rev = (p.get("revisions") or [{}])[0]
            content = (rev.get("slots") or {}).get("main", {}).get("content", "")
            if not content:
                continue
            save_page(p["title"], p["pageid"], rev.get("revid"), content)
            cat_of.setdefault(p["title"], set()).add(cat)
            got += 1
        total += got
        cont = d.get("continue", {})
        if not cont:
            break
        time.sleep(0.3)
    return total


def main():
    cat_of = {}
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        m = json.load(open(manifest_path, encoding="utf-8"))
        cat_of = {k: set(v) for k, v in m.get("title_categories", {}).items()}

    # 0) 落地页（总表类条目）
    print("== 落地页 ==")
    d = api({"action": "query", "prop": "revisions", "rvprop": "ids|content", "rvslots": "main",
             "titles": "|".join(LANDING_TITLES), "redirects": "1"})
    landing_dir = os.path.join(OUT_DIR, "landing")
    os.makedirs(landing_dir, exist_ok=True)
    for p in d.get("query", {}).get("pages", []):
        if p.get("missing"):
            print("   missing:", p["title"])
            continue
        c = (p["revisions"][0].get("slots") or {}).get("main", {}).get("content", "")
        fn = os.path.join(landing_dir, p["title"].replace("/", "_") + ".txt")
        open(fn, "w", encoding="utf-8").write(c)
        print(f"   {p['title']}: {len(c)} chars")

    # 1) 直接挂在主分类下的条目（换乘车站等）
    print("== 主分类直接条目 ==")
    n = fetch_category_pages(MAIN_CAT, cat_of)
    print(f"   {MAIN_CAT}: {n}")

    # 2) 容器分类及其子分类
    leaf_cats = []
    for cc in CONTAINER_CATS:
        subs = api({"action": "query", "list": "categorymembers", "cmtitle": cc,
                    "cmtype": "subcat", "cmlimit": "200"})["query"]["categorymembers"]
        subs = [s["title"] for s in subs]
        print(f"== {cc}: {len(subs)} 个子分类 ==")
        leaf_cats.extend(subs)
    # 容器分类自身也可能直接挂条目
    for cc in CONTAINER_CATS:
        n = fetch_category_pages(cc, cat_of)
        if n:
            print(f"   {cc} 直接条目: {n}")

    print(f"== 叶子分类抓取（{len(leaf_cats)} 个）==")
    for i, cat in enumerate(leaf_cats):
        n = fetch_category_pages(cat, cat_of)
        print(f"   [{i + 1}/{len(leaf_cats)}] {cat}: {n}")

    # 3) manifest
    title_categories = {k: sorted(v) for k, v in cat_of.items()}
    files = os.listdir(PAGES_DIR)
    manifest = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "zh.wikipedia.org",
        "fetch_method": "generator=categorymembers + rvprop=content",
        "pages_on_disk": len(files),
        "container_categories": CONTAINER_CATS,
        "leaf_categories": leaf_cats,
        "title_categories": title_categories,
    }
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n完成：磁盘上共 {len(files)} 个条目文件，manifest 已更新")
    print(f"条目名总数（含分类映射）：{len(title_categories)}")


if __name__ == "__main__":
    main()
