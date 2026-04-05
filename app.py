"""
BizAI - Main Server (FastAPI)
Dual-mode system: Normal Perplexity search + BizAI pipeline.
"""
import os
import sys
import uuid
import json
import datetime
from contextlib import asynccontextmanager
import sys
import io
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from google import genai
from ddgs import DDGS

# Force UTF-8 for Windows console output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_engine import rag_engine
from mode_router.router import detect_business_intent
from agents.graph import run_business_pipeline
from models.schemas import (
    ChatRequest, BusinessAnalyzeRequest, BusinessDetectRequest,
    BusinessDetectResponse, BusinessAnalyzeResponse
)

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

UPLOAD_FOLDER = 'temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = FastAPI(title="BizAI", version="2.0.0")


# --- Static File Serving -----------------------------------------------------

@app.get("/")
async def serve_index():
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/{path:path}")
async def serve_static(path: str):
    # Only serve actual files, not API routes
    if path.startswith("api/"): # Safety check for some route configurations
        return JSONResponse({"error": "Resource not found"}, status_code=404)
        
    file_path = os.path.join(".", path)
    if os.path.isfile(file_path):
        return FileResponse(file_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


# --- PDF Upload --------------------------------------------------------------

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        return JSONResponse({"error": "Only PDF files are supported"}, status_code=400)
    
    file_id = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, file_id)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    success, err_msg = rag_engine.process_pdf(file_path, file_id)
    
    if success:
        return {"message": f"Successfully processed {file.filename}", "file_id": file_id}
    return JSONResponse({"error": err_msg}, status_code=500)


# --- URL Crawl ---------------------------------------------------------------

@app.post("/api/crawl")
async def crawl_url(request: Request):
    data = await request.json()
    url = data.get('url')
    if not url:
        return JSONResponse({"error": "No URL provided"}, status_code=400)
    if not url.startswith(('http://', 'https://')):
        return JSONResponse({"error": "Invalid URL format"}, status_code=400)
    
    success, err_msg = rag_engine.process_url(url)
    
    if success:
        return {"message": f"Successfully crawled {url}", "url": url}
    return JSONResponse({"error": err_msg}, status_code=500)


# --- Business Mode: Auto-Detect ---------------------------------------------

@app.post("/api/business/detect")
async def business_detect(request: Request):
    data = await request.json()
    query = data.get("query", "")
    if not query:
        return JSONResponse({"error": "No query provided"}, status_code=400)
    
    result = detect_business_intent(query)
    return result


# --- Business Mode: Full Analysis Pipeline ----------------------------------

@app.post("/api/business/analyze")
async def business_analyze(request: Request):
    data = await request.json()
    query = data.get("query", "")
    stage = data.get("stage")
    biz_type = data.get("business_type", "B2C")
    is_premium = data.get("is_premium", False)
    
    if not query:
        return JSONResponse({"error": "No query provided"}, status_code=400)
    
    try:
        result = run_business_pipeline(
            query, 
            stage_override=stage, 
            business_type=biz_type, 
            is_premium=is_premium
        )
        return JSONResponse(content=result)
    except Exception as e:
        print(f"Business pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": f"Business analysis failed: {str(e)}"},
            status_code=500
        )


# --- Normal Chat Mode (Preserved from original) -----------------------------

def perform_robust_search(query):
    """Searches the web using ddgs for live, relevant sources."""
    results = []
    try:
        ddgs = DDGS()
        print(f"DEBUG: Performing deep web search for: {query}")
        text_results = list(ddgs.text(query, max_results=10))
        if text_results:
            for r in text_results:
                results.append({
                    "title": r.get("title", "Unknown Title"),
                    "href": r.get("href"),
                    "body": r.get("body", ""),
                    "provider": "Web"
                })
        
        needs_news = not results or any(kw in query.lower() for kw in [
            "temperature", "weather", "ipl", "current", "latest",
            "update", "news", "war", "today"
        ])
        if needs_news:
            try:
                news_results = list(ddgs.news(query, max_results=6))
                for n in news_results:
                    results.append({
                        "title": n.get("title", "Live Update"),
                        "href": n.get("url"),
                        "body": n.get("body", ""),
                        "provider": n.get("source", "News")
                    })
            except Exception as ne:
                print(f"DEBUG: News search failed: {ne}")
    except Exception as e:
        print(f"DEBUG: Robust search failed: {e}")
    
    return results


@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    prompt = data.get('prompt')
    history = data.get('history', [])
    use_rag = data.get('use_rag', True)
    business_mode = data.get('business_mode', False)
    
    if not prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)
    
    # If business mode is ON, redirect to business pipeline
    if business_mode:
        try:
            result = run_business_pipeline(prompt)
            return JSONResponse(content=result)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    
    # --- Normal Perplexity mode (preserved) ---
    sources_metadata = []
    context_text = ""
    
    rag_engine.clear()
    
    try:
        search_results = perform_robust_search(prompt)
        for res in search_results:
            url = res.get('href')
            title = res.get('title', 'Unknown Title')
            body = res.get('body', '')
            domain = rag_engine._get_domain(url) if url else "web"
            
            if url:
                num = len(sources_metadata) + 1
                context_text += f"\n--- RESEARCH SOURCE [{num}] ---\nTITLE: {title}\nSNIPPET: {body}\n"
                sources_metadata.append({
                    "number": num,
                    "title": title,
                    "domain": domain,
                    "image": "",
                    "snippet": body[:150] + "...",
                    "source": url
                })
                
                if num <= 3:
                    try:
                        await rag_engine.process_url(url)
                    except Exception:
                        pass
    except Exception as se:
        print(f"DEBUG: Research failed: {se}")
    
    try:
        rag_context = rag_engine.retrieve_context_with_sources(prompt)
        for c in rag_context:
            existing = next((s for s in sources_metadata if c.get('source', '') in s.get('source', '')), None)
            if existing:
                context_text += f"\n--- SOURCE [{existing['number']}] (Full Content) ---\n{c['text']}\n"
            else:
                context_text += f"\n--- ADDITIONAL CONTEXT ---\n{c['text']}\n"
    except Exception:
        pass
    
    now = datetime.datetime.now()
    current_date_str = now.strftime("%A, %B %d, %Y")
    is_greeting = prompt.lower().strip() in [
        "hi", "hello", "hey", "hola", "greetings", "hi there", "hello there"
    ]
    
    if is_greeting:
        SYSTEM_INSTRUCTION = (
            f"Current Date: {current_date_str}. "
            "You are a helpful, friendly, and concise AI assistant. "
            "The user said a simple greeting. Respond warmly and ask how you can help them today. "
            "Do NOT use research mode or citations for this greeting."
        )
    else:
        SYSTEM_INSTRUCTION = (
            f"Current Date: {current_date_str}. "
            "You are an ELITE AI RESEARCHER specializing in deep factual synthesis. "
            "IMPORTANT: You are in STRICT GROUNDING MODE. Do NOT use phrases like 'Source [1] reports...' or 'According to Source [2]'. "
            "You MUST only cite using numbered badges like [1] at the end of sentences where facts are used. "
            "Structure your response as: 1. Direct synthesized answer. 2. Detailed bullets/paragraphs with [1][2]. 3. Bolded 'FINAL VERIFIED ANSWER'. "
            "CRITICAL: NO bibliography or 'Sources' sections. Purely functional citations [1]."
        )
    
    final_prompt = prompt
    if context_text and not is_greeting:
        final_prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            "Using the following numbered sources, answer the question accurately. "
            f"If the answer isn't in the sources, say so.\n\n"
            f"=== SOURCES ===\n{context_text}\n\n"
            f"=== QUESTION ===\n{prompt}"
        )
    else:
        final_prompt = f"{SYSTEM_INSTRUCTION}\n\n=== QUESTION ===\n{prompt}"
    
    MODEL_SEQUENCE = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro"
    ]
    
    def generate_stream():
        last_error = "Unknown error"
        
        if sources_metadata:
            try:
                yield f"SOURCES_LIST:{json.dumps(sources_metadata)}\n"
            except Exception as ey:
                print(f"Error yielding sources: {ey}")
        
        # Auto-detect business intent and suggest
        try:
            detect_result = detect_business_intent(prompt)
            if detect_result.get("is_business") and detect_result.get("confidence", 0) > 0.4:
                suggestion = detect_result.get("suggestion", "")
                if suggestion:
                    yield f"BIZ_SUGGEST:{json.dumps({'suggestion': suggestion, 'confidence': detect_result['confidence']})}\n"
        except Exception:
            pass
        
        success_any = False
        for model_id in MODEL_SEQUENCE:
            try:
                chat_session = client.chats.create(model=model_id, history=history)
                stream = chat_session.send_message_stream(final_prompt)
                
                for chunk in stream:
                    if chunk.text:
                        success_any = True
                        yield chunk.text
                
                if success_any:
                    return
            except Exception as e:
                last_error = str(e)
                print(f"Model {model_id} failed: {last_error}")
                continue
        
        if not success_any:
            error_data = {
                "error": "All AI models failed or are currently unavailable.",
                "details": last_error
            }
            yield f"AI_ERROR:{json.dumps(error_data)}\n"
    
    return StreamingResponse(generate_stream(), media_type='text/plain')


# --- Run Server --------------------------------------------------------------

if __name__ == '__main__':
    import uvicorn
    print("BizAI Server starting on http://127.0.0.1:8080")
    uvicorn.run(app, host="127.0.0.1", port=8080)
