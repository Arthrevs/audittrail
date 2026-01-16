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
    version="6.2.0"
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

>>> INPUT SNIPPET:
{question[:200]}... (truncated)

------------------------------------------------------------
>>> AI ANALYSIS:
{data.get('answer')}

------------------------------------------------------------
>>> AUDIT METRICS:

[ Confidence Score ]
{data.get('confidence_percentage')}%

[ Why This Score? ]
{data.get('what_might_be_wrong')}

[ Missing Context / Variables ]
{data.get('uncertainty_areas')}

[ Risks of Single Answer ]
{data.get('risk_if_incorrect')}

[ Alternative Possibilities ]
{data.get('alternative_interpretation')}
============================================================
"""

# -------------------------------------------------
# 3. ENDPOINT (Text In -> Text Out)
# -------------------------------------------------
@app.post("/audit", response_class=PlainTextResponse)
def audit_question(
    # Input is strictly Plain Text
    question: str = Body(..., media_type="text/plain")
):
    try:
        # 1. Validate
        question = question.strip()
        if len(question) < 5:
            return "Error: Input is too short to analyze."

        # 2. Ask AI for Structure (Internally)
        system_prompt = """
        You are AuditTrail, a Logic & Security Auditor.
        Your goal is HONESTY, not politeness.
        
        STRICT SCORING RULES:
        1. [90-100%] DETERMINISTIC: Code/Logic is 100% clear, safe, and has only one possible outcome.
        2. [70-80%]  MINOR AMBIGUITY: Code is messy, or question is slightly vague but has a standard answer.
        3. [< 50%]   SECURITY CRITICAL: Code has bugs, buffer overflows, or dangerous instructions.
        4. [< 40%]   RACE CONDITIONS: Code outcome depends on luck (threading).
        5. [< 30%]   CONTEXT MISSING (THE "DEPENDS" RULE): 
           - If the user asks a Medical/Legal/Technical question but leaves out symptoms, duration, or jurisdiction.
           - You CANNOT be confident. You must list the possibilities (e.g., "Could be Migraine (80%), Could be Tumor (5%)").
           - Do NOT just say "See a doctor." Analyze the logic gap.
        6. [< 10%]   PARADOX/MALICE: Infinite loops, logical contradictions, or malicious intent.

        Output Instructions:
        - In 'answer', provide a detailed breakdown of possibilities, not just a generic recommendation.
        - In 'uncertainty_areas', list the specific questions you need answered to be 100% sure.

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