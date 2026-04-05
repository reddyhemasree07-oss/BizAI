"""
Agent Graph - Orchestrates the multi-agent pipeline.
Runs agents in sequence: Intent -> Research -> Analysis -> Ideas -> Planner.

Uses simple sequential orchestration (no LangGraph dependency required).
Can be upgraded to LangGraph state machine in Phase 2.
"""
import traceback
from agents.intent_agent import detect_intent
from agents.research_agent import research
from agents.analysis_agent import analyze
from agents.idea_agent import generate_ideas
from agents.planner_agent import build_plan


def run_business_pipeline(query: str, stage_override: str = None, business_type: str = "B2C", is_premium: bool = False) -> dict:
    """
    Execute the full business co-founder pipeline.
    
    Args:
        query: User's business question
        stage_override: Optional stage override from UI (idea, growth, scale)
        business_type: B2B, B2C, or F2F
        is_premium: Whether the user has a paid subscription
    """
    print(f"\n{'='*60}")
    print(f"[Pipeline] Starting {business_type} analysis ({stage_override or 'auto'}) for: {query}")
    print(f"{'='*60}\n")
    
    errors = []
    
    # --- Step 1: Intent Detection ----------------------------------------
    print("[Pipeline] Step 1/5: Intent Detection")
    try:
        intent_data = detect_intent(query)
        # Use explicit overrides if provided
        if stage_override: intent_data["stage"] = stage_override
        intent_data["business_type"] = business_type
        intent_data["is_premium"] = is_premium
        
        print(f"  -> Stage: {intent_data.get('stage')} | Type: {business_type} | Premium: {is_premium}")
    except Exception as e:
        print(f"  X Intent detection failed: {e}")
        intent_data = {"intent": "explore_idea", "stage": stage_override or "idea", "business_type": business_type, "is_premium": is_premium}
        errors.append(f"Intent detection: {str(e)}")
    
    # --- Step 2: Research ------------------------------------------------
    print("[Pipeline] Step 2/5: Market Research")
    try:
        research_result = research(query, intent_data)
        research_data = research_result.get("research_data", {})
        sources = research_result.get("sources", [])
        raw_context = research_result.get("raw_context", "")
    except Exception as e:
        print(f"  X Research failed: {e}")
        research_data, sources, raw_context = {}, [], ""
        errors.append(f"Research: {str(e)}")
    
    # --- Step 3: Analysis ------------------------------------------------
    print("[Pipeline] Step 3/5: Market Analysis")
    try:
        analysis_data = analyze(query, research_data, raw_context, intent_data)
    except Exception as e:
        print(f"  X Analysis failed: {e}")
        analysis_data = {}
        errors.append(f"Analysis: {str(e)}")
    
    # --- Step 4: Idea Generation -----------------------------------------
    print("[Pipeline] Step 4/5: Idea Generation")
    try:
        ideas = generate_ideas(query, intent_data, research_data, analysis_data)
    except Exception as e:
        print(f"  X Idea generation failed: {e}")
        ideas = []
        errors.append(f"Idea generation: {str(e)}")
    
    # --- Step 5: Business Planning ---------------------------------------
    print("[Pipeline] Step 5/5: Business Planning")
    top_idea = ideas[0] if ideas else {"idea_title": "Unknown"}
    try:
        plan = build_plan(query, intent_data, research_data, analysis_data, top_idea)
    except Exception as e:
        print(f"  X Planning failed: {e}")
        plan = {"this_week_actions": [], "follow_ups": [], "summary": "Failed to generate plan."}
        errors.append(f"Planning: {str(e)}")
    
    # --- Assemble Final Response -----------------------------------------
    response = {
        "ideas": ideas,
        "market_analysis": plan.get("quantitative", {}),
        "competitors": research_data.get("competitors", []),
        "risk_assessment": plan.get("risk_assessment", {}),
        "this_week_actions": plan.get("this_week_actions", []),
        "follow_ups": plan.get("follow_ups", []),
        "sources": sources,
        "stage": intent_data.get("stage", "idea"),
        "business_type": business_type,
        "is_premium": is_premium,
        "confidence": "high" if len(sources) >= 5 else "medium",
        "summary": plan.get("summary", ""),
        "analysis": analysis_data,
        "errors": errors
    }
    
    return response
    
    print(f"\n{'='*60}")
    print(f"[Pipeline] Complete. {len(ideas)} ideas, {len(sources)} sources, confidence: {confidence}")
    if errors:
        print(f"[Pipeline] Warnings: {'; '.join(errors)}")
    print(f"{'='*60}\n")
    
    return response
