import os
import json
import logging
import re
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
# Cerebras uses the OpenAI SDK structure but with a different base URL
cerebras_client = OpenAI(base_url="https://api.cerebras.ai/v1", api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None

app = FastAPI(title="AuditTrail Unified Core")

# CORS: Allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Define Input Model
class AuditRequest(BaseModel):
    question: str

# Auditor Prompt
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

# FIX: Removed 'async' to prevent blocking the event loop with sync client
def get_model_data(client, model_id, question):
    if not client: return None
    try:
        resp = client.chat.completions.create(
            model=model_id, 
            messages=[{"role": "user", "content": question}]
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.error(f"Model Error ({model_id}): {e}")
        return None

# 2. Endpoint uses JSON input/output
# FIX: Removed 'async' (and 'await') to allow FastAPI to handle threading automatically
@app.post("/audit", response_class=JSONResponse)
def process_request(request: AuditRequest):
    question = request.question
    
    # Generate Primary Answer (OpenAI)
    primary_answer = get_model_data(openai_client, "gpt-4o-mini", question)
    
    # Get Second Perspective (Cerebras)
    cerebras_perspective = get_model_data(cerebras_client, "llama3.3-70b", question)

    if not primary_answer:
        return {"report": "ERROR: Primary AI (OpenAI) failed to respond. Check API Keys."}

    # Generate Unified Audit
    audit_input = f"User Query: {question}\n\nOpenAI Perspective: {primary_answer}\n\nCerebras Perspective: {cerebras_perspective or 'N/A'}"
    
    data = {}
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
        return {"report": f"AUDIT FAILURE: {str(e)}"}

    # 3. Format Output Text
    output = "ANSWER BY AI\n"
    output += f"{primary_answer}\n\n"
    
    output += "AUDITTRAIL UNIFIED REPORT\n"
    output += f"Combined Consensus Confidence: {data.get('consensus_score', 0)}%\n\n"
    
    output += "• Confidence per Claim:\n"
    claims = data.get('claims', {})
    for claim, level in claims.items():
        output += f"{claim}: {level}\n"
    
    output += f"\n• Uncertainties & Missing Information:\n" + "\n".join([f"- {i}" for i in data.get('uncertainties', [])])
    output += f"\n\n• Reasoning Risks & Possible Biases:\n" + "\n".join([f"- {i}" for i in data.get('risks', [])])
    output += f"\n\n• Severity-Based Warnings:\n" + "\n".join([f"- {i}" for i in data.get('severity', [])])
    output += f"\n\n• Alternative Perspective (Comparison):\n{data.get('comparison', 'No comparison available.')}\n\n"
    
    output += "DISCLAIMER: This report is a cross-model mathematical audit. Consult professionals for final decisions."
    
    # 4. Return JSON Object
    return {"report": output}