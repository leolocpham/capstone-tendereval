"""
pptx_generator.py
Generates the TenderEval AI PowerPoint ranking deck.

Slide structure:
  1. Title / Cover
  2. Evaluation Overview (scope, criteria summary, bidders)
  3. Proposal Compliance Results (Part 1)
  4–N. Section-by-section SWOT spider / bar (Part 2 Technical)
  N+1. Commercial SWOT Summary (Part 3)
  N+2. TCO Comparison
  N+3. Overall Ranking Matrix
  N+4. Recommendation

Brand: Navy #052B48, Orange #D05F27, Arial
"""

from __future__ import annotations

import io
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Pt, Emu

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
NAVY = RGBColor(0x05, 0x2B, 0x48)
ORANGE = RGBColor(0xD0, 0x5F, 0x27)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)
MID_GREY = RGBColor(0xBF, 0xBF, 0xBF)
BLACK = RGBColor(0x00, 0x00, 0x00)

# SWOT colours
SWOT_RGB = {
    "S": RGBColor(0x00, 0xB0, 0x50),
    "O": RGBColor(0xFF, 0xFF, 0x00),
    "N": RGBColor(0xBF, 0xBF, 0xBF),
    "T": RGBColor(0xFF, 0xC0, 0x00),
    "W": RGBColor(0xFF, 0x00, 0x00),
}

# Widescreen 16:9
SLIDE_W = Cm(33.87)
SLIDE_H = Cm(19.05)

# Bidder accent colours (up to 5 bidders)
BIDDER_COLOURS = [
    RGBColor(0x05, 0x2B, 0x48),   # Navy
    RGBColor(0xD0, 0x5F, 0x27),   # Orange
    RGBColor(0x00, 0x70, 0xC0),   # Blue
    RGBColor(0x70, 0xAD, 0x47),   # Green
    RGBColor(0x7B, 0x0F, 0x88),   # Purple
]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _rgb_hex(rgb: RGBColor) -> str:
    return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _add_textbox(slide, left, top, width, height, text, font_size=14,
                 bold=False, color=BLACK, bg_color=None, align=PP_ALIGN.LEFT,
                 wrap=True):
    from pptx.util import Pt
    txBox = slide.shapes.add_textbox(left, top, width, height)
    if bg_color:
        txBox.fill.solid()
        txBox.fill.fore_color.rgb = bg_color
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = "Arial"
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txBox


def _add_rect(slide, left, top, width, height, fill_color, line_color=None):
    from pptx.util import Pt
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height,
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(0.5)
    else:
        shape.line.fill.background()
    return shape


def _slide_header(slide, title: str, subtitle: str = ""):
    """Add standard slide header bar."""
    # Navy top bar
    bar = _add_rect(slide, Cm(0), Cm(0), SLIDE_W, Cm(1.8), NAVY)
    _add_textbox(slide, Cm(0.4), Cm(0.1), Cm(32), Cm(1.6),
                 title, font_size=18, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
    # Orange accent line
    _add_rect(slide, Cm(0), Cm(1.8), SLIDE_W, Cm(0.12), ORANGE)
    if subtitle:
        _add_textbox(slide, Cm(0.4), Cm(1.95), Cm(32), Cm(0.6),
                     subtitle, font_size=10, color=MID_GREY)


def _slide_footer(slide, eval_name: str, page_num: int, total_pages: int):
    """Add footer bar."""
    _add_rect(slide, Cm(0), Cm(18.45), SLIDE_W, Cm(0.6), NAVY)
    _add_textbox(slide, Cm(0.4), Cm(18.47), Cm(20), Cm(0.55),
                 eval_name, font_size=8, color=WHITE)
    _add_textbox(slide, Cm(30), Cm(18.47), Cm(3.5), Cm(0.55),
                 f"{page_num} / {total_pages}", font_size=8, color=WHITE, align=PP_ALIGN.RIGHT)


def _add_table(slide, left, top, width, col_widths, rows_data,
               header_fill=NAVY, header_font_color=WHITE,
               row_fills=None, font_size=9):
    """
    Add a table to the slide.
    rows_data: list of lists of strings (first row = header).
    col_widths: list of Emu/Cm values.
    row_fills: optional list of RGBColor (one per data row, excluding header).
    """
    from pptx.util import Pt
    cols = len(col_widths)
    table_rows = len(rows_data)
    height = Cm(0.55 * table_rows)

    tbl = slide.shapes.add_table(table_rows, cols, left, top, width, height).table

    for c_idx, cw in enumerate(col_widths):
        tbl.columns[c_idx].width = cw

    for r_idx, row_data in enumerate(rows_data):
        for c_idx, cell_text in enumerate(row_data):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = str(cell_text)
            tf = cell.text_frame
            tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            run = tf.paragraphs[0].runs[0] if tf.paragraphs[0].runs else tf.paragraphs[0].add_run()
            run.font.name = "Arial"
            run.font.size = Pt(font_size)

            if r_idx == 0:
                # Header
                run.font.bold = True
                run.font.color.rgb = header_font_color
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill
            else:
                run.font.color.rgb = BLACK
                if row_fills and (r_idx - 1) < len(row_fills) and row_fills[r_idx - 1]:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = row_fills[r_idx - 1]
                elif r_idx % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = LIGHT_GREY

    return tbl


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_ranking_deck(eval_data: dict[str, Any]) -> bytes:
    """
    Build the PowerPoint ranking deck and return as bytes.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # Use blank layout
    blank_layout = prs.slide_layouts[6]

    eval_name = eval_data.get("eval_name", "Evaluation")
    equipment_type = eval_data.get("equipment_type", "")
    tender_number = eval_data.get("tender_number", "")
    bidders: list[str] = eval_data.get("bidders", [])
    criteria: dict = eval_data.get("criteria", {})
    scores: dict = eval_data.get("scores", {})
    tco_results: dict = eval_data.get("tco_results", {})

    from utils.tco import (
        calculate_part1_score,
        calculate_part_score,
        calculate_section_score,
        part1_pass,
        build_scorecard,
    )

    slides = []

    # -----------------------------------------------------------------------
    # Slide 1: Cover
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _add_rect(sld, Cm(0), Cm(0), SLIDE_W, SLIDE_H, NAVY)
    _add_rect(sld, Cm(0), Cm(14), SLIDE_W, Cm(0.4), ORANGE)
    _add_textbox(sld, Cm(1.5), Cm(3), Cm(30), Cm(2.2),
                 "TenderEval AI", font_size=36, bold=True, color=WHITE)
    _add_textbox(sld, Cm(1.5), Cm(5.5), Cm(30), Cm(1.8),
                 eval_name, font_size=24, bold=True, color=ORANGE)
    _add_textbox(sld, Cm(1.5), Cm(7.5), Cm(30), Cm(1.2),
                 f"Equipment: {equipment_type}", font_size=16, color=WHITE)
    _add_textbox(sld, Cm(1.5), Cm(8.9), Cm(30), Cm(0.9),
                 f"Tender Reference: {tender_number}", font_size=13, color=MID_GREY)
    _add_textbox(sld, Cm(1.5), Cm(10.2), Cm(30), Cm(0.9),
                 f"Bidders: {', '.join(bidders)}", font_size=13, color=MID_GREY)
    _add_textbox(sld, Cm(1.5), Cm(14.6), Cm(30), Cm(0.8),
                 "Capstone Copper — Pinto Valley Operation", font_size=11, color=MID_GREY)

    # -----------------------------------------------------------------------
    # Slide 2: Evaluation Overview
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Evaluation Overview", f"{eval_name} — {equipment_type}")

    content_top = Cm(2.6)
    col1_left = Cm(0.5)
    col2_left = Cm(17.5)
    col_w = Cm(16.5)

    _add_textbox(sld, col1_left, content_top, col_w, Cm(0.6),
                 "Evaluation Structure", font_size=12, bold=True, color=NAVY)
    _add_rect(sld, col1_left, content_top + Cm(0.65), col_w, Cm(0.08), ORANGE)

    summary_text = (
        f"Part 1 — Proposal Compliance ({len(criteria.get('part1', []))} criteria, pass/fail gate)\n"
        f"Part 2 — Technical SWOT ({sum(len(s.get('sub_criteria',[])) for s in criteria.get('part2', []))} sub-criteria across "
        f"{len(criteria.get('part2', []))} sections)\n"
        f"Part 3 — Commercial SWOT ({sum(len(s.get('sub_criteria',[])) for s in criteria.get('part3', []))} sub-criteria across "
        f"{len(criteria.get('part3', []))} sections)\n"
        f"TCO — Capital + Operating costs, NPV @ 8%"
    )
    _add_textbox(sld, col1_left, content_top + Cm(0.9), col_w, Cm(4),
                 summary_text, font_size=11, color=BLACK)

    _add_textbox(sld, col2_left, content_top, col_w, Cm(0.6),
                 "Bidders Under Evaluation", font_size=12, bold=True, color=NAVY)
    _add_rect(sld, col2_left, content_top + Cm(0.65), col_w, Cm(0.08), ORANGE)

    for i, bidder in enumerate(bidders):
        b_col = BIDDER_COLOURS[i % len(BIDDER_COLOURS)]
        _add_rect(sld, col2_left, content_top + Cm(0.9 + i * 1.2),
                  Cm(0.4), Cm(0.8), b_col)
        model = scores.get(bidder, {}).get("model_identified", "")
        label = f"{bidder}  —  {model}" if model else bidder
        _add_textbox(sld, col2_left + Cm(0.6), content_top + Cm(0.9 + i * 1.2),
                     col_w - Cm(0.7), Cm(0.8),
                     label, font_size=12, bold=True, color=BLACK)

    _slide_footer(sld, eval_name, 2, len(bidders) + 9)

    # -----------------------------------------------------------------------
    # Slide 3: Part 1 — Compliance Results
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Part 1 — Proposal Compliance", "Pass / Fail Gate (threshold > 0.5)")

    p1_criteria = criteria.get("part1", [])
    headers = ["#", "Criterion"] + bidders + ["Passed?"]
    col_ws_tbl = [Cm(1.3), Cm(9.5)] + [Cm(3.8) for _ in bidders] + [Cm(2.5)]
    total_w = sum(col_ws_tbl)

    rows = [headers]
    row_fills_p1 = []
    for c in p1_criteria:
        row = [c["id"], c["name"]]
        all_pass = True
        any_fail = False
        for bidder in bidders:
            entry = scores.get(bidder, {}).get("part1_scores", {}).get(c["id"], {})
            sv = entry.get("score", 0.5)
            row.append({1: "PASS", 0.5: "PARTIAL", 0: "FAIL"}.get(sv, str(sv)))
            if sv < 1:
                all_pass = False
            if sv == 0:
                any_fail = True
        row.append("✓" if all_pass else ("✗" if any_fail else "~"))
        rows.append(row)
        row_fills_p1.append(None)

    # Summary row
    summary_row = ["", "OVERALL"]
    for bidder in bidders:
        sc = calculate_part1_score(
            scores.get(bidder, {}).get("part1_scores", {}), p1_criteria
        )
        passed = part1_pass(sc)
        summary_row.append(f"{sc:.1%} {'✓' if passed else '✗'}")
    summary_row.append("")
    rows.append(summary_row)
    row_fills_p1.append(LIGHT_GREY)

    _add_table(sld, Cm(0.3), Cm(2.4), total_w, col_ws_tbl, rows,
               row_fills=row_fills_p1, font_size=9)
    _slide_footer(sld, eval_name, 3, len(bidders) + 9)

    # -----------------------------------------------------------------------
    # Slides 4+: Part 2 — Technical SWOT per section
    # -----------------------------------------------------------------------
    slide_num = 4
    p2_sections = criteria.get("part2", [])
    for sec in p2_sections:
        sld = prs.slides.add_slide(blank_layout)
        slides.append(sld)
        _slide_header(sld,
                      f"Part 2 — Technical: §{sec['section_id']} {sec['section_name']}",
                      f"Weight: {sec.get('weight', 1.0):.1f}×  |  SWOT: S=+1, O=+0.5, N=0, T=−0.5, W=−1")

        sub_list = sec.get("sub_criteria", [])
        headers = ["#", "Sub-Criterion"] + bidders
        col_ws_tbl = [Cm(1.3), Cm(13)] + [Cm(3.3) for _ in bidders]
        total_w = sum(col_ws_tbl)

        rows = [headers]
        for sub in sub_list:
            row = [sub["id"], sub["name"]]
            for bidder in bidders:
                entry = scores.get(bidder, {}).get("part2_scores", {}).get(sub["id"], {})
                row.append(entry.get("rating", "N"))
            rows.append(row)

        # Section totals row
        tot_row = ["", f"§{sec['section_id']} WEIGHTED TOTAL"]
        for bidder in bidders:
            b_scores = scores.get(bidder, {}).get("part2_scores", {})
            raw = calculate_section_score(sec["section_id"], b_scores, p2_sections)
            weighted = raw * sec.get("weight", 1.0)
            tot_row.append(f"{weighted:+.2f}")
        rows.append(tot_row)

        # Build per-cell fills for SWOT ratings
        row_fills = [None] * (len(sub_list) + 1)

        _add_table(sld, Cm(0.3), Cm(2.4), total_w, col_ws_tbl, rows,
                   row_fills=row_fills, font_size=9)

        # Section score bar chart (simple rectangles)
        bar_top = Cm(16.5)
        _add_textbox(sld, Cm(0.5), bar_top - Cm(0.5), Cm(32), Cm(0.45),
                     "Section weighted score by bidder:", font_size=9, color=MID_GREY)
        max_abs = max(
            abs(
                calculate_section_score(sec["section_id"],
                                        scores.get(b, {}).get("part2_scores", {}),
                                        p2_sections) * sec.get("weight", 1.0)
            )
            for b in bidders
        ) or 1

        bar_width_max = Cm(6)
        for b_idx, bidder in enumerate(bidders):
            b_scores = scores.get(bidder, {}).get("part2_scores", {})
            raw = calculate_section_score(sec["section_id"], b_scores, p2_sections)
            weighted = raw * sec.get("weight", 1.0)
            bar_w = Emu(int(bar_width_max * abs(weighted) / max_abs))
            b_col = BIDDER_COLOURS[b_idx % len(BIDDER_COLOURS)]
            bar_left = Cm(0.5) + b_idx * (bar_width_max + Cm(0.4))
            bar_fill = SWOT_RGB["S"] if weighted > 0 else (SWOT_RGB["W"] if weighted < 0 else SWOT_RGB["N"])
            _add_rect(sld, bar_left, bar_top, bar_w if bar_w > Cm(0.05) else Cm(0.1), Cm(0.45), bar_fill)
            _add_textbox(sld, bar_left, bar_top + Cm(0.45), Cm(7), Cm(0.5),
                         f"{bidder}: {weighted:+.2f}", font_size=8, color=b_col)

        _slide_footer(sld, eval_name, slide_num, len(bidders) + 9)
        slide_num += 1

    # -----------------------------------------------------------------------
    # Slide N: Part 2 — Technical SWOT Summary (all sections)
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Part 2 — Technical SWOT Summary", "Weighted section scores across all bidders")

    headers = ["§", "Section", "Weight"] + bidders + ["Best"]
    col_ws_tbl = [Cm(1.2), Cm(8.5), Cm(1.8)] + [Cm(3.5) for _ in bidders] + [Cm(2.5)]
    total_w = sum(col_ws_tbl)

    rows = [headers]
    for sec in p2_sections:
        row = [f"§{sec['section_id']}", sec["section_name"], f"{sec.get('weight', 1.0):.1f}×"]
        best_score = None
        best_bidder = ""
        sec_scores = []
        for bidder in bidders:
            b_scores = scores.get(bidder, {}).get("part2_scores", {})
            raw = calculate_section_score(sec["section_id"], b_scores, p2_sections)
            w = raw * sec.get("weight", 1.0)
            row.append(f"{w:+.2f}")
            sec_scores.append(w)
            if best_score is None or w > best_score:
                best_score = w
                best_bidder = bidder
        row.append(best_bidder)
        rows.append(row)

    # Total row
    tot_row = ["", "PART 2 TOTAL", ""]
    for bidder in bidders:
        t = calculate_part_score(
            scores.get(bidder, {}).get("part2_scores", {}), p2_sections
        )
        tot_row.append(f"{t:+.2f}")
    best_t = max(bidders, key=lambda b: calculate_part_score(
        scores.get(b, {}).get("part2_scores", {}), p2_sections
    ), default="")
    tot_row.append(best_t)
    rows.append(tot_row)

    _add_table(sld, Cm(0.3), Cm(2.4), total_w, col_ws_tbl, rows, font_size=9)
    _slide_footer(sld, eval_name, slide_num, len(bidders) + 9)
    slide_num += 1

    # -----------------------------------------------------------------------
    # Slide N+1: Part 3 — Commercial SWOT Summary
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Part 3 — Commercial SWOT Summary", "Supplier Support | T&C | Warranties | Parts Supply")

    p3_sections = criteria.get("part3", [])
    headers = ["§", "Section", "Weight"] + bidders + ["Best"]
    col_ws_tbl = [Cm(1.2), Cm(8.5), Cm(1.8)] + [Cm(3.5) for _ in bidders] + [Cm(2.5)]
    total_w = sum(col_ws_tbl)

    rows = [headers]
    for sec in p3_sections:
        row = [f"§{sec['section_id']}", sec["section_name"], f"{sec.get('weight', 1.0):.1f}×"]
        best_score = None
        best_bidder = ""
        for bidder in bidders:
            b_scores = scores.get(bidder, {}).get("part3_scores", {})
            raw = calculate_section_score(sec["section_id"], b_scores, p3_sections)
            w = raw * sec.get("weight", 1.0)
            row.append(f"{w:+.2f}")
            if best_score is None or w > best_score:
                best_score = w
                best_bidder = bidder
        row.append(best_bidder)
        rows.append(row)

    tot_row = ["", "PART 3 TOTAL", ""]
    for bidder in bidders:
        t = calculate_part_score(
            scores.get(bidder, {}).get("part3_scores", {}), p3_sections
        )
        tot_row.append(f"{t:+.2f}")
    best_t = max(bidders, key=lambda b: calculate_part_score(
        scores.get(b, {}).get("part3_scores", {}), p3_sections
    ), default="")
    tot_row.append(best_t)
    rows.append(tot_row)

    _add_table(sld, Cm(0.3), Cm(2.4), total_w, col_ws_tbl, rows, font_size=9)
    _slide_footer(sld, eval_name, slide_num, len(bidders) + 9)
    slide_num += 1

    # -----------------------------------------------------------------------
    # Slide N+2: TCO Comparison
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Total Cost of Ownership Comparison", "CAPEX + OPEX over equipment life | NPV @ 8%")

    tco_metrics = [
        ("Total CAPEX (AUD)", "total_capex"),
        ("Total OPEX (AUD)", "total_opex"),
        ("Total TCO (AUD)", "total_tco"),
        ("NPV @ 8% (AUD)", "npv"),
        ("Cost per Hour (AUD/hr)", "cost_per_hour"),
    ]
    headers = ["Metric"] + bidders + ["Lowest Cost"]
    col_ws_tbl = [Cm(8)] + [Cm(4) for _ in bidders] + [Cm(3.5)]
    total_w = sum(col_ws_tbl)

    rows = [headers]
    for label, key in tco_metrics:
        row = [label]
        best_val = None
        best_b = ""
        for bidder in bidders:
            val = tco_results.get(bidder, {}).get(key, 0)
            row.append(f"${val:,.0f}" if "Hour" not in label else f"${val:,.2f}")
            if best_val is None or val < best_val:
                best_val = val
                best_b = bidder
        row.append(best_b)
        rows.append(row)

    _add_table(sld, Cm(0.3), Cm(2.8), total_w, col_ws_tbl, rows, font_size=10)

    # Simple bar chart for TCO
    bar_top = Cm(12)
    _add_textbox(sld, Cm(0.5), bar_top - Cm(0.6), Cm(32), Cm(0.5),
                 "Total TCO Comparison", font_size=11, bold=True, color=NAVY)
    max_tco = max(
        (tco_results.get(b, {}).get("total_tco", 0) for b in bidders), default=1
    ) or 1
    bar_w_max = Cm(25)
    for b_idx, bidder in enumerate(bidders):
        tco_val = tco_results.get(bidder, {}).get("total_tco", 0)
        bar_w = Emu(int(bar_w_max * tco_val / max_tco))
        b_col = BIDDER_COLOURS[b_idx % len(BIDDER_COLOURS)]
        bar_left = Cm(5)
        bar_y = bar_top + b_idx * Cm(1.1)
        _add_textbox(sld, Cm(0.3), bar_y, Cm(4.5), Cm(0.8),
                     bidder, font_size=10, bold=True, color=b_col)
        _add_rect(sld, bar_left, bar_y + Cm(0.1),
                  bar_w if bar_w > Cm(0.1) else Cm(0.1), Cm(0.65), b_col)
        _add_textbox(sld, bar_left + bar_w + Cm(0.2), bar_y, Cm(6), Cm(0.8),
                     f"${tco_val:,.0f}", font_size=10, color=b_col)

    _slide_footer(sld, eval_name, slide_num, len(bidders) + 9)
    slide_num += 1

    # -----------------------------------------------------------------------
    # Slide N+3: Overall Ranking Matrix
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Overall Ranking Matrix",
                  "Part 1 compliance | Part 2+3 qualitative SWOT | TCO")

    from utils.tco import build_scorecard

    scorecards = [
        build_scorecard(b, scores.get(b, {}), criteria, tco_results.get(b, {}))
        for b in bidders
    ]
    scorecards.sort(key=lambda x: (
        not x["part1_pass"],  # failed part 1 goes last
        -x["combined_qualitative"],
        x["tco"],
    ))

    headers = ["Rank", "Bidder", "Model", "P1 Score", "P1 Gate",
               "Tech SWOT", "Comm SWOT", "Combined", "TCO (AUD)", "$/hr"]
    col_ws_tbl = [Cm(1.2), Cm(4.5), Cm(4.5), Cm(2.2), Cm(2.0),
                  Cm(2.2), Cm(2.5), Cm(2.5), Cm(4.0), Cm(2.5)]
    total_w = sum(col_ws_tbl)

    rows = [headers]
    for rank_idx, sc in enumerate(scorecards, 1):
        bidder = sc["bidder"]
        model = scores.get(bidder, {}).get("model_identified", "")
        rows.append([
            f"#{rank_idx}",
            bidder,
            model,
            f"{sc['part1_score']:.1%}",
            "✓ PASS" if sc["part1_pass"] else "✗ FAIL",
            f"{sc['part2_score']:+.2f}",
            f"{sc['part3_score']:+.2f}",
            f"{sc['combined_qualitative']:+.2f}",
            f"${sc['tco']:,.0f}",
            f"${sc['cost_per_hour']:,.2f}",
        ])

    _add_table(sld, Cm(0.2), Cm(2.4), total_w, col_ws_tbl, rows, font_size=9)
    _slide_footer(sld, eval_name, slide_num, len(bidders) + 9)
    slide_num += 1

    # -----------------------------------------------------------------------
    # Slide N+4: Recommendation
    # -----------------------------------------------------------------------
    sld = prs.slides.add_slide(blank_layout)
    slides.append(sld)
    _slide_header(sld, "Recommendation", "Based on weighted evaluation results")

    # Determine recommendation
    passed_bidders = [sc for sc in scorecards if sc["part1_pass"]]
    if passed_bidders:
        recommended = passed_bidders[0]
        rec_text = recommended["bidder"]
        rec_model = scores.get(rec_text, {}).get("model_identified", "")
    else:
        recommended = scorecards[0] if scorecards else None
        rec_text = recommended["bidder"] if recommended else "N/A"
        rec_model = scores.get(rec_text, {}).get("model_identified", "") if recommended else ""

    # Banner
    _add_rect(sld, Cm(0.5), Cm(2.5), Cm(32.9), Cm(2.4), NAVY)
    _add_textbox(sld, Cm(1), Cm(2.6), Cm(32), Cm(1.1),
                 "Recommended Option", font_size=12, color=ORANGE, bold=True)
    _add_textbox(sld, Cm(1), Cm(3.5), Cm(32), Cm(1.2),
                 f"{rec_text}  —  {rec_model}", font_size=20, color=WHITE, bold=True)

    # Rationale bullets
    _add_textbox(sld, Cm(0.8), Cm(5.3), Cm(32), Cm(0.6),
                 "Rationale", font_size=13, bold=True, color=NAVY)
    _add_rect(sld, Cm(0.8), Cm(5.9), Cm(32), Cm(0.06), ORANGE)

    rationale_lines = []
    if recommended:
        p1_sc = recommended.get("part1_score", 0)
        p2_sc = recommended.get("part2_score", 0)
        p3_sc = recommended.get("part3_score", 0)
        tco_val = recommended.get("tco", 0)
        rationale_lines = [
            f"• Proposal Compliance: {p1_sc:.1%} — {'PASS' if recommended.get('part1_pass') else 'FAIL'}",
            f"• Technical SWOT Score: {p2_sc:+.2f}  |  Commercial SWOT Score: {p3_sc:+.2f}  |  Combined: {p2_sc+p3_sc:+.2f}",
            f"• Total Cost of Ownership: ${tco_val:,.0f}  |  Cost per Hour: ${recommended.get('cost_per_hour',0):,.2f}",
        ]
        strengths = scores.get(rec_text, {}).get("key_strengths", [])
        if strengths:
            rationale_lines.append("• Key Strengths: " + "  |  ".join(strengths[:3]))
        risks = scores.get(rec_text, {}).get("key_risks", [])
        if risks:
            rationale_lines.append("• Key Risks / TQs to resolve: " + "  |  ".join(risks[:3]))

    _add_textbox(sld, Cm(0.8), Cm(6.1), Cm(32), Cm(6),
                 "\n".join(rationale_lines), font_size=11, color=BLACK)

    # Ranking summary
    _add_textbox(sld, Cm(0.8), Cm(13.0), Cm(32), Cm(0.6),
                 "All Options — Final Ranking", font_size=11, bold=True, color=NAVY)
    for rank_idx, sc in enumerate(scorecards, 1):
        b_col = BIDDER_COLOURS[(rank_idx - 1) % len(BIDDER_COLOURS)]
        _add_rect(sld, Cm(0.8), Cm(13.6 + rank_idx * 0.8),
                  Cm(0.3), Cm(0.6), b_col)
        _add_textbox(sld, Cm(1.3), Cm(13.6 + rank_idx * 0.8), Cm(32), Cm(0.7),
                     f"#{rank_idx}  {sc['bidder']}  —  P2+P3: {sc['combined_qualitative']:+.2f}  "
                     f"|  TCO: ${sc['tco']:,.0f}  "
                     f"|  {'✓ PASS' if sc['part1_pass'] else '✗ FAIL'}",
                     font_size=10, color=BLACK)

    _slide_footer(sld, eval_name, slide_num, len(bidders) + 9)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()
