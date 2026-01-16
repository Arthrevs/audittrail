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

# Environment Variables from Render
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Initialize Specialized Clients
# 1. GPT-4o-mini via OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# 2. GPT-OSS (Llama 3.3) via Cerebras
cerebras_client = None
if CEREBRAS_API_KEY:
    cerebras_client = OpenAI(
        base_url="https://api.cerebras.ai/v1",
        api_key=CEREBRAS_API_KEY
    )

app = FastAPI(title="AuditTrail Professional Core", version="11.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIT_PROMPT = """
You are a technical auditor. Evaluate the accuracy and safety of the response.
Return JSON:
{
  "confidence_percentage": <0-100>,
  "technical_critique": "<analysis>",
  "risk_assessment": "<consequences>",
  "missing_variables": "<required data>",
  "alternative_interpretations": "<other possibilities>"
}
"""

def clean_json(text: str) -> str:
    if not text: return "{}"
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()

async def run_audit(client, model_id, provider_name, question):
    if not client: return {"model": provider_name, "success": False, "error": "Missing Configuration"}
    try:
        # Step 1: Generate Primary Answer
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": question}]
        )
        answer = resp.choices[0].message.content or "No content returned."

        # Step 2: Perform Cross-Audit
        audit_resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": AUDIT_PROMPT},
                {"role": "user", "content": f"Query: {question}\\nAnswer: {answer}"}
            ],
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
    successful = [r for r in results if r.get("success")]
    confs = [r["audit"].get("confidence_percentage", 0) for r in successful]
    avg_conf = round(sum(confs)/len(confs), 1) if confs else 0

    # Professional Sequential Output
    output = "AUDITTRAIL TRANSPARENCY REPORT\n"
    output += f"Consensus Confidence: {avg_conf}%\n"
    output += f"Verification Status: {len(successful)} of {len(results)} active\n\n"

    for r in results:
        mod = r['model']
        if r.get('success'):
            audit = r['audit']
            output += f"--- [{mod}] ANALYSIS ---\n"
            output += f"Confidence Score: {audit.get('confidence_percentage')}%\n"
            output += f"Technical Critique: {audit.get('technical_critique')}\n"
            output += f"Missing Information: {audit.get('missing_variables')}\n"
            output += f"Alternative Interpretations: {audit.get('alternative_interpretations')}\n"
            output += f"Risk Factor: {audit.get('risk_assessment')}\n\n"
        else:
            output += f"[{mod}] STATUS: FAILED\nReason: {r.get('error')}\n\n"

    output += "MEDICAL DISCLAIMER: Systems cannot diagnose conditions. Consult a professional."
    return output

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))