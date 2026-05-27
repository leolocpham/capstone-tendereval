"""
tco.py
Scoring calculations and Total Cost of Ownership analysis for TenderEval AI.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# SWOT → numeric mapping
# ---------------------------------------------------------------------------

SWOT_VALUES: dict[str, float] = {
    "S": 1.0,
    "O": 0.5,
    "N": 0.0,
    "T": -0.5,
    "W": -1.0,
}


def swot_to_numeric(rating: str) -> float:
    """Convert a SWOT rating string to its numeric value. Returns 0.0 for unknown."""
    return SWOT_VALUES.get(str(rating).strip().upper(), 0.0)


# ---------------------------------------------------------------------------
# Part 1 — Compliance Gate
# ---------------------------------------------------------------------------

def calculate_part1_score(
    scores: dict[str, dict],
    criteria: list[dict],
) -> float:
    """
    Weighted average of Part 1 compliance scores.

    Args:
        scores:   {criterion_id: {"score": float, ...}}
        criteria: list of Part 1 criterion dicts with "id" and "weight" keys.

    Returns:
        Weighted average score in [0, 1]. Returns 0.0 if no criteria.
    """
    total_weight = sum(c.get("weight", 1.0) for c in criteria)
    if total_weight == 0:
        return 0.0

    weighted_sum = 0.0
    for c in criteria:
        cid = c["id"]
        score_entry = scores.get(cid, {})
        score = float(score_entry.get("score", 0))
        weighted_sum += score * c.get("weight", 1.0)

    return weighted_sum / total_weight


def part1_pass(score: float, threshold: float = 0.5) -> bool:
    """Return True if Part 1 weighted score exceeds the pass threshold."""
    return score > threshold


# ---------------------------------------------------------------------------
# Part 2 / Part 3 — SWOT section and part scoring
# ---------------------------------------------------------------------------

def calculate_section_score(
    section_id: int,
    scores: dict[str, dict],
    sections: list[dict],
) -> float:
    """
    Calculate the raw SWOT score for a single section.

    Args:
        section_id: The integer section ID to score.
        scores:     {criterion_id: {"rating": str, ...}}
        sections:   list of section dicts (part2 or part3 structure).

    Returns:
        Sum of numeric SWOT values for all sub-criteria in the section.
        Returns 0.0 if section not found.
    """
    for sec in sections:
        if sec.get("section_id") == section_id:
            total = 0.0
            for sub in sec.get("sub_criteria", []):
                entry = scores.get(sub["id"], {})
                total += swot_to_numeric(entry.get("rating", "N"))
            return total
    return 0.0


def calculate_section_weighted(
    section_id: int,
    scores: dict[str, dict],
    sections: list[dict],
) -> float:
    """
    Calculate the SWOT score for a section, weighted by the section weight.

    Returns:
        section_raw_score * section_weight
    """
    for sec in sections:
        if sec.get("section_id") == section_id:
            raw = calculate_section_score(section_id, scores, sections)
            weight = sec.get("weight", 1.0)
            return raw * weight
    return 0.0


def calculate_part_score(
    scores: dict[str, dict],
    sections: list[dict],
) -> float:
    """
    Calculate the total weighted SWOT score across all sections in a part.

    Returns:
        Sum of (section_raw_score × section_weight) for all sections.
        A negative value means more risks/weaknesses than strengths.
    """
    total = 0.0
    for sec in sections:
        section_id = sec.get("section_id")
        raw = calculate_section_score(section_id, scores, sections)
        total += raw * sec.get("weight", 1.0)
    return total


def calculate_part_normalised(
    scores: dict[str, dict],
    sections: list[dict],
) -> float:
    """
    Return the part score normalised to [−1, +1] per weighted sub-criterion.
    Useful for cross-part comparison.
    """
    total_sub = sum(
        len(sec.get("sub_criteria", [])) * sec.get("weight", 1.0)
        for sec in sections
    )
    if total_sub == 0:
        return 0.0
    return calculate_part_score(scores, sections) / total_sub


# ---------------------------------------------------------------------------
# Per-section summary for display
# ---------------------------------------------------------------------------

def section_summary(
    section_id: int,
    scores: dict[str, dict],
    sections: list[dict],
) -> dict[str, Any]:
    """
    Return a summary dict for a section:
    {
        "section_id": int,
        "section_name": str,
        "weight": float,
        "raw_score": float,
        "weighted_score": float,
        "sub_count": int,
        "ratings": {"S": n, "O": n, "N": n, "T": n, "W": n}
    }
    """
    for sec in sections:
        if sec.get("section_id") == section_id:
            ratings = {"S": 0, "O": 0, "N": 0, "T": 0, "W": 0}
            for sub in sec.get("sub_criteria", []):
                r = scores.get(sub["id"], {}).get("rating", "N").upper()
                if r in ratings:
                    ratings[r] += 1

            raw = calculate_section_score(section_id, scores, sections)
            weight = sec.get("weight", 1.0)
            return {
                "section_id": section_id,
                "section_name": sec.get("section_name", ""),
                "weight": weight,
                "raw_score": raw,
                "weighted_score": raw * weight,
                "sub_count": len(sec.get("sub_criteria", [])),
                "ratings": ratings,
            }
    return {}


# ---------------------------------------------------------------------------
# TCO calculations
# ---------------------------------------------------------------------------

def npv(rate: float, cashflows: list[float]) -> float:
    """
    Calculate Net Present Value.

    Args:
        rate:       Discount rate per period (e.g. 0.08 for 8%).
        cashflows:  List of cash outflows/inflows per period (Year 0, 1, 2, …).
                    Year 0 is typically the CAPEX lump sum (positive = cost).

    Returns:
        NPV as a positive cost figure (sum of discounted cashflows).
    """
    total = 0.0
    for t, cf in enumerate(cashflows):
        total += cf / ((1 + rate) ** t)
    return total


def calculate_tco(
    tco_inputs: dict[str, Any],
    discount_rate: float = 0.08,
) -> dict[str, float]:
    """
    Calculate TCO summary from tco_inputs dict.

    tco_inputs structure:
    {
        "rtw_cost":          float,   # Ready-to-work capital cost
        "change_mgmt_capex": float,   # Change management capital
        "training":          float,   # Training cost
        "seed_components":   float,   # Initial seed component stock
        "total_life_hours":  float,   # Total expected operating hours
        "opex_years": [
            {"operating": float, "maintenance": float, "indirect": float},
            ...  # one dict per year
        ]
    }

    Returns:
    {
        "total_capex":     float,
        "total_opex":      float,
        "total_tco":       float,
        "npv":             float,
        "cost_per_hour":   float,
    }
    """
    # CAPEX
    total_capex = (
        float(tco_inputs.get("rtw_cost", 0))
        + float(tco_inputs.get("change_mgmt_capex", 0))
        + float(tco_inputs.get("training", 0))
        + float(tco_inputs.get("seed_components", 0))
    )

    # OPEX — sum across all years
    opex_years: list[dict] = tco_inputs.get("opex_years", [])
    annual_opex: list[float] = []
    for yr in opex_years:
        yr_total = (
            float(yr.get("operating", 0))
            + float(yr.get("maintenance", 0))
            + float(yr.get("indirect", 0))
        )
        annual_opex.append(yr_total)
    total_opex = sum(annual_opex)

    total_tco = total_capex + total_opex

    # NPV: Year 0 = CAPEX, subsequent years = annual OPEX
    cashflows = [total_capex] + annual_opex
    npv_value = npv(discount_rate, cashflows)

    # Cost per operating hour
    total_life_hours = float(tco_inputs.get("total_life_hours", 0))
    cost_per_hour = total_tco / total_life_hours if total_life_hours > 0 else 0.0

    return {
        "total_capex": total_capex,
        "total_opex": total_opex,
        "total_tco": total_tco,
        "npv": npv_value,
        "cost_per_hour": cost_per_hour,
    }


# ---------------------------------------------------------------------------
# Overall bidder ranking helpers
# ---------------------------------------------------------------------------

def build_scorecard(bidder_name: str, scores: dict, criteria: dict, tco_results: dict) -> dict:
    """
    Build a flat scorecard dict for a bidder for ranking purposes.

    Returns:
    {
        "bidder": str,
        "part1_score": float,       # weighted average [0,1]
        "part1_pass": bool,
        "part2_score": float,       # weighted SWOT sum
        "part3_score": float,       # weighted SWOT sum
        "combined_qualitative": float,  # part2 + part3
        "tco": float,               # total TCO
        "npv": float,
        "cost_per_hour": float,
    }
    """
    p1_score = calculate_part1_score(
        scores.get("part1_scores", {}), criteria.get("part1", [])
    )
    p2_score = calculate_part_score(
        scores.get("part2_scores", {}), criteria.get("part2", [])
    )
    p3_score = calculate_part_score(
        scores.get("part3_scores", {}), criteria.get("part3", [])
    )

    tco = tco_results.get("total_tco", 0)
    npv_val = tco_results.get("npv", 0)
    cph = tco_results.get("cost_per_hour", 0)

    return {
        "bidder": bidder_name,
        "part1_score": p1_score,
        "part1_pass": part1_pass(p1_score),
        "part2_score": p2_score,
        "part3_score": p3_score,
        "combined_qualitative": p2_score + p3_score,
        "tco": tco,
        "npv": npv_val,
        "cost_per_hour": cph,
    }
