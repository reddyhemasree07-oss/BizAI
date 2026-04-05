"""
Research Agent - Performs market and competitor research using 
web search (DDGS) and deep crawling (Crawl4AI).
"""
import os
import time
import asyncio
import traceback
from ddgs import DDGS
from crawl4ai import AsyncWebCrawler
from urllib.parse import urlparse
from google import genai
from dotenv import load_dotenv
from utils.helpers import extract_json_from_llm, truncate

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash"


def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return "web"


def web_search(query: str, max_results: int = 10) -> list[dict]:
    """Perform web search using DDGS."""
    results = []
    try:
        ddgs = DDGS()
        text_results = list(ddgs.text(query, max_results=max_results))
        for r in text_results:
            results.append({
                "title": r.get("title", ""),
                "href": r.get("href", ""),
                "body": r.get("body", ""),
                "domain": _get_domain(r.get("href", "")),
                "provider": "Web"
            })
    except Exception as e:
        print(f"Web search failed: {e}")
    return results


def deep_crawl(url: str) -> str:
    """Deep crawl a URL using Crawl4AI, returns markdown content."""
    try:
        async def _crawl():
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                if result.success:
                    return result.markdown[:5000]  # Cap content length
                return ""
        return asyncio.run(_crawl())
    except Exception as e:
        print(f"Crawl failed for {url}: {e}")
        return ""


EXTRACT_PROMPT = """You are a business research analyst. From the following research data about "{query}", extract structured business intelligence.

RESEARCH DATA:
{context}

Return ONLY this JSON (no markdown fences, no explanation):
{{
    "industry": "<detected industry>",
    "competitor_count": <number>,
    "competitors": [
        {{"name": "<name>", "description": "<what they do>", "strength": "<key strength>", "weakness": "<key weakness>", "url": "<url if found>"}}
    ],
    "estimated_tam_millions": <number or 0>,
    "market_trend": "<declining|stable|growing|exploding>",
    "market_cagr_percent": <number>,
    "target_population": <number of potential customers or 0>,
    "avg_annual_spend_per_customer": <dollar amount or 0>,
    "technical_complexity": "<low|medium|high|very high>",
    "estimated_capital": "<low|medium|high|very high>",
    "months_to_revenue": <number>,
    "is_scalable": <true|false>,
    "demand_supply_gap": "<description>",
    "key_trends": ["trend1", "trend2"],
    "geography": "<primary geography>"
}}"""


def research(query: str, intent_data: dict = None) -> dict:
    """
    Full research pipeline:
    1. Generate targeted search queries
    2. Web search via DDGS
    3. Deep crawl top results via Crawl4AI
    4. Extract structured data via LLM
    
    Returns:
        Dict with research_data, sources, raw_context
    """
    print(f"[ResearchAgent] Starting research for: {query}")
    
    # Build targeted search queries
    topics = intent_data.get("key_topics", []) if intent_data else []
    industry = intent_data.get("industry_detected", "") if intent_data else ""
    
    search_queries = [
        query,
        f"{query} market size TAM",
        f"{query} competitors landscape",
    ]
    if industry and industry != "unknown":
        search_queries.append(f"{industry} industry trends 2025")
    
    # Collect all search results
    all_results = []
    sources_metadata = []
    
    for sq in search_queries[:3]:  # Limit to 3 queries to save time
        results = web_search(sq, max_results=6)
        all_results.extend(results)
    
    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        url = r.get("href", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)
    
    # Build context from search snippets
    context_parts = []
    for i, r in enumerate(unique_results[:12]):
        num = i + 1
        context_parts.append(f"[{num}] {r['title']}: {r['body']}")
        sources_metadata.append({
            "number": num,
            "title": r.get("title", ""),
            "domain": r.get("domain", ""),
            "source": r.get("href", ""),
            "snippet": truncate(r.get("body", ""), 150),
            "image": ""
        })
    
    # Deep crawl top 3 results for richer context
    for r in unique_results[:3]:
        url = r.get("href", "")
        if url:
            crawled = deep_crawl(url)
            if crawled:
                context_parts.append(f"[DEEP] {r['title']}:\n{truncate(crawled, 2000)}")
    
    raw_context = "\n\n".join(context_parts)
    
    # Extract structured data via LLM
    research_data = {}
    try:
        prompt = EXTRACT_PROMPT.format(query=query, context=raw_context[:8000])
        response = client.models.generate_content(model=MODEL, contents=prompt)
        extracted = extract_json_from_llm(response.text)
        if extracted and isinstance(extracted, dict):
            research_data = extracted
    except Exception as e:
        print(f"[ResearchAgent] Extraction failed: {e}")
        traceback.print_exc()
    
    # Ensure required fields exist with defaults
    defaults = {
        "industry": "Unknown",
        "competitor_count": 5,
        "competitors": [],
        "estimated_tam_millions": 0,
        "market_trend": "stable",
        "technical_complexity": "medium",
        "estimated_capital": "medium",
        "months_to_revenue": 6,
        "is_scalable": True,
        "geography": "Global"
    }
    for k, v in defaults.items():
        if k not in research_data:
            research_data[k] = v
    
    print(f"[ResearchAgent] Research complete. {len(sources_metadata)} sources found.")
    
    return {
        "research_data": research_data,
        "sources": sources_metadata,
        "raw_context": raw_context
    }
