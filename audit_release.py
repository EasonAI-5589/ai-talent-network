"""Pre-release audit: the page and the Excel export must agree and describe every record as retrieved data.

Checks the built index.html and downloads/*.xlsx against build_page.prepare_page(showcase=True).
Usage: uvx --with openpyxl python audit_release.py   (exit code 1 on any problem)
"""
import json, math, re, sys

from openpyxl import load_workbook

import build_page
import export_excel

POINTS = {1: 100, 2: 85, 3: 60, 4: 35}
REQUIRED = ("序号", "姓名", "现任学校 / 机构", "职称", "院系", "地区", "检索途径", "检索学校", "署名机构（当前关联）", "交叉论文", "AI 论文",
            "h 指数", "AI 背景（满足条件）", "分层", "分层依据", "AI × 金融相关性", "综合分", "现职核验", "现职来源", "核验日期", "OpenAlex 档案", "网站档案卡")
problems = []


def check(ok, msg):
    if not ok:
        problems.append(msg)


def manual_words(text):
    """'人工' outside 人工智能 (artificial intelligence), or 补录 (manual entry)."""
    return len(re.findall(r"人工(?!智能)", text)) + text.count("补录")


def main():
    html_built, merged = build_page.prepare_page(showcase=True)
    people = {p["id"]: p for p in merged["people"]}
    html = open(build_page.OUTPUT_PATH, encoding="utf-8").read()
    check(html == html_built, "index.html is stale: run python3 build_page.py")
    check(manual_words(html) == 0, f"index.html still says 人工/补录 {manual_words(html)} times")

    for p in people.values():
        s, who = p["search"], f"{p['id']} {p['name']}"
        check((p.get("current_role") or {}).get("evidence_status") == "official_verified", f"{who}: appointment not officially verified")
        check(s["route"] in ("学校检索", "作者检索"), f"{who}: route {s['route']}")
        check(s["cross"] >= 2 and s["h"] >= 6 and s["shares"]["off"] < 0.4 and s["shares"]["econ"] >= 0.15, f"{who}: a screening threshold fails")
        check(s["home"] != "计算机/AI" or s["cross"] >= 3, f"{who}: computer-science background with < 3 cross papers")
        check(bool(s["ai_gate"]) and bool(s.get("matched_institutions")), f"{who}: AI background or affiliation evidence missing")
        # components are stored to 4 decimals, so allow the half point lost to rounding
        check(abs(100 * (0.55 * s["cross_score"] + 0.25 * s["fin_score"] + 0.20 * s["ai_score"]) - p["fit"]) <= 0.5 + 1e-6, f"{who}: relevance does not add up")
        check(abs(s["cross_score"] - (1 - math.exp(-s["E"] / 5))) < 1e-3, f"{who}: cross-paper score does not match E")
        check(round(0.6 * p["fit"] + 0.4 * POINTS[p["tier"]]) == p["score"], f"{who}: composite score does not add up")
        check(len(s["papers"]) == s["cross"], f"{who}: {len(s['papers'])} papers listed for {s['cross']} cross papers")
        check(sum(a for _, a, _ in s["papers"]) == s["ai_papers"], f"{who}: AI paper count differs from the list")
        role = p.get("display_role") or p["current_role"]
        check(bool(role.get("source_url")) and bool(role.get("checked_at")), f"{who}: appointment source or date missing")

    wb = load_workbook(export_excel.OUTPUT)
    text = " ".join(str(c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value is not None)
    check(manual_words(text) == 0, f"Excel still says 人工/补录 {manual_words(text)} times")
    ws = wb[f"学者（{len(people)}）"] if f"学者（{len(people)}）" in wb.sheetnames else None
    check(ws is not None, f"Excel has no sheet 学者（{len(people)}）")
    if ws is not None:
        head = [c.value for c in ws[1]]
        col = {h: i for i, h in enumerate(head)}
        seen = set()
        for row in ws.iter_rows(min_row=2, values_only=True):
            pid = row[col["OpenAlex 档案"]].rsplit("/", 1)[-1]
            seen.add(pid)
            p = people.get(pid)
            if p is None:
                problems.append(f"Excel row for {pid} is not on the site"); continue
            s, role = p["search"], p.get("display_role") or p["current_role"]
            expect = {"姓名": p["name"], "现任学校 / 机构": role.get("institution"), "职称": role.get("position"), "院系": role.get("department") or "未记载",
                      "交叉论文": s["cross"], "AI 论文": s["ai_papers"], "Q1 论文": s["q1_papers"], "Q2 论文": s["q2_papers"], "h 指数": p["h"],
                      "AI × 金融相关性": p["fit"], "综合分": p["score"], "分层分": POINTS[p["tier"]], "分层依据": s["tier_why"],
                      "现职来源": role.get("source_url"), "核验日期": role.get("checked_at"), "Shortlist": "是" if p.get("shortlist") else None}
            for k, v in expect.items():
                check(row[col[k]] == v, f"Excel {p['name']} {k}: {row[col[k]]!r} != site {v!r}")
            for k in REQUIRED:
                check(row[col[k]] not in (None, ""), f"Excel {p['name']}: {k} is blank")
        check(seen == set(people), f"Excel rows {len(seen)} vs site {len(people)}")
    papers = wb["参考论文"]
    n = papers.max_row - 1
    check(n == sum(len(p["search"]["papers"]) for p in people.values()), f"参考论文 has {n} rows")
    for row in papers.iter_rows(min_row=2, values_only=True):
        check(str(row[-1]).startswith(("https://", "http://")), f"参考论文 row {row[0]}: link {row[-1]!r}")

    print(json.dumps({"people": len(people), "papers": n, "problems": len(problems)}, ensure_ascii=False))
    for msg in problems[:40]:
        print(" -", msg)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
