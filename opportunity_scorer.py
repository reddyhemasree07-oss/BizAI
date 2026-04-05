"""
Opportunity Scoring - Evaluates opportunity attractiveness combining
market timing, gap analysis, and growth trajectory.
"""
from utils.helpers import clamp


def score_opportunity(data: dict) -> dict:
    """
    Score the overall opportunity attractiveness.
    
    Factors:
    - Market timing (is this the right time?)
    - Gap size (how underserved is the market?)
    - Growth trajectory (is the market growing?)
    - Barrier to entry (how hard is it for others to copy?)
    - Revenue clarity (how clear is the monetization path?)
    
    Returns dict with per-factor scores and composite.
    """
    scores = {}
    
    # Market timing
    trend = data.get("market_trend", "stable").lower()
    trend_map = {"declining": 2, "stable": 4, "growing": 7, "exploding": 9}
    scores["market_timing"] = trend_map.get(trend, 5)
    
    # Gap size (demand vs supply)
    competitors = data.get("competitor_count", 5)
    demand_signal = data.get("search_volume_signal", "medium").lower()
    demand_map = {"low": 2, "medium": 5, "high": 7, "very high": 9}
    gap_demand = demand_map.get(demand_signal, 5)
    
    if competitors <= 3:
        gap_supply = 8
    elif competitors <= 10:
        gap_supply = 5
    else:
        gap_supply = 2
    scores["gap_size"] = round((gap_demand + gap_supply) / 2, 1)
    
    # Growth trajectory
    cagr = data.get("market_cagr_percent", 5)
    if cagr > 20:
        scores["growth_trajectory"] = 9
    elif cagr > 10:
        scores["growth_trajectory"] = 7
    elif cagr > 5:
        scores["growth_trajectory"] = 5
    else:
        scores["growth_trajectory"] = 3
    
    # Barrier to entry
    barriers = data.get("barrier_to_entry", "medium").lower()
    barrier_map = {"low": 3, "medium": 5, "high": 7, "very high": 9}
    scores["barrier_to_entry"] = barrier_map.get(barriers, 5)
    
    # Revenue clarity
    has_model = data.get("revenue_model_clear", True)
    scores["revenue_clarity"] = 8 if has_model else 3
    
    # Composite (equal weights for opportunity)
    weights = {
        "market_timing": 0.25,
        "gap_size": 0.25,
        "growth_trajectory": 0.20,
        "barrier_to_entry": 0.15,
        "revenue_clarity": 0.15,
    }
    
    composite = sum(
        clamp(scores.get(k, 5)) * w
        for k, w in weights.items()
    )
    scores["composite"] = round(composite, 2)
    
    # Rating label
    if composite >= 7:
        scores["rating"] = "Strong Opportunity"
    elif composite >= 5:
        scores["rating"] = "Moderate Opportunity"
    else:
        scores["rating"] = "Weak Opportunity"
    
    return scores
