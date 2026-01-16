import os
import json
import logging
import asyncio
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------------------
# 1. SETUP
# -------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found in environment")
if not CEREBRAS_API_KEY:
    print("WARNING: CEREBRAS_API_KEY not found in environment")

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

cerebras_client = OpenAI(
    api_key=CEREBRAS_API_KEY,
    base_url="https://api.cerebras.ai/v1"
) if CEREBRAS_API_KEY else None

app = FastAPI(
    title="AuditTrail API - Multi-Model Cross-Validation",
    description="AI Transparency with GPT-4 and Cerebras Llama",
    version="8.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 2. DOMAIN DETECTION
# -------------------------------------------------
def detect_domain(question: str) -> dict:
    q_lower = question.lower()

    medical_keywords = [
        'symptom', 'pain', 'disease', 'diagnosis', 'treatment',
        'medicine', 'doctor', 'health', 'sick', 'headache',
        'fever', 'blood', 'cancer', 'diabetes', 'toe', 'burning'
    ]

    legal_keywords = [
        'law', 'legal', 'contract', 'court', 'sue',
        'lawyer', 'attorney', 'rights', 'liable', 'tax'
    ]

    code_keywords = [
        'function', 'code', 'bug', 'error', 'debug',
        'compile', 'programming', 'script', 'syntax'
    ]

    if any(kw in q_lower for kw in medical_keywords):
        return {"domain": "MEDICAL", "risk": "VERY_HIGH"}
    elif any(kw in q_lower for kw in legal_keywords):
        return {"domain": "LEGAL", "risk": "VERY_HIGH"}
    elif any(kw in q_lower for kw in code_keywords):
        return {"domain": "CODE", "risk": "MEDIUM"}
    else:
        return {"domain": "GENERAL", "risk": "LOW"}

# -------------------------------------------------
# 3. MULTI-MODEL AUDIT SYSTEM
# -------------------------------------------------
AUDIT_PROMPT_TEMPLATE = """
You are AuditTrail, an AI transparency system. Analyze this AI response critically.

ORIGINAL QUESTION:
{question}

AI'S ANSWER:
{answer}

Return valid JSON with these keys:
{{
  "confidence_percentage": <number 0-100>,
  "what_might_be_wrong": "<issues or gaps>",
  "uncertainty_areas": "<missing information>",
  "alternative_interpretation": "<alternative explanations>",
  "risk_if_incorrect": "<possible consequences>"
}}

For MEDICAL and LEGAL domains, confidence should usually be below 50 percent.
"""

async def call_openai(question: str) -> dict:
    if not openai_client:
        return {"error": "OpenAI API key not configured", "model": "GPT-4"}

    try:
        answer_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Answer clearly and helpfully."},
                {"role": "user", "content": question}
            ],
            temperature=0.5
        )

        answer = answer_response.choices[0].message.content

        audit_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": AUDIT_PROMPT_TEMPLATE.format(question=question, answer=answer)}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        audit_data = json.loads(audit_response.choices[0].message.content)

        return {
            "model": "GPT-4",
            "answer": answer,
            "audit": audit_data,
            "success": True
        }

    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return {"error": str(e), "model": "GPT-4", "success": False}

# -------------------------------------------------
# 4. REPORT FORMATTER
# -------------------------------------------------
def format_multi_model_report(question, data, domain_info):
    consensus = data["consensus"]
    results = data["results"]

    report = f"""
============================================================
AUDITTRAIL MULTI-MODEL TRANSPARENCY REPORT
============================================================

DOMAIN: {domain_info['domain']}
RISK LEVEL: {domain_info['risk']}
MODELS: {', '.join(data['models_used'])}

QUESTION:
{question}

============================================================
MODEL RESPONSES:
"""

    for r in results:
        report += f"""
[{r['model']}]
{r['answer'][:400]}
"""

    report += f"""
============================================================
CONSENSUS CONFIDENCE

Average Confidence: {consensus['average_confidence']}%
Range: {consensus['min_confidence']}% - {consensus['max_confidence']}%
Agreement Level: {consensus['agreement_level']}
"""

    best = max(results, key=lambda x: x["audit"]["confidence_percentage"])
    audit = best["audit"]

    report += f"""
============================================================
DETAILED ANALYSIS (from {best['model']})

What Might Be Wrong:
{audit['what_might_be_wrong']}

Missing Information:
{audit['uncertainty_areas']}

Alternative Interpretations:
{audit['alternative_interpretation']}

Risk If Incorrect:
{audit['risk_if_incorrect']}
"""

    return report

# -------------------------------------------------
# 5. MAIN ENDPOINT
# -------------------------------------------------
@app.post("/audit")
async def audit_question(request: dict = Body(...)):
    question = request.get("question", "").strip()
    if len(question) < 5:
        return {"error": "Question too short"}

    domain_info = detect_domain(question)
    multi_model_data = await multi_model_audit(question)

    report = format_multi_model_report(question, multi_model_data, domain_info)
    return {"report": report, "success": True}

# -------------------------------------------------
# 6. RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))

    print("AuditTrail Multi-Model v8.1")
    print(f"Endpoint: POST http://localhost:{port}/audit")
    uvicorn.run(app, host="0.0.0.0", port=port)
