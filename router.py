"""
Mode Router - Central routing logic for Business Mode.
Detects whether queries are business-related and routes accordingly.
"""
import os
from google import genai
from dotenv import load_dotenv
from utils.helpers import extract_json_from_llm

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash"

# Keywords that signal business intent (used for fast pre-screening)
BUSINESS_SIGNALS = [
    "startup", "business idea", "business plan", "market size", "revenue model",
    "competitor", "pricing strategy", "customer segment", "mvp", "fundraise",
    "tam sam som", "go to market", "monetize", "validate idea",
    "product market fit", "scale", "growth strategy", "business model",
    "saas", "b2b", "b2c", "entrepreneur", "venture", "profit",
    "investment", "bootstrap", "side hustle", "passive income",
    "market research", "target audience", "value proposition",
    "launch", "co-founder", "pitch deck", "unit economics",
    "churn", "acquisition cost", "lifetime value", "market opportunity",
    "industry analysis", "swot", "competitive advantage", "disruption"
]


def quick_detect(query: str) -> tuple[bool, float]:
    """
    Fast keyword-based business intent detection.
    Returns (is_business, confidence).
    """
    query_lower = query.lower()
    matches = sum(1 for signal in BUSINESS_SIGNALS if signal in query_lower)
    
    if matches >= 3:
        return True, 0.9
    elif matches >= 2:
        return True, 0.75
    elif matches == 1:
        return True, 0.5
    
    # Check for question patterns
    business_patterns = [
        "how to start", "should i", "is there a market",
        "how much can i", "what business", "how to make money",
        "profitable", "how to sell", "how to build a",
        "idea for", "opportunity in"
    ]
    
    pattern_matches = sum(1 for p in business_patterns if p in query_lower)
    if pattern_matches > 0:
        return True, 0.4
    
    return False, 0.0


def llm_detect(query: str) -> dict:
    """
    LLM-powered business intent detection for ambiguous queries.
    Only called when keyword detection is uncertain.
    """
    prompt = f"""Determine if the following query is related to business, entrepreneurship, startups, or making money. 

Query: "{query}"

Return ONLY this JSON:
{{"is_business": true/false, "confidence": 0.0-1.0, "reason": "<brief reason>"}}"""
    
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        result = extract_json_from_llm(response.text)
        if result and isinstance(result, dict):
            return result
    except Exception as e:
        print(f"LLM detect failed: {e}")
    
    return {"is_business": False, "confidence": 0.0, "reason": "Detection failed"}


def detect_business_intent(query: str) -> dict:
    """
    Two-phase business intent detection:
    1. Fast keyword screening
    2. LLM classification for uncertain cases
    
    Returns:
        {
            "is_business": bool,
            "confidence": float (0-1),
            "suggestion": str (message for user if business detected while mode is OFF)
        }
    """
    # Phase 1: Fast keyword detection
    is_biz, confidence = quick_detect(query)
    
    if confidence >= 0.75:
        return {
            "is_business": True,
            "confidence": confidence,
            "suggestion": "[Business] This looks like a business question! Enable Business Mode for structured analysis, market research, and actionable recommendations."
        }
    
    if confidence <= 0.1:
        return {
            "is_business": False,
            "confidence": 0.0,
            "suggestion": ""
        }
    
    # Phase 2: LLM classification for uncertain cases
    llm_result = llm_detect(query)
    
    final_is_biz = llm_result.get("is_business", False)
    final_confidence = llm_result.get("confidence", 0.0)
    
    suggestion = ""
    if final_is_biz and final_confidence > 0.5:
        suggestion = "[Business] This looks like a business question! Enable Business Mode for structured analysis, market research, and actionable recommendations."
    
    return {
        "is_business": final_is_biz,
        "confidence": final_confidence,
        "suggestion": suggestion
    }
