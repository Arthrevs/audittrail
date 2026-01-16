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

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Environment Variables (Ensure these are set in Render)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
cerebras_client = OpenAI(base_url="https://api.cerebras.ai/v1", api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None

app = FastAPI(title="AuditTrail Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIT_PROMPT = """Evaluate this AI response. Return strictly valid JSON:
{"confidence": 0-100, "critique": "", "risk": "", "missing": "", "alt": ""}"""

def clean_json(text):
    text = re.sub(r"```json\s*|```\s*", "", text)
    return text.strip()

async def run_audit(client, model_id, provider_name, question):
    if not client: return {"model": provider_name, "success": False, "error": "Missing Config"}
    try:
        # Step 1: Get Answer
        resp = client.chat.completions.create(model=model_id, messages=[{"role": "user", "content": question}])
        answer = resp.choices[0].message.content or "No response."
        
        # Step 2: Get Audit
        audit_resp = client.chat.completions.create(
            model=model_id, 
            messages=[{"role": "system", "content": AUDIT_PROMPT}, {"role": "user", "content": f"Q: {question}\nA: {answer}"}],
            response_format={"type": "json_object"}
        )
        audit_data = json.loads(clean_json(audit_resp.choices[0].message.content))
        return {"model": provider_name, "answer": answer, "audit": audit_data, "success": True}
    except Exception as e:
        return {"model": provider_name, "success": False, "error": str(e)}

@app.post("/audit", response_class=PlainTextResponse)
async def process_request(question: str = Body(..., media_type="text/plain")):
    tasks = [
        run_audit(openai_client, "gpt-4o-mini", "GPT-4", question),
        run_audit(cerebras_client, "llama3.3-70b", "Cerebras", question)
    ]
    results = await asyncio.gather(*tasks)
    
    # Sequential Plain Text Formatting
    output = "AUDITTRAIL TRANSPARENCY REPORT\n"
    output += "==============================\n"
    
    for r in results:
        mod = r['model']
        if r.get('success'):
            audit = r['audit']
            output += f"\n[{mod}] ANALYSIS\n"
            output += f"Confidence Score: {audit.get('confidence')}%\n"
            output += f"Technical Critique: {audit.get('critique')}\n"
            output += f"Risk Factor: {audit.get('risk')}\n"
            output += f"Missing Info: {audit.get('missing')}\n"
        else:
            output += f"\n[{mod}] STATUS: FAILED\nReason: {r.get('error')}\n"
            
    output += "\nMEDICAL DISCLAIMER: Systems cannot diagnose conditions. Consult a professional."
    return output