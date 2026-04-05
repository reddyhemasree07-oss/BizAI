"""
Quantitative Business Analysis - TAM/SAM/SOM estimation,
revenue projections, cost structure, and growth modeling.

All estimates are ranges with confidence levels and stated assumptions.
NEVER claims 100% success, guaranteed profit, or zero risk.
"""


def estimate_market_size(research_data: dict) -> dict:
    """
    Estimate TAM, SAM, SOM from research data.
    Uses back-of-envelope calculations with clearly stated assumptions.
    """
    industry = research_data.get("industry", "Unknown")
    geography = research_data.get("geography", "Global")
    
    # Extract numeric signals from research
    tam_hint = research_data.get("estimated_tam_millions", None)
    population_target = research_data.get("target_population", None)
    avg_spend = research_data.get("avg_annual_spend_per_customer", None)
    
    assumptions = []
    
    # TAM estimation
    if tam_hint:
        tam_low = tam_hint * 0.7
        tam_high = tam_hint * 1.3
        tam_confidence = "medium"
        assumptions.append(f"TAM based on industry research data: ${tam_hint}M reported")
    elif population_target and avg_spend:
        tam_value = (population_target * avg_spend) / 1_000_000
        tam_low = tam_value * 0.6
        tam_high = tam_value * 1.4
        tam_confidence = "low"
        assumptions.append(f"TAM = {population_target:,} potential customers x ${avg_spend}/year")
    else:
        tam_low, tam_high = 100, 10000
        tam_confidence = "low"
        assumptions.append("TAM estimated from industry benchmarks - needs primary research")
    
    # SAM = TAM x addressable fraction (typically 10-40%)
    sam_fraction = research_data.get("sam_fraction", 0.2)
    sam_low = tam_low * sam_fraction * 0.8
    sam_high = tam_high * sam_fraction * 1.2
    assumptions.append(f"SAM = {sam_fraction*100:.0f}% of TAM (geographic + segment filter)")
    
    # SOM = SAM x realistic capture (typically 1-5% in first 3 years)
    som_fraction = research_data.get("som_fraction", 0.02)
    som_low = sam_low * som_fraction
    som_high = sam_high * som_fraction * 2
    assumptions.append(f"SOM = {som_fraction*100:.0f}% of SAM (realistic first 3-year capture)")
    
    return {
        "tam": f"${tam_low:,.0f}M - ${tam_high:,.0f}M",
        "tam_value": round((tam_low + tam_high) / 2, 1),
        "sam": f"${sam_low:,.0f}M - ${sam_high:,.0f}M",
        "sam_value": round((sam_low + sam_high) / 2, 1),
        "som": f"${som_low:,.1f}M - ${som_high:,.1f}M",
        "som_value": round((som_low + som_high) / 2, 1),
        "confidence": tam_confidence,
        "assumptions": assumptions
    }


def estimate_revenue(research_data: dict) -> dict:
    """Estimate revenue potential with ranges."""
    pricing = research_data.get("price_per_unit", 50)
    customers_y1 = research_data.get("projected_customers_year1", 100)
    growth_rate = research_data.get("annual_growth_rate", 0.5)
    
    monthly_y1 = pricing * customers_y1 / 12
    annual_y1 = pricing * customers_y1
    annual_y2 = annual_y1 * (1 + growth_rate)
    annual_y3 = annual_y2 * (1 + growth_rate * 0.8)
    
    return {
        "model": research_data.get("revenue_model", "Subscription"),
        "monthly_potential": f"${monthly_y1:,.0f} - ${monthly_y1 * 1.5:,.0f}",
        "annual_potential": f"${annual_y1:,.0f} - ${annual_y1 * 1.5:,.0f}",
        "year_2_potential": f"${annual_y2:,.0f}",
        "year_3_potential": f"${annual_y3:,.0f}",
        "time_to_first_revenue": research_data.get("months_to_revenue", "3-6 months"),
        "time_to_profitability": research_data.get("months_to_profit", "12-18 months"),
        "confidence": "low",
        "assumptions": [
            f"Price per unit/subscription: ${pricing}/month",
            f"Year 1 customers: {customers_y1}",
            f"Annual growth rate: {growth_rate*100:.0f}%",
            "Linear customer acquisition assumed"
        ]
    }


def estimate_costs(research_data: dict) -> dict:
    """Estimate cost structure."""
    complexity = research_data.get("technical_complexity", "medium").lower()
    
    initial_map = {"low": 5000, "medium": 25000, "high": 100000, "very high": 500000}
    monthly_map = {"low": 1000, "medium": 5000, "high": 20000, "very high": 50000}
    
    initial = initial_map.get(complexity, 25000)
    monthly = monthly_map.get(complexity, 5000)
    
    return {
        "initial_investment": f"${initial:,} - ${initial * 2:,}",
        "monthly_operating": f"${monthly:,} - ${monthly * 1.5:,.0f}",
        "key_costs": [
            "Development / Engineering",
            "Cloud infrastructure",
            "Marketing & customer acquisition",
            "Legal & compliance",
            "Salaries (if hiring)"
        ],
        "break_even_timeline": research_data.get("break_even", "12-18 months"),
        "assumptions": [
            f"Technical complexity: {complexity}",
            "Bootstrapped / lean startup approach assumed",
            "No venture funding factored in"
        ]
    }


def full_quantitative_analysis(research_data: dict) -> dict:
    """Run the complete quantitative analysis suite."""
    market = estimate_market_size(research_data)
    revenue = estimate_revenue(research_data)
    costs = estimate_costs(research_data)
    
    return {
        "market_size": market,
        "revenue_estimate": revenue,
        "cost_structure": costs,
        "growth_potential": research_data.get("growth_potential", "Moderate - dependent on execution"),
        "demand_supply_gap": research_data.get("demand_supply_gap", "Gap exists but needs validation"),
        "confidence": "low",
        "key_variables": [
            "Customer acquisition cost (CAC)",
            "Lifetime value (LTV)",
            "Churn rate",
            "Market growth rate",
            "Competitive response"
        ],
        "validation_steps": [
            "Survey 50+ potential customers about willingness to pay",
            "Run a landing page test with paid ads ($500 budget)",
            "Build a no-code MVP and onboard 10 beta users",
            "Measure activation and retention for 30 days",
            "Compare CAC vs LTV from beta data"
        ]
    }
