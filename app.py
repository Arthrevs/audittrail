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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
cerebras_client = OpenAI(base_url="https://api.cerebras.ai/v1", api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None

app = FastAPI(title="AuditTrail Unified Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auditor Prompt: Instructions to return specific formatted data
COMBINED_AUDIT_PROMPT = """
You are a senior auditor. Analyze the user query and the model perspectives.
Return a STRICT JSON object:
{
  "consensus_score": 0-100,
  "claims": {"claim_name": "high/medium/low"},
  "uncertainties": ["list"],
  "risks": ["list"],
  "severity": ["list"],
  "comparison": "summary"
}
"""

def clean_json(text):
    text = re.sub(r"```json\s*|```\s*", "", text)
    return text.strip()

async def get_model_data(client, model_id, question):
    if not client: return None
    try:
        resp = client.chat.completions.create(model=model_id, messages=[{"role": "user", "content": question}])
        return resp.choices[0].message.content
    except: return None

@app.post("/audit", response_class=PlainTextResponse)
async def process_request(question: str = Body(..., media_type="text/plain")):
    # 1. Generate Primary Answer (OpenAI ONLY) as requested
    primary_answer = await get_model_data(openai_client, "gpt-4o-mini", question)
    
    # 2. Get Second Perspective (Cerebras) for the Consensus Audit
    cerebras_perspective = await get_model_data(cerebras_client, "llama3.3-70b", question)

    if not primary_answer:
        return "ERROR: Primary AI (OpenAI) failed to respond."

    # 3. Generate the Unified Audit using both perspectives
    audit_input = f"User Query: {question}\n\nOpenAI Perspective: {primary_answer}\n\nCerebras Perspective: {cerebras_perspective or 'N/A'}"
    
    try:
        audit_resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COMBINED_AUDIT_PROMPT},
                {"role": "user", "content": audit_input}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(clean_json(audit_resp.choices[0].message.content))
    except Exception as e:
        return f"AUDIT FAILURE: {str(e)}"

    # 4. Sequential Professional Formatting
    output = "ANSWER BY AI\n"  # Updated Header
    output += "========================================\n"
    output += f"{primary_answer}\n\n"
    
    output += "AUDITTRAIL UNIFIED REPORT\n"
    output += "========================================\n"
    output += f"Combined Consensus Confidence: {data.get('consensus_score') or 0}%\n\n"
    
    # Arranged Confidence per Claim as requested
    output += "• Confidence per Claim:\n"
    claims = data.get('claims', {})
    for claim, level in claims.items():
        output += f"{claim}: {level}\n"
    
    output += f"\n• Uncertainties & Missing Information:\n" + "\n".join([f"- {i}" for i in data.get('uncertainties', [])])
    output += f"\n\n• Reasoning Risks & Possible Biases:\n" + "\n".join([f"- {i}" for i in data.get('risks', [])])
    output += f"\n\n• Severity-Based Warnings:\n" + "\n".join([f"- {i}" for i in data.get('severity', [])])
    output += f"\n\n• One-Click Second Opinion (Comparison):\n{data.get('comparison')}\n\n"
    
    output += "DISCLAIMER: This report is a cross-model mathematical audit. Consult professionals for final decisions."
    return output