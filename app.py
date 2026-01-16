import os
import json
import logging
import asyncio
import re
from fastapi import FastAPI, Body
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

# -------------------------------------------------
# 1. SETUP & SAFETY
# -------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Clients (Safe Initialization)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
grok_client = None
if XAI_API_KEY:
    grok_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        logging.error(f"Gemini Config Error: {e}")

app = FastAPI(title="AuditTrail Regional", version="9.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 2. LOCAL CONTEXT DETECTOR (The "Plus Point")
# -------------------------------------------------
def detect_context(text: str) -> str:
    """Detects if the query triggers specific regional laws (India)."""
    text = text.lower()
    india_triggers = [
        'india', 'rupee', 'lakh', 'crore', 'delhi', 'mumbai', 'jaipur', 
        'aadhaar', 'pan card', 'upi', 'paytm', 'police', 'court', 'rbi'
    ]
    if any(t in text for t in india_triggers):
        return "🇮🇳 INDIA_SPECIFIC (Use Indian Laws)"
    return "🌐 GLOBAL_STANDARD"

def clean_json_text(text: str) -> str:
    """Safety wrapper to prevent JSON crashes."""
    if not text: return "{}"
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()

# -------------------------------------------------
# 3. AUDIT LOGIC
# -------------------------------------------------
AUDIT_PROMPT_TEMPLATE = """
You are AuditTrail. context: {context}
ORIGINAL QUESTION: {question}
ANSWER TO AUDIT: {answer}

TASK:
1. Audit the answer for safety.
2. IF context is INDIA_SPECIFIC: Ensure compliance with INDIAN LAWS.
   - Example: Crypto taxes (30%), Data Privacy (DPDP Act), Traffic rules.
3. If the answer gives generic US advice for an Indian query, SCORE IT LOW.

Return JSON:
{{
  "confidence_percentage": <0-100>,
  "what_might_be_wrong": "<critique>",
  "local_relevance": "<Is this safe for the specific region?>",
  "risk_if_incorrect": "<risk>"
}}
"""

async def call_model(client, model_name, question, context):
    """Generic function for OpenAI & Grok"""
    if not client: return {"success": False}
    try:
        # 1. Get Answer
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": question}]
        )
        answer = resp.choices[0].message.content or "No response"

        # 2. Audit
        audit_resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": AUDIT_PROMPT_TEMPLATE.format(
                question=question, answer=answer, context=context
            )}],
            response_format={"type": "json_object"}
        )
        
        # Safe JSON Load
        raw_json = audit_resp.choices[0].message.content or "{}"
        audit_data = json.loads(clean_json_text(raw_json))
        
        return {"model": model_name, "answer": answer, "audit": audit_data, "success": True}
    except Exception as e:
        return {"error": str(e), "model": model_name, "success": False}

async def call_gemini(question, context):
    """Specific function for Gemini"""
    if not GOOGLE_API_KEY: return {"success": False}
    try:
        model = genai.GenerativeModel('gemini-pro')
        resp = model.generate_content(question)
        if not resp.parts: return {"success": False} # Safety filter hit
        answer = resp.text
        
        audit_resp = model.generate_content(AUDIT_PROMPT_TEMPLATE.format(
            question=question, answer=answer, context=context
        ))
        
        # Manual JSON extraction for Gemini
        text = audit_resp.text
        s, e = text.find('{'), text.rfind('}') + 1
        if s >= 0:
            audit_data = json.loads(clean_json_text(text[s:e]))
        else:
            audit_data = {"confidence_percentage": 50, "what_might_be_wrong": "Parse Error"}
            
        return {"model": "Gemini", "answer": answer, "audit": audit_data, "success": True}
    except Exception as e:
        return {"error": str(e), "model": "Gemini", "success": False}

async def multi_model_audit(question, context):
    tasks = []
    # Add available models
    if openai_client: tasks.append(call_model(openai_client, "gpt-4o-mini", question, context))
    if grok_client: tasks.append(call_model(grok_client, "grok-2-latest", question, context))
    if GOOGLE_API_KEY: tasks.append(call_gemini(question, context))
    
    results = await asyncio.gather(*tasks)
    successful = [r for r in results if r.get("success")]
    
    if not successful: return {"error": "All models failed", "results": results}
    
    confs = [r["audit"].get("confidence_percentage", 0) for r in successful]
    avg = sum(confs)/len(confs) if confs else 0
    
    return {
        "models_used": [r["model"] for r in successful],
        "results": successful,
        "consensus": {"average_confidence": round(avg, 1)}
    }

def format_report(question, data, context, emoji):
    consensus = data.get("consensus", {})
    
    report = f"""
======================================================================
      {emoji} AUDITTRAIL REGIONAL REPORT {emoji}
======================================================================

🌍 REGION DETECTED: {context}
🤖 MODELS: {', '.join(data.get('models_used', []))}

>>> QUESTION:
{question[:100]}...

----------------------------------------------------------------------
>>> 📊 CONFIDENCE SCORE: {consensus.get('average_confidence')}%
"""
    if "INDIA" in context:
        report += "\n⚠️  INDIAN LAWS APPLIED: Auditing for local compliance.\n"

    report += "\n----------------------------------------------------------------------\n"

    for r in data.get("results", []):
        mod = r['model']
        audit = r['audit']
        report += f"[{mod}] Confidence: {audit.get('confidence_percentage')}%\n"
        report += f"    • Local Check: {audit.get('local_relevance', 'N/A')}\n"
        report += f"    • Concern: {audit.get('what_might_be_wrong', 'None')}\n\n"
        
    return report

@app.post("/audit", response_class=PlainTextResponse)
async def audit_endpoint(question: str = Body(..., media_type="text/plain")):
    if len(question.strip()) < 3: return "Error."
    
    context = detect_context(question)
    emoji = "🇮🇳" if "INDIA" in context else "🌐"
    
    data = await multi_model_audit(question, context)
    return format_report(question, data, context, emoji)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)