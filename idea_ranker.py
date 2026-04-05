"""
Idea Ranking Algorithm - Deterministic scoring for business ideas.
Does NOT rely purely on LLM text; uses weighted multi-factor formulas.
"""
from utils.helpers import clamp


# Weights for composite scoring (must sum to 1.0)
WEIGHTS = {
    "feasibility": 0.25,
    "market_size": 0.20,
    "competition_gap": 0.20,
    "time_to_revenue": 0.15,
    "scalability": 0.10,
    "founder_fit": 0.10,
}


def compute_composite_score(scores: dict) -> float:
    """
    Compute weighted composite score from individual factor scores.
    
    Args:
        scores: Dict with keys matching WEIGHTS, values 1-10
    
    Returns:
        Composite score 0-10
    """
    total = 0.0
    for factor, weight in WEIGHTS.items():
        val = clamp(float(scores.get(factor, 5)), 1, 10)
        total += val * weight
    return round(total, 2)


def rank_ideas(ideas: list[dict]) -> list[dict]:
    """
    Rank a list of ideas by composite score (descending).
    
    Each idea dict should have a 'scores' sub-dict with factor keys.
    Returns the sorted list with computed composite scores.
    """
    for idea in ideas:
        if "scores" not in idea:
            idea["scores"] = {k: 5 for k in WEIGHTS}
        idea["scores"]["composite"] = compute_composite_score(idea["scores"])
    
    return sorted(ideas, key=lambda x: x["scores"]["composite"], reverse=True)


def score_from_research(research_data: dict) -> dict:
    """
    Derive factor scores from structured research data.
    Uses heuristics rather than pure LLM guessing.
    
    Args:
        research_data: Dict with keys like 'competitor_count', 'market_size_estimate', etc.
    
    Returns:
        Dict of factor scores (1-10 each)
    """
    scores = {}
    
    # Feasibility: inversely related to capital requirements and tech complexity
    capital = research_data.get("estimated_capital", "medium").lower()
    capital_map = {"low": 8, "medium": 6, "high": 3, "very high": 2}
    scores["feasibility"] = capital_map.get(capital, 5)
    
    # Market size: based on estimated TAM
    tam = research_data.get("estimated_tam_millions", 0)
    if tam > 10000:
        scores["market_size"] = 9
    elif tam > 1000:
        scores["market_size"] = 7
    elif tam > 100:
        scores["market_size"] = 5
    elif tam > 10:
        scores["market_size"] = 3
    else:
        scores["market_size"] = 2
    
    # Competition gap: fewer competitors = bigger gap = higher score
    comp_count = research_data.get("competitor_count", 5)
    if comp_count <= 2:
        scores["competition_gap"] = 9
    elif comp_count <= 5:
        scores["competition_gap"] = 7
    elif comp_count <= 10:
        scores["competition_gap"] = 5
    elif comp_count <= 20:
        scores["competition_gap"] = 3
    else:
        scores["competition_gap"] = 2
    
    # Time to revenue
    months = research_data.get("months_to_revenue", 12)
    if months <= 1:
        scores["time_to_revenue"] = 9
    elif months <= 3:
        scores["time_to_revenue"] = 7
    elif months <= 6:
        scores["time_to_revenue"] = 5
    elif months <= 12:
        scores["time_to_revenue"] = 4
    else:
        scores["time_to_revenue"] = 2
    
    # Scalability
    scalable = research_data.get("is_scalable", True)
    scores["scalability"] = 7 if scalable else 3
    
    # Founder fit - default to 5 (requires user input to personalize)
    scores["founder_fit"] = research_data.get("founder_fit", 5)
    
    scores["composite"] = compute_composite_score(scores)
    return scores
