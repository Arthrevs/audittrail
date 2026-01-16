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
    raise RuntimeError("OPENAI_API_KEY not found. Check .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="AuditTrail API (Text-to-Text)",
    description="Accepts plain text, returns a plain text report.",
    version="6.0.0"
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

>>> YOUR QUESTION:
{question}

------------------------------------------------------------
>>> AI ANSWER:
{data.get('answer')}

------------------------------------------------------------
>>> AUDIT METRICS:

[ Confidence Score ]
{data.get('confidence_percentage')}%

[ What Might Be Wrong ]
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
    # Input is strictly Plain Text
    question: str = Body(..., media_type="text/plain")
):
    try:
        # 1. Validate
        question = question.strip()
        if len(question) < 5:
            return "Error: Question too short."

        # 2. Ask AI for Structure (Internally)
        # We still ask for JSON internally so the AI "thinks" in categories,
        # but the user will never see this JSON.
        system_prompt = """
        You are AuditTrail. 
        Answer the question and audit it.
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

# ... (rest of your code above)

if __name__ == "__main__":
    import uvicorn
    # Get the PORT from Google Cloud, default to 8080 if running locally
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)