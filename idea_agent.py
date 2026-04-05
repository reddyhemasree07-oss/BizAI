"""
Idea Generator Agent - Generates and scores business ideas
based on research data and market analysis.

Uses LLM for creative generation, then deterministic scoring.
"""
import os
from google import genai
from dotenv import load_dotenv
from utils.helpers import extract_json_from_llm
from business_logic.idea_ranker import rank_ideas, score_from_research

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash"


IDEA_PROMPT = """You are a world-class startup advisor and idea generator. Based on the user's query and the market research, generate 3 specific, actionable business ideas.

ANALYSIS RULES (STRICT):
- Use data-backed reasoning wherever possible.
- Use estimates and ranges (NOT guarantees).
- Clearly state assumptions.
- ALWAYS include risks.
- NEVER claim guaranteed success, 100% profit, or zero risk.

USER QUERY: "{query}"
BUSINESS TYPE: {business_type} (B2B/B2C/F2F)
ENTREPRENEUR STAGE: {stage}
INDUSTRY: {industry}

MARKET RESEARCH:
- Market Size: ${tam}M TAM
- Competitors: {competitor_count}
- Market Trend: {market_trend}
- Key Opportunities: {opportunities}
- Customer Segments: {segments}

For each idea, you MUST fill in ALL fields. Be specific and concrete - no generic answers.

Return ONLY this JSON array:
[
    {{
        "idea_title": "<Catchy name>",
        "problem": "<Specific problem statement, 1-2 sentences>",
        "target_customer": "<Exact customer profile based on business type>",
        "solution": "<Concrete solution description>",
        "revenue_model": "<How it makes money, with price ranges and price points>",
        "key_risk": "<Single biggest risk - be specific>",
        "first_action_this_week": "<One concrete action to take THIS WEEK>",
        "estimated_capital": "<low|medium|high|very high>",
        "months_to_revenue": <number>,
        "is_scalable": <true|false>
    }},
    ...
]"""


def generate_ideas(query: str, intent_data: dict, research_data: dict, analysis_data: dict) -> list[dict]:
    """
    Generate and rank business ideas.
    
    1. LLM generates creative ideas based on research
    2. Deterministic scoring algorithm ranks them
    3. Returns sorted list with composite scores
    """
    print(f"[IdeaAgent] Generating ideas for: {query}")
    
    stage = intent_data.get("stage", "idea")
    business_type = intent_data.get("business_type", "B2C")
    industry = research_data.get("industry", "Unknown")
    tam = research_data.get("estimated_tam_millions", 0)
    competitor_count = research_data.get("competitor_count", 0)
    market_trend = research_data.get("market_trend", "stable")
    
    opportunities = ", ".join(analysis_data.get("key_opportunities", ["General market opportunity"]))
    segments = ", ".join([
        s.get("segment", "") for s in analysis_data.get("customer_segments", [])
    ]) or "General consumers"
    
    try:
        prompt = IDEA_PROMPT.format(
            query=query,
            business_type=business_type,
            stage=stage,
            industry=industry,
            tam=tam,
            competitor_count=competitor_count,
            market_trend=market_trend,
            opportunities=opportunities,
            segments=segments
        )
        
        response = client.models.generate_content(model=MODEL, contents=prompt)
        ideas = extract_json_from_llm(response.text)
        
        if ideas and isinstance(ideas, list):
            # Apply deterministic scoring to each idea
            for idea in ideas:
                # Build scoring input from idea + research
                scoring_input = {
                    "estimated_capital": idea.get("estimated_capital", research_data.get("estimated_capital", "medium")),
                    "estimated_tam_millions": tam,
                    "competitor_count": competitor_count,
                    "months_to_revenue": idea.get("months_to_revenue", research_data.get("months_to_revenue", 6)),
                    "is_scalable": idea.get("is_scalable", True),
                    "founder_fit": 5  # Default - can be personalized
                }
                idea["scores"] = score_from_research(scoring_input)
            
            # Rank by composite score
            ranked = rank_ideas(ideas)
            print(f"[IdeaAgent] Generated {len(ranked)} ideas. Top score: {ranked[0]['scores']['composite']}")
            return ranked
    
    except Exception as e:
        print(f"[IdeaAgent] Generation failed: {e}")
    
    # Fallback: single generic idea
    return [{
        "idea_title": f"Opportunity in {industry}",
        "problem": "Market research needed to identify specific problem",
        "target_customer": "To be determined through customer discovery",
        "solution": "Solution design pending market validation",
        "revenue_model": "To be determined",
        "key_risk": "Insufficient market data for confident assessment",
        "first_action_this_week": "Interview 5 potential customers about their biggest pain points",
        "scores": {
            "feasibility": 5, "market_size": 5, "competition_gap": 5,
            "time_to_revenue": 5, "scalability": 5, "founder_fit": 5,
            "composite": 5.0
        }
    }]
