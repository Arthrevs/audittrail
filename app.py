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
# 1. SETUP & CONFIGURATION
# -------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
grok_client = None
if XAI_API_KEY:
    grok_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        logging.error(f"Gemini Config Error: {e}")

app = FastAPI(title="AuditTrail Standard", version="10.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 2. UTILITY FUNCTIONS
# -------------------------------------------------
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
You are AuditTrail, a specialized AI logic and security auditor.
ORIGINAL QUESTION: {question}
ANSWER TO AUDIT: {answer}

TASK:
1. Conduct a rigorous audit of the provided answer for technical accuracy and safety.
2. Identify logical fallacies, security vulnerabilities (if code), or hazardous misinformation.
3. Quantify the confidence level based on the determinism of the problem.

Return strictly valid JSON:
{{
  "confidence_percentage": <0-100>,
  "what_might_be_wrong": "<technical critique>",
  "risk_assessment": "<potential consequences of incorrect implementation>",
  "uncertainty_factors": "<missing variables or ambiguous constraints>"
}}
"""

async def call_model(client, model_name, question):
    if not client: return {"model": model_name, "success": False, "error": "API Key Missing"}
    try:
        # 1. Generate primary response
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": question}]
        )
        answer = resp.choices[0].message.content or "No response"

        # 2. Execute audit
        audit_resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": AUDIT_PROMPT_TEMPLATE.format(
                question=question, answer=answer
            )}],
            response_format={"type": "json_object"}
        )
        
        raw_json = audit_resp.choices[0].message.content or "{}"
        audit_data = json.loads(clean_json_text(raw_json))
        
        return {"model": model_name, "answer": answer, "audit": audit_data, "success": True}
    except Exception as e:
        return {"error": str(e), "model": model_name, "success": False}

async def call_gemini(question):
    if not GOOGLE_API_KEY: return {"model": "Gemini", "success": False, "error": "API Key Missing"}
    try:
        model = genai.GenerativeModel('gemini-pro')
        resp = model.generate_content(question)
        if not resp.parts: return {"model": "Gemini", "success": False, "error": "Safety Block"}
        answer = resp.text
        
        audit_resp = model.generate_content(AUDIT_PROMPT_TEMPLATE.format(
            question=question, answer=answer
        ))
        
        text = audit_resp.text
        s, e = text.find('{'), text.rfind('}') + 1
        audit_data = json.loads(clean_json_text(text[s:e])) if s >= 0 else {"confidence_percentage": 0}
            
        return {"model": "Gemini", "answer": answer, "audit": audit_data, "success": True}
    except Exception as e:
        return {"error": str(e), "model": "Gemini", "success": False}

async def multi_model_audit(question):
    tasks = [
        call_model(openai_client, "gpt-4o-mini", question),
        call_model(grok_client, "grok-2-latest", question),
        call_gemini(question)
    ]
    
    results = await asyncio.gather(*tasks)
    successful = [r for r in results if r.get("success")]
    confs = [r["audit"].get("confidence_percentage", 0) for r in successful]
    avg = sum(confs)/len(confs) if confs else 0
    
    return {
        "results": results,
        "consensus": {"average_confidence": round(avg, 1)}
    }

def format_report_standard(question, data):
    consensus = data.get("consensus", {})
    
    report = f"""AUDITTRAIL TRANSPARENCY REPORT
Version: 10.1.0-Global
Audit Parameters: Multi-Model Consensus

QUERY SUMMARY
{question[:150]}...

METRICS
Consensus Confidence Score: {consensus.get('average_confidence')}%
Model Verification Count: {len([r for r in data.get('results', []) if r.get('success')])}

AUDIT DETAILS
"""

    for r in data.get("results", []):
        mod = r['model']
        if r.get('success'):
            audit = r['audit']
            report += f"\n[{mod}]\n"
            report += f"Confidence: {audit.get('confidence_percentage')}%\n"
            report += f"Analysis: {audit.get('what_might_be_wrong', 'N/A')}\n"
            report += f"Risk Factor: {audit.get('risk_assessment', 'N/A')}\n"
        else:
            report += f"\n[{mod}] STATUS: FAILED ({r.get('error', 'Authentication/Connection Error')})\n"
        
    return report

@app.post("/audit", response_class=PlainTextResponse)
async def audit_endpoint(question: str = Body(..., media_type="text/plain")):
    if len(question.strip()) < 3: return "Error: Input length insufficient."
    
    data = await multi_model_audit(question)
    return format_report_standard(question, data)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)