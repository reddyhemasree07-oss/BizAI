"""
Risk Scoring Engine - Deterministic risk assessment for business ideas.
Evaluates market, execution, financial, competitive, and regulatory risks.
"""
from utils.helpers import clamp


RISK_CATEGORIES = [
    "market_risk",
    "execution_risk", 
    "financial_risk",
    "competitive_risk",
    "regulatory_risk"
]

RISK_WEIGHTS = {
    "market_risk": 0.25,
    "execution_risk": 0.25,
    "financial_risk": 0.20,
    "competitive_risk": 0.20,
    "regulatory_risk": 0.10,
}


def compute_aggregate_risk(risk_scores: dict) -> float:
    """Compute weighted aggregate risk score (1-10)."""
    total = 0.0
    for cat, weight in RISK_WEIGHTS.items():
        val = clamp(float(risk_scores.get(cat, 5)), 1, 10)
        total += val * weight
    return round(total, 2)


def assess_risk(business_data: dict) -> dict:
    """
    Assess risk across all categories based on business data.
    
    Args:
        business_data: Dict with research findings, market data, competitive landscape
    
    Returns:
        Complete risk assessment with per-category scores, aggregate, and mitigations
    """
    risks = {}
    mitigations = {}
    
    # Market Risk: Is there real demand?
    tam = business_data.get("estimated_tam_millions", 0)
    validation = business_data.get("demand_validated", False)
    if tam > 1000 and validation:
        risks["market_risk"] = 2
        mitigations["market_risk"] = "Large validated market - low risk"
    elif tam > 100:
        risks["market_risk"] = 4
        mitigations["market_risk"] = "Run customer discovery interviews to validate demand"
    elif tam > 0:
        risks["market_risk"] = 6
        mitigations["market_risk"] = "Small market - validate willingness to pay with landing page tests"
    else:
        risks["market_risk"] = 8
        mitigations["market_risk"] = "Market size unvalidated - prioritize market research immediately"
    
    # Execution Risk: Can you build this?
    complexity = business_data.get("technical_complexity", "medium").lower()
    complexity_map = {"low": 3, "medium": 5, "high": 7, "very high": 9}
    risks["execution_risk"] = complexity_map.get(complexity, 5)
    if risks["execution_risk"] >= 7:
        mitigations["execution_risk"] = "Build MVP with no-code tools first to validate before heavy engineering"
    else:
        mitigations["execution_risk"] = "Start with a minimal prototype; iterate based on user feedback"
    
    # Financial Risk: Can you fund this?
    capital = business_data.get("estimated_capital", "medium").lower()
    capital_map = {"low": 2, "medium": 5, "high": 7, "very high": 9}
    risks["financial_risk"] = capital_map.get(capital, 5)
    months_to_rev = business_data.get("months_to_revenue", 12)
    if months_to_rev > 12:
        risks["financial_risk"] = min(10, risks["financial_risk"] + 2)
    mitigations["financial_risk"] = "Pre-sell to early customers before building; consider bootstrapping"
    
    # Competitive Risk: How crowded is this space?
    comp_count = business_data.get("competitor_count", 5)
    has_moat = business_data.get("has_moat", False)
    if comp_count > 20:
        risks["competitive_risk"] = 9 if not has_moat else 6
    elif comp_count > 10:
        risks["competitive_risk"] = 7 if not has_moat else 4
    elif comp_count > 3:
        risks["competitive_risk"] = 5 if not has_moat else 3
    else:
        risks["competitive_risk"] = 3
    mitigations["competitive_risk"] = "Differentiate through niche focus, superior UX, or unique data advantage"
    
    # Regulatory Risk
    industry = business_data.get("industry", "").lower()
    regulated = any(kw in industry for kw in ["health", "finance", "insurance", "legal", "pharma", "crypto", "food"])
    risks["regulatory_risk"] = 7 if regulated else 3
    mitigations["regulatory_risk"] = "Consult domain-specific legal advisor early" if regulated else "Low regulatory exposure"
    
    aggregate = compute_aggregate_risk(risks)
    
    # Overall level
    if aggregate <= 3:
        level = "low"
    elif aggregate <= 6:
        level = "medium"
    else:
        level = "high"
    
    return {
        "categories": [
            {
                "category": cat.replace("_", " ").title(),
                "score": risks[cat],
                "description": f"Score: {risks[cat]}/10",
                "mitigation": mitigations.get(cat, "")
            }
            for cat in RISK_CATEGORIES
        ],
        "aggregate_score": aggregate,
        "overall_level": level,
        "key_risks": [
            cat.replace("_", " ").title()
            for cat, score in risks.items()
            if score >= 7
        ]
    }
