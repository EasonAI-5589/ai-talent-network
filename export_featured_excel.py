"""Export the 150 Featured Scholars (5 directions x 30 scholars) to an Excel workbook.

Includes:
- 150人精选总表 (all 150 scholars)
- 5 direction-specific sheets (30 scholars each: 宏观金融, 资产定价, 公司金融, 市场微观结构, 金融科技 FinTech&AI)
- 评选与加权说明 (Academic Leader qualification & Collaboration Fit weighting methodology)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
PUBLIC_REPO = Path("/Users/user/Documents/AI-Talent-Network/github-pages")
FEATURED_PATH = ROOT / "data" / "featured_150.json"
ROLES_PATH = ROOT / "data" / "current_roles_verified.json"
OUTPUT_PATH = ROOT / "downloads" / "pbcsf-150-featured-scholars.xlsx"
SITE = "https://easonai-5589.github.io/ai-talent-network/"

HEAD_FONT = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="264873")
LINK_FONT = Font(color="264873", underline="single")
WRAP_ALIGN = Alignment(wrap_text=True, vertical="top")

COLUMNS = [
    ("方向序号", 8, "int"),
    ("一级方向", 10, "text"),
    ("细分方向", 22, "text"),
    ("子方向标签", 12, "text"),
    ("姓名", 22, "text"),
    ("中文名", 10, "text"),
    ("现任学校 / 机构", 20, "text"),
    ("职称", 18, "text"),
    ("学院 / 院系", 24, "text"),
    ("地区", 7, "text"),
    ("是否学科带头人", 18, "text"),
    ("总发表数（>10底线）", 12, "int"),
    ("金融Top3（JF/JFE/RFS）", 12, "int"),
    ("经济Top5（AER/QJE等）", 12, "int"),
    ("核心顶刊合计", 11, "int"),
    ("延伸顶刊（MS/JFQA等）", 12, "int"),
    ("顶刊总计", 9, "int"),
    ("顶刊发表构成", 28, "text"),
    ("学术带头人认定依据", 42, "text"),
    ("合作契合度（0-100）", 12, "int"),
    ("合作契合分档", 12, "text"),
    ("综合推荐指数", 11, "num1"),
    ("加权一：华语学术背景（30分）", 32, "text"),
    ("加权二：中国问题研究（25分）", 42, "text"),
    ("加权三：对华交流与高校纽带（25分）", 38, "text"),
    ("加权四：资历与大牛豁免（20分）", 36, "text"),
    ("入选与权重综合说明", 64, "text"),
    ("代表性顶刊 / 交叉论文", 56, "text"),
    ("h 指数", 8, "int"),
    ("总被引", 10, "int"),
    ("AI×金融相关性", 10, "int"),
    ("现职核验来源", 36, "url"),
    ("网站档案卡", 14, "url"),
]

SHEET_TITLES = {
    "macro_finance": "宏观金融（30）",
    "asset_pricing": "资产定价（30）",
    "corporate_finance": "公司金融（30）",
    "market_microstructure": "市场微观结构（30）",
    "fintech": "金融科技-FinTech（30）",
    "ai_finance": "金融科技-AI（30）",
}


def write_table(ws, columns, rows):
    ws.append([c[0] for c in columns])
    for cell in ws[1]:
        cell.font = HEAD_FONT
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row in rows:
        ws.append([v[0] if isinstance(v, tuple) else v for v in row])
        r = ws.max_row
        for i, ((_, _, kind), v) in enumerate(zip(columns, row), start=1):
            cell = ws.cell(r, i)
            cell.alignment = WRAP_ALIGN
            if kind == "num1" and cell.value is not None:
                cell.number_format = "0.0"
            elif kind == "url" and v:
                url = v[1] if isinstance(v, tuple) else v
                if url:
                    cell.hyperlink = url
                    cell.font = LINK_FONT
    for i, (_, width, _) in enumerate(columns, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "F2"
    ws.auto_filter.ref = ws.dimensions


def build_row(item, roles):
    aid = item["id"]
    role = roles.get(aid) or {}
    w = item["weights"]
    source_url = item.get("source_url") or role.get("source_url") or ""
    return [
        item["direction_rank"],
        item["direction_group"],
        item["direction_label"],
        item["sub_direction"],
        item["name"],
        item.get("name_zh") or "",
        item["institution"],
        item["position"],
        item["department"] or "未记载",
        item["region"],
        f"是 · {item['leader_level']}",
        item["works"],
        item["fin3_count"],
        item["econ5_count"],
        item["core_top_count"],
        item["ext_top_count"],
        item["total_top_count"],
        item["journal_summary"],
        item["leader_why"],
        item["collab_score"],
        item["collab_tier"],
        item["overall_priority"],
        f"{w['heritage']['score']}/30：{w['heritage']['reason']}",
        f"{w['china_research']['score']}/25：{w['china_research']['reason']}",
        f"{w['china_ties']['score']}/25：{w['china_ties']['reason']}",
        f"{w['career_stage']['score']}/20：{w['career_stage']['reason']}",
        item["selection_summary"],
        "；".join(item.get("rep_top_papers") or []),
        item.get("h"),
        item.get("cites"),
        item.get("fit"),
        source_url,
        ("打开档案卡", f"{SITE}#p-{aid}"),
    ]


def write_guide_sheet(ws, featured):
    total_n = featured.get("total", 180)
    kb_total = featured.get("kb_total", 4669)
    rows = [
        (f"PBCSF {total_n} 人精选学者名单（6 大子方向 × 30 人 · 学科带头人 × 合作契合度）", ""),
        ("生成日期", featured.get("generated_at", "2026-10-27")),
        ("总知识库规模", f"合并五道口《师资库2026.xlsx》（7 大地区 84 所高校 4,142 条）与 AI×金融库（652 位），去重后共 {kb_total:,} 位学者"),
        ("总人数与方向结构", f"共 {total_n} 位不重复学科带头人，按 6 个子方向各选拔 30 人：宏观金融（30）、资产定价（30）、公司金融（30）、市场微观结构（30）、金融科技·FinTech（30）、金融科技·AI（30）"),
        ("", ""),
        ("一、学科带头人认定标准（学术底线）", ""),
        ("总发表量门槛", "总发表论文数 > 10 篇（double-digit publications）"),
        ("核心顶刊带头人（一线标准）", "总发表 > 10 篇，且金融 Top 3（JF、JFE、RFS）与经济 Top 5（AER、ECTA、QJE、JPE、REStud）核心顶刊发表 ≥ 6 篇"),
        ("延伸顶刊带头人（延伸标准）", "总发表 > 10 篇，且计入 Management Science（MS）、JFQA、Operations Research（OR）、REStat、JME、JoE、Review of Finance（RF）等延伸顶刊后合计 ≥ 5 篇"),
        ("高影响力带头人（交叉/AI标准）", "总发表 > 10 篇，且达到 L1/L2 顶级奖项或高影响力标准（经济金融 h≥45 / 被引≥1.5 万，计算机与交叉 h≥60 / 被引≥2.5 万）"),
        ("", ""),
        ("二、合作契合度加权体系（0–100 分，非等权加权）", ""),
        ("加权一：华语学术背景（0–30 分）", "华人学者、具中文姓名或华语高校学位背景赋 30 分；全职任教于亚太高校赋 20 分；其余国际学者赋 10 分"),
        ("加权二：中国问题研究（0–25 分）", "发表 2 篇及以上中国金融/经济问题论文赋 25 分；研究领域明确聚焦中国经济与金融市场赋 22 分；发表 1 篇中国主题论文赋 20 分；方法可迁移应用赋 8 分"),
        ("加权三：对华交流与高校纽带（0–25 分）", "在海外名校与国内高校均有双聘/兼职记录或现任职于国内顶尖高校赋 25 分、香港高校赋 23 分、新加坡高校赋 21 分；海外学者与国内高校有合作署名研究赋 18–22 分；其余赋 12 分"),
        ("加权四：资历阶段与大牛豁免（0–20 分）", "诺奖/图灵奖/克拉克奖或核心顶刊 ≥ 8 篇、顶刊总计 ≥ 12 篇、h ≥ 50 的顶尖大牛学者适用“年龄不设限”规则赋满分 20 分；2008 年及以后获博士学位的中青年正教授/副教授赋 18–19 分；其余资深教授赋 16 分"),
        ("综合推荐指数", "0.55 × 合作契合度 + 0.45 × 学术带头人实力分（基于核心顶刊、延伸顶刊与综合分折算），兼顾学术底线与合作落地潜力"),
        ("", ""),
        ("线上看板地址", SITE),
    ]
    for k, v in rows:
        ws.append([k, v])
        if k and not v:
            ws.cell(ws.max_row, 1).font = Font(bold=True, size=12, color="264873")
    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 115
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = WRAP_ALIGN
    ws.cell(ws.max_row, 2).hyperlink = SITE
    ws.cell(ws.max_row, 2).font = LINK_FONT


def export_featured(output: Path = OUTPUT_PATH):
    featured = json.loads(FEATURED_PATH.read_text(encoding="utf-8"))
    roles = json.loads(ROLES_PATH.read_text(encoding="utf-8")) if ROLES_PATH.exists() else {}
    scholars = featured["scholars"]
    order = featured["order"]
    all_items = [scholars[aid] for aid in order if aid in scholars]

    wb = Workbook()
    ws_all = wb.active
    ws_all.title = f"{len(all_items)}人精选总表"
    write_table(ws_all, COLUMNS, [build_row(item, roles) for item in all_items])

    for d in featured["directions"]:
        dkey = d["key"]
        d_items = [item for item in all_items if item["direction"] == dkey]
        ws_d = wb.create_sheet(SHEET_TITLES.get(dkey, d["label"]))
        write_table(ws_d, COLUMNS, [build_row(item, roles) for item in d_items])

    ws_guide = wb.create_sheet("评选与加权说明")
    write_guide_sheet(ws_guide, featured)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    alt_out = output.parent / "pbcsf-180-featured-scholars.xlsx"
    if alt_out != output:
        wb.save(alt_out)

    if PUBLIC_REPO.exists():
        for fn in (output.name, "pbcsf-180-featured-scholars.xlsx"):
            pub_out = PUBLIC_REPO / "downloads" / fn
            pub_out.parent.mkdir(parents=True, exist_ok=True)
            wb.save(pub_out)

    return {"scholars": len(all_items), "sheets": wb.sheetnames, "output": str(output)}


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH
    print(json.dumps(export_featured(out), ensure_ascii=False))
