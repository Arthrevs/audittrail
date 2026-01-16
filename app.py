import os
import json
import logging
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------------------
# 1. SETUP
# -------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found. Ensure it is set in Render.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="AuditTrail API (Text-to-Text)",
    description="Accepts plain text, returns a plain text report.",
    version="6.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 2. FORMATTER (The Secret Sauce)
# -------------------------------------------------
def format_text_report(question, data):
    """
    Converts structured data into a human-readable text report.
    """
    return f"""
============================================================
                AUDITTRAIL TRANSPARENCY REPORT
============================================================

>>> CODE SNIPPET / QUESTION:
{question[:200]}... (truncated for brevity)

------------------------------------------------------------
>>> AI ANSWER:
{data.get('answer')}

------------------------------------------------------------
>>> AUDIT METRICS:

[ Confidence Score ]
{data.get('confidence_percentage')}%

[ Analysis Logic ]
{data.get('what_might_be_wrong')}

[ Uncertainty Areas ]
{data.get('uncertainty_areas')}

[ Risks If Incorrect ]
{data.get('risk_if_incorrect')}

[ Alternative Interpretation ]
{data.get('alternative_interpretation')}
============================================================
"""

# -------------------------------------------------
# 3. ENDPOINT (Text In -> Text Out)
# -------------------------------------------------
@app.post("/audit", response_class=PlainTextResponse)
def audit_question(
    # Input is strictly Plain Text (Matches your Frontend)
    question: str = Body(..., media_type="text/plain")
):
    try:
        # 1. Validate
        question = question.strip()
        if len(question) < 5:
            return "Error: Code is too short to analyze."

        # 2. Ask AI for Structure (Internally)
        # This prompt now includes the advanced "Honesty" logic
        system_prompt = """
        You are AuditTrail, an advanced AI Security & Logic Auditor.
        You use "Generative Self-Reflection" to calculate confidence scores.

        STRICT SCORING RULES (The "Honesty" Protocol):
        1. [90-100%] SAFE: Code is deterministic, standard, and secure.
        2. [70-80%]  MINOR BUGS: Code is messy or inefficient, but safe.
        3. [< 50%]   SECURITY CRITICAL: Buffer overflows, raw pointers, SQL Injection, Hardcoded secrets.
        4. [< 40%]   RACE CONDITIONS / AMBIGUITY: Threading without locks, non-deterministic outputs (Conflicting Truths).
        5. [< 20%]   MALICIOUS INTENT: Insider threats, logic bombs, "Rage Quit" comments, sabotage.
        6. [< 10%]   PHILOSOPHICAL PARADOX: Infinite recursion logic, "Liar's Paradox", unsolvable logic traps.

        Reasoning:
        If the code's output cannot be predicted (Race Condition) or is logically impossible (Paradox), your confidence MUST be low. 
        If the code implies human malice (sabotage comments), your confidence in its "Safety" is near zero.

        Return strictly valid JSON with keys: 
        answer, confidence_percentage, what_might_be_wrong, 
        uncertainty_areas, risk_if_incorrect, alternative_interpretation.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # 3. Process & Format
        content = response.choices[0].message.content
        data = json.loads(content)

        # 4. Return Formatted String (Plain Text)
        return format_text_report(question, data)

    except Exception as e:
        return f"System Error: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)