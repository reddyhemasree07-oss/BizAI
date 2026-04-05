"""
Analysis Agent - Processes research data into actionable market analysis.
Produces competitor comparisons, SWOT analysis, and market insights.
"""
import os
from google import genai
from dotenv import load_dotenv
from utils.helpers import extract_json_from_llm

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash"


ANALYSIS_PROMPT = """You are a senior business analyst. Analyze the research data and produce a thorough market analysis.

ANALYSIS RULES (STRICT):
- Use data-backed reasoning wherever possible.
- Use estimates and ranges (NOT guarantees).
- Clearly state assumptions.
- ALWAYS include risks.
- NEVER claim guaranteed success, 100% profit, or zero risk.

USER CONTEXT:
- QUERY: "{query}"
- INDUSTRY: {industry}
- BUSINESS TYPE: {business_type}
- ENTREPRENEUR STAGE: {stage}

TIERED ACCESS (INSTRUCTIONS):
- If Stage is 'idea': Focus on Market Demand, existing problems, and gaps.
- If Stage is 'growth': Include Competitor Comparison (Pricing, Positioning, S&W) and Revenue Estimation gaps.
- If Stage is 'scale': Include Deep Competitor Intelligence and Market Expansion opportunities.

RESEARCH DATA:
{research_summary}

Return ONLY this JSON:
{{
    "market_overview": "<2-3 sentence market overview>",
    "market_maturity": "<emerging|growing|mature|declining>",
    "key_opportunities": ["opportunity1", "opportunity2", "opportunity3"],
    "key_threats": ["threat1", "threat2"],
    "customer_segments": [
        {{"segment": "<name>", "size": "<estimated size range>", "pain_point": "<main pain>", "willingness_to_pay": "<low|medium|high>"}}
    ],
    "competitor_comparison": {{
        "pricing_model": "<general pricing in market>",
        "positioning_map": "<how leaders position themselves>",
        "strengths_weaknesses": ["str1", "weak1"]
    }},
    "deep_intel": {{
        "positioning_gaps": ["gap1", "gap2"],
        "expansion_geographies": ["region1", "region2"]
    }}
}}"""


def analyze(query: str, research_data: dict, raw_context: str = "", intent_data: dict = None) -> dict:
    """
    Run market analysis on research data.
    
    Args:
        query: Original user query
        research_data: Structured data from research agent
        raw_context: Raw research text for additional context
        intent_data: Contextual data about the user's business stage/type
    
    Returns:
        Dict with market analysis results
    """
    print(f"[AnalysisAgent] Analyzing market for: {query}")
    
    intent_data = intent_data or {}
    industry = research_data.get("industry", "Unknown")
    stage = intent_data.get("stage", "idea")
    business_type = intent_data.get("business_type", "B2B")
    
    # Build research summary for the LLM
    competitors = research_data.get("competitors", [])
    comp_summary = "\n".join([
        f"- {c.get('name', 'Unknown')}: {c.get('description', '')} (Strength: {c.get('strength', 'N/A')})"
        for c in competitors[:8]
    ]) or "No specific competitors identified"
    
    research_summary = f"""
Market Trend: {research_data.get('market_trend', 'Unknown')}
Estimated TAM: ${research_data.get('estimated_tam_millions', 0)}M
Competitor Count: {research_data.get('competitor_count', 'Unknown')}
Key Competitors:
{comp_summary}
Technical Complexity: {research_data.get('technical_complexity', 'Unknown')}
Geography: {research_data.get('geography', 'Global')}
Key Trends: {', '.join(research_data.get('key_trends', []))}
Additional Context: {raw_context[:2000] if raw_context else 'None'}
"""
    
    try:
        prompt = ANALYSIS_PROMPT.format(
            query=query,
            industry=industry,
            business_type=business_type,
            stage=stage,
            research_summary=research_summary
        )
        
        response = client.models.generate_content(model=MODEL, contents=prompt)
        result = extract_json_from_llm(response.text)
        
        if result and isinstance(result, dict):
            return result
    except Exception as e:
        print(f"[AnalysisAgent] Analysis failed: {e}")
    
    # Fallback
    return {
        "market_overview": "Analysis could not be completed with available data.",
        "market_maturity": "unknown",
        "key_opportunities": [],
        "key_threats": [],
        "customer_segments": [],
        "competitor_comparison": {},
        "deep_intel": {}
    }
