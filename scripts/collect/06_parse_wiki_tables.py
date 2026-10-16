# -*- coding: utf-8 -*-
"""解析维基百科《北京地铁车站列表》的 wikitable，输出结构化车站表。

输出 data/processed/wiki_line_stations.csv：
line, seq, name, name_en, district, open_date, laying, platform, transfers
"""
import csv
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根（scripts/collect 上溯三级）
SRC = os.path.join(BASE, "data", "raw", "wikipedia", "landing", "北京地铁车站列表.txt")
OUT = os.path.join(BASE, "data", "processed", "wiki_line_stations.csv")


def strip_links(s: str) -> str:
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\{\{Rail color box\|[^}]*?\|([^|}]+)\|square\}\}", r"转\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_cells(row_text: str):
    """把一个表格行切成单元格（以行首 | 或 !! 划分）。

    注意：只有 '|-'（行分隔）才算分隔符；单元格值恰为 '-' 时要保留。
    """
    lines = row_text.split("\n")
    cells, cur = [], None
    for ln in lines:
        s = ln.strip()
        if s == "|}" or s.startswith("|-"):
            cur = None
            continue
        if ln.startswith("|") or ln.startswith("!"):
            body = ln.lstrip("|!").strip()
            if cur is not None:
                cells.append(cur)
            cur = body
        else:
            if cur is not None:
                cur += "\n" + ln
    if cur is not None:
        cells.append(cur)
    return cells


def parse_rowspan(cell: str):
    """返回 (rowspan, 值)。"""
    m = re.match(r"rowspan\s*=\s*\"?(\d+)\"?\s*\|(.*)$", cell, flags=re.S)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return 1, cell


def main():
    wt = open(SRC, encoding="utf-8").read()
    # 按线路章节切分
    sections = re.split(r"\n==\s*([^=]+?)\s*==\n", wt)
    rows = []
    for i in range(1, len(sections), 2):
        line_name = sections[i].strip()
        body = sections[i + 1]
        if "{|" not in body:
            continue
        tables = re.findall(r"\{\|.*?\n\|\}", body, flags=re.S)
        for table in tables:
            trs = table.split("\n|-")
            # 只处理以「车站名」为表头的线路站表（跳过换乘站矩阵等其他表格）
            head_ok = any("车站名" in "".join(split_cells(tr.strip("\n"))[:2]) for tr in trs[:4])
            if not head_ok:
                continue
            data_rows = []
            for tr in trs:
                cells = split_cells(tr.strip("\n"))
                if not cells:
                    continue
                if "车站名" in cells[0] or "车站名" in "".join(cells[:2]):
                    continue
                data_rows.append(cells)
            # 处理 rowspan：逐行展开
            span_buf = {}  # col_index -> [remaining, value]
            seq = 0
            for cells in data_rows:
                # 先解析本行 cell 的 (span, value)
                parsed = [parse_rowspan(c) for c in cells]
                out = []
                ci = 0
                for col in range(8):  # 最多 8 列
                    if col in span_buf and span_buf[col][0] > 0:
                        out.append(span_buf[col][1])
                        span_buf[col][0] -= 1
                        continue
                    if ci < len(parsed):
                        span, val = parsed[ci]
                        ci += 1
                        out.append(val)
                        if span > 1:
                            span_buf[col] = [span - 1, val]
                    else:
                        out.append("")
                name = strip_links(out[0]) if out else ""
                if not name or not re.search(r"[\u4e00-\u9fff]", name):
                    continue
                if "colspan" in name or "style=" in name or "align=" in name:
                    continue
                # 过滤掉以"转"开头且无实际站名的残留行
                if re.match(r"^转\d+(转\d+)*$", name.strip()):
                    continue
                # 有些行 name 单元格里混入了换乘图标
                seq += 1
                rows.append({
                    "line": line_name,
                    "seq": seq,
                    "name": name.split(" ")[0],
                    "name_en": strip_links(out[1]) if len(out) > 1 else "",
                    "district": strip_links(out[2]) if len(out) > 2 else "",
                    "open_date": strip_links(out[3]) if len(out) > 3 else "",
                    "laying": strip_links(out[4]) if len(out) > 4 else "",
                    "platform": strip_links(out[5]) if len(out) > 5 else "",
                    "transfers": strip_links(out[6]) if len(out) > 6 else "",
                })

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line", "seq", "name", "name_en", "district", "open_date", "laying", "platform", "transfers"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    cnt = Counter(r["line"] for r in rows)
    print(f"总行数: {len(rows)}")
    for k, v in cnt.items():
        print(f"  {k}: {v}")
    print()
    print("== 18号线 预览 ==")
    for r in rows:
        if r["line"] == "18号线":
            print("  ", r["seq"], r["name"], "|", r["laying"], "|", r["open_date"], "|", r["transfers"])


if __name__ == "__main__":
    main()
