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

# Unified Auditor Prompt for Medical, Math, and Logic
COMBINED_AUDIT_PROMPT = """
You are a senior auditor specialized in Medical, Mathematics, and Logic.
Analyze the user's query and the AI's preliminary findings.
Return a STRICT JSON object:
{
  "consensus_score": 0-100,
  "confidence_per_claim": "List of key claims and their individual certainty",
  "uncertainties_and_missing": "Explicit list of what the AI doesn't know",
  "reasoning_risks_and_biases": "Potential logical fallacies or biases identified",
  "severity_warnings": "High-risk outcomes if the logic/diagnosis is wrong",
  "second_opinion_summary": "Internal comparison of model discrepancies"
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
    # Step 1: Parallel initial analysis from both keys
    ans_tasks = [
        get_model_data(openai_client, "gpt-4o-mini", question),
        get_model_data(cerebras_client, "llama3.3-70b", question)
    ]
    answers = await asyncio.gather(*ans_tasks)
    valid_answers = [a for a in answers if a]

    if not valid_answers:
        return "ERROR: API Configuration Missing or Failed."

    # Step 2: Generate the Unified Audit by comparing both model perspectives
    audit_input = f"User Query: {question}\n\nModel Perspectives:\n1. {valid_answers[0]}\n2. {valid_answers[1] if len(valid_answers)>1 else 'N/A'}"
    
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

    # Step 3: Sequential Professional Formatting
    output = "AUDITTRAIL UNIFIED TRANSPARENCY REPORT\n"
    output += "========================================\n"
    output += f"Combined Consensus Confidence: {data.get('consensus_score') or 0}%\n\n"
    
    output += f"• Confidence per Claim:\n{data.get('confidence_per_claim')}\n\n"
    output += f"• Uncertainties & Missing Information:\n{data.get('uncertainties_and_missing')}\n\n"
    output += f"• Reasoning Risks & Possible Biases:\n{data.get('reasoning_risks_and_biases')}\n\n"
    output += f"• Severity-Based Warnings:\n{data.get('severity_warnings')}\n\n"
    output += f"• One-Click Second Opinion (Comparison):\n{data.get('second_opinion_summary')}\n\n"
    
    output += "DISCLAIMER: This report is a cross-model mathematical audit. Consult professionals for final decisions."
    return output

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))