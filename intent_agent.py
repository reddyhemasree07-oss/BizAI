"""
Intent Agent - Detects business intent and classifies entrepreneur stage.
First node in the business agent pipeline.
"""
import os
import json
from google import genai
from dotenv import load_dotenv
from utils.helpers import extract_json_from_llm

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash"


INTENT_PROMPT = """You are a business intent classification AI. Analyze the user query and return a JSON object.

Classify the intent into EXACTLY one of:
- explore_idea: User wants to brainstorm or explore a new business idea
- validate_market: User wants to check if there's a real market for something
- analyze_competition: User wants to understand competitors
- build_plan: User wants a business plan or strategy
- find_opportunities: User is looking for market gaps or opportunities
- scale_business: User has an existing business and wants to grow
- general_advice: General business/entrepreneurship question

Classify the entrepreneur stage into EXACTLY one of:
- idea: Pre-launch, brainstorming, no product yet
- growth: Has a product/MVP, looking to grow
- scale: Established business, looking to scale operations

Also generate 2-3 clarifying questions that would help provide a better analysis.

User Query: "{query}"

Respond with ONLY this JSON (no markdown, no explanation):
{{
    "intent": "<intent_category>",
    "stage": "<stage>",
    "confidence": <0.0 to 1.0>,
    "clarifying_questions": ["question1", "question2"],
    "key_topics": ["topic1", "topic2"],
    "industry_detected": "<industry or 'unknown'>"
}}"""


def detect_intent(query: str) -> dict:
    """
    Detect business intent, stage, and extract key topics from a query.
    
    Returns:
        Dict with intent, stage, confidence, clarifying_questions, key_topics
    """
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=INTENT_PROMPT.format(query=query)
        )
        
        result = extract_json_from_llm(response.text)
        
        if result and isinstance(result, dict):
            # Validate required fields
            valid_intents = [
                "explore_idea", "validate_market", "analyze_competition",
                "build_plan", "find_opportunities", "scale_business", "general_advice"
            ]
            valid_stages = ["idea", "growth", "scale"]
            
            if result.get("intent") not in valid_intents:
                result["intent"] = "explore_idea"
            if result.get("stage") not in valid_stages:
                result["stage"] = "idea"
            
            return result
        
    except Exception as e:
        print(f"Intent detection failed: {e}")
    
    # Fallback
    return {
        "intent": "explore_idea",
        "stage": "idea",
        "confidence": 0.3,
        "clarifying_questions": [
            "What industry are you interested in?",
            "What problem are you trying to solve?"
        ],
        "key_topics": [],
        "industry_detected": "unknown"
    }
