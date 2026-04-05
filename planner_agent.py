"""
Business Planner Agent - Structures complete business cases,
generates action items, and produces follow-up suggestions.
"""
import os
from google import genai
from dotenv import load_dotenv
from utils.helpers import extract_json_from_llm
from business_logic.risk_scorer import assess_risk
from business_logic.quantitative import full_quantitative_analysis

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash"


PLAN_PROMPT = """You are a senior startup advisor and strategic planner. Based on the business idea and market analysis, generate a high-intelligence, structured executive plan.

ANALYSIS RULES (STRICT):
- Use data-backed reasoning wherever possible.
- Use estimates and ranges (NOT guarantees).
- Clearly state assumptions.
- ALWAYS include risks.
- NEVER claim guaranteed success, 100% profit, or zero risk.

USER CONTEXT:
- TOP IDEA: {idea_title}
- BUSINESS TYPE: {business_type}
- ENTREPRENEUR STAGE: {stage}
- INDUSTRY: {industry}

TIERED PLANNING (INSTRUCTIONS):
- If Stage is 'idea': Provide a 30-Day Action Plan (Validation, Build, First Users, First Revenue).
- If Stage is 'growth': Provide a 60-90 Day Growth Plan (Channel execution, Revenue estimation, Partnerships).
- If Stage is 'scale': Provide a 6-12 Month Strategic Roadmap (Expansion, Funding, Simulations).

Return ONLY this JSON:
{{
    "summary": "<2-3 sentence executive summary of the business opportunity>",
    "plan_type": "<30-day|90-day|roadmap>",
    "milestones": [
        {{ "period": "<Week 1 / Month 1 / Q1>", "focus": "<Core focus>", "actions": ["action1", "action2"] }}
    ],
    "quantitative": {{
        "revenue_estimation": "<Estimated range for year 1 based on customers x price x conversion>",
        "growth_channel_roi": "<Ranked 1-10 expected ROI for primary channels>"
    }},
    "strategic_partnerships": [
        {{ "partner_type": "<type>", "rationale": "<why>", "impact": "<expected impact range>" }}
    ],
    "scale_strategy": {{
        "funding": "<bootstrap vs VC recommendation>",
        "expansion": "<next geo or segment>"
    }},
    "follow_up_questions": ["q1", "q2", "q3"],
    "reasoning_steps": ["step1", "step2", "step3"]
}}"""


def build_plan(query: str, intent_data: dict, research_data: dict,
               analysis_data: dict, top_idea: dict) -> dict:
    """
    Build a complete business plan from the top idea.
    """
    print(f"[PlannerAgent] Building plan for: {top_idea.get('idea_title', 'Unknown')}")
    
    stage = intent_data.get("stage", "idea")
    business_type = intent_data.get("business_type", "B2B")
    industry = research_data.get("industry", "Unknown")
    
    # 1. Generate plan via LLM
    plan_data = {}
    try:
        prompt = PLAN_PROMPT.format(
            idea_title=top_idea.get("idea_title", ""),
            business_type=business_type,
            industry=industry,
            market_trend=research_data.get("market_trend", "stable"),
            competitor_count=research_data.get("competitor_count", 0),
            stage=stage
        )
        
        response = client.models.generate_content(model=MODEL, contents=prompt)
        result = extract_json_from_llm(response.text)
        
        if result and isinstance(result, dict):
            plan_data = result
    except Exception as e:
        print(f"[PlannerAgent] Plan generation failed: {e}")
    
    # 2. Risk assessment (includes assumptions/risks as requested)
    risk_assessment = assess_risk(research_data)
    
    # 3. Quantitative (TAM/SAM/SOM)
    quantitative = full_quantitative_analysis(research_data)
    
    # Inject LLM revenue estimations if available
    if plan_data.get("quantitative"):
        quantitative["revenue_projections"] = plan_data["quantitative"].get("revenue_estimation")
    
    # 4. Combine
    return {
        "summary": plan_data.get("summary", "Business plan analysis in progress."),
        "this_week_actions": plan_data.get("milestones", [{}])[0].get("actions", ["Define MVPscope"]),
        "milestones": plan_data.get("milestones", []),
        "strategic_partnerships": plan_data.get("strategic_partnerships", []),
        "scale_strategy": plan_data.get("scale_strategy", {}),
        "follow_ups": plan_data.get("follow_up_questions", ["What is your initial budget?"]),
        "reasoning_steps": plan_data.get("reasoning_steps", []),
        "risk_assessment": risk_assessment,
        "quantitative": quantitative,
        "stage": stage
    }
