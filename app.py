import os
import json
import logging
import asyncio
from fastapi import FastAPI, Body
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
import anthropic
import google.generativeai as genai

# -------------------------------------------------
# 1. SETUP
# -------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI(
    title="AuditTrail API - Multi-Model Cross-Validation",
    description="AI Transparency with GPT, Claude, and Gemini",
    version="8.0.0"
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
    """Detects domain and risk level from question"""
    q_lower = question.lower()
    
    medical_keywords = ['symptom', 'pain', 'disease', 'diagnosis', 'treatment', 
                       'medicine', 'doctor', 'health', 'sick', 'headache', 
                       'fever', 'blood', 'cancer', 'diabetes', 'toe', 'burning']
    
    legal_keywords = ['law', 'legal', 'contract', 'court', 'sue', 'lawyer',
                     'attorney', 'rights', 'liable', 'deduct', 'tax']
    
    code_keywords = ['function', 'code', 'bug', 'error', 'debug', 'compile',
                    'programming', 'script', 'syntax', 'loop', 'array']
    
    math_keywords = ['calculate', 'equation', 'solve', 'formula', 'integral',
                    'derivative', 'theorem', 'proof', 'mathematics']
    
    philosophy_keywords = ['philosophy', 'ethics', 'moral', 'meaning', 'existence',
                          'consciousness', 'free will', 'metaphysics']
    
    education_keywords = ['learn', 'study', 'homework', 'assignment', 'explain',
                         'understand', 'teach', 'lesson', 'quiz']
    
    finance_keywords = ['invest', 'stock', 'money', 'bitcoin', 'crypto',
                       'trading', 'portfolio', 'market', 'financial']
    
    if any(kw in q_lower for kw in medical_keywords):
        return {"domain": "MEDICAL", "risk": "VERY_HIGH", "emoji": "🏥"}
    elif any(kw in q_lower for kw in legal_keywords):
        return {"domain": "LEGAL", "risk": "VERY_HIGH", "emoji": "⚖️"}
    elif any(kw in q_lower for kw in code_keywords):
        return {"domain": "CODE", "risk": "MEDIUM", "emoji": "💻"}
    elif any(kw in q_lower for kw in math_keywords):
        return {"domain": "MATHEMATICS", "risk": "LOW", "emoji": "🔢"}
    elif any(kw in q_lower for kw in philosophy_keywords):
        return {"domain": "PHILOSOPHY", "risk": "LOW", "emoji": "🤔"}
    elif any(kw in q_lower for kw in education_keywords):
        return {"domain": "EDUCATION", "risk": "MEDIUM", "emoji": "📚"}
    elif any(kw in q_lower for kw in finance_keywords):
        return {"domain": "FINANCE", "risk": "HIGH", "emoji": "💰"}
    else:
        return {"domain": "GENERAL", "risk": "LOW", "emoji": "💬"}

# -------------------------------------------------
# 3. MULTI-MODEL AUDIT SYSTEM
# -------------------------------------------------

AUDIT_PROMPT_TEMPLATE = """
You are AuditTrail, an AI transparency system. Analyze this AI response critically.

ORIGINAL QUESTION:
{question}

AI'S ANSWER:
{answer}

YOUR JOB: Audit this answer with brutal honesty.

Return valid JSON with these keys:
{{
  "confidence_percentage": <number 0-100>,
  "what_might_be_wrong": "<specific issues, assumptions, gaps>",
  "uncertainty_areas": "<critical missing information>",
  "alternative_interpretation": "<if confidence < 70%, list alternative scenarios>",
  "risk_if_incorrect": "<consequences if wrong>"
}}

CONFIDENCE RULES:
- 90-100%: Verifiable facts, mathematical proofs
- 70-89%: Well-established info, minor gaps
- 50-69%: Multiple valid interpretations, missing context
- 30-49%: High uncertainty, many unknowns
- 10-29%: Speculation, critical info missing
- 0-9%: Cannot answer responsibly

For MEDICAL/LEGAL: Rarely exceed 50% without full context.
Be honest about what you DON'T know.
"""

async def call_openai(question: str) -> dict:
    """Get answer + audit from GPT-4"""
    if not openai_client:
        return {"error": "OpenAI API key not configured", "model": "GPT-4"}
    
    try:
        # Step 1: Get initial answer
        answer_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Answer the question clearly and helpfully."},
                {"role": "user", "content": question}
            ],
            temperature=0.5
        )
        answer = answer_response.choices[0].message.content
        
        # Step 2: Audit the answer
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

async def call_claude(question: str) -> dict:
    """Get answer + audit from Claude"""
    if not anthropic_client:
        return {"error": "Anthropic API key not configured", "model": "Claude"}
    
    try:
        # Step 1: Get initial answer
        answer_response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": question}
            ]
        )
        answer = answer_response.content[0].text
        
        # Step 2: Audit the answer
        audit_response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": AUDIT_PROMPT_TEMPLATE.format(question=question, answer=answer)}
            ]
        )
        
        audit_text = audit_response.content[0].text
        # Claude doesn't force JSON, so try to parse or extract
        try:
            audit_data = json.loads(audit_text)
        except:
            # Fallback: extract confidence from text
            audit_data = {
                "confidence_percentage": 50,
                "what_might_be_wrong": "Unable to parse structured audit",
                "uncertainty_areas": audit_text[:200],
                "alternative_interpretation": "",
                "risk_if_incorrect": "Unknown"
            }
        
        return {
            "model": "Claude",
            "answer": answer,
            "audit": audit_data,
            "success": True
        }
    except Exception as e:
        logging.error(f"Claude error: {e}")
        return {"error": str(e), "model": "Claude", "success": False}

async def call_gemini(question: str) -> dict:
    """Get answer + audit from Gemini"""
    if not GOOGLE_API_KEY:
        return {"error": "Google API key not configured", "model": "Gemini"}
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Step 1: Get initial answer
        answer_response = model.generate_content(question)
        answer = answer_response.text
        
        # Step 2: Audit the answer
        audit_prompt = AUDIT_PROMPT_TEMPLATE.format(question=question, answer=answer)
        audit_response = model.generate_content(audit_prompt)
        audit_text = audit_response.text
        
        # Try to extract JSON
        try:
            # Look for JSON in the response
            start = audit_text.find('{')
            end = audit_text.rfind('}') + 1
            if start >= 0 and end > start:
                audit_data = json.loads(audit_text[start:end])
            else:
                raise ValueError("No JSON found")
        except:
            audit_data = {
                "confidence_percentage": 50,
                "what_might_be_wrong": "Unable to parse structured audit",
                "uncertainty_areas": audit_text[:200],
                "alternative_interpretation": "",
                "risk_if_incorrect": "Unknown"
            }
        
        return {
            "model": "Gemini",
            "answer": answer,
            "audit": audit_data,
            "success": True
        }
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return {"error": str(e), "model": "Gemini", "success": False}

async def multi_model_audit(question: str) -> dict:
    """Run question through ALL available models in parallel"""
    tasks = []
    
    if openai_client:
        tasks.append(call_openai(question))
    if anthropic_client:
        tasks.append(call_claude(question))
    if GOOGLE_API_KEY:
        tasks.append(call_gemini(question))
    
    if not tasks:
        return {"error": "No API keys configured"}
    
    results = await asyncio.gather(*tasks)
    
    # Calculate consensus
    successful_results = [r for r in results if r.get("success")]
    
    if not successful_results:
        return {"error": "All models failed", "results": results}
    
    # Extract confidence scores
    confidences = [r["audit"]["confidence_percentage"] for r in successful_results]
    avg_confidence = sum(confidences) / len(confidences)
    min_confidence = min(confidences)
    max_confidence = max(confidences)
    
    # Check agreement
    confidence_spread = max_confidence - min_confidence
    agreement_level = "HIGH" if confidence_spread < 20 else "MODERATE" if confidence_spread < 40 else "LOW"
    
    return {
        "models_used": [r["model"] for r in successful_results],
        "results": successful_results,
        "consensus": {
            "average_confidence": round(avg_confidence, 1),
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "confidence_spread": confidence_spread,
            "agreement_level": agreement_level
        }
    }

# -------------------------------------------------
# 4. ENHANCED FORMATTER WITH MULTI-MODEL DATA
# -------------------------------------------------
def format_multi_model_report(question, multi_model_data, domain_info):
    domain = domain_info['domain']
    risk = domain_info['risk']
    emoji = domain_info['emoji']
    
    risk_indicator = {
        "VERY_HIGH": "🔴🔴🔴 CRITICAL - VERIFY WITH PROFESSIONAL",
        "HIGH": "🔴🔴 HIGH - DOUBLE CHECK BEFORE ACTING",
        "MEDIUM": "🟡 MEDIUM - REVIEW CAREFULLY",
        "LOW": "🟢 LOW - GENERALLY SAFE"
    }
    
    consensus = multi_model_data.get("consensus", {})
    results = multi_model_data.get("results", [])
    
    report = f"""
{'='*70}
     {emoji} AUDITTRAIL MULTI-MODEL TRANSPARENCY REPORT {emoji}
{'='*70}

DOMAIN DETECTED: {domain}
RISK LEVEL: {risk_indicator.get(risk, risk)}
MODELS ANALYZED: {', '.join(multi_model_data.get('models_used', []))}

{'='*70}
>>> YOUR QUESTION:
{question}

{'='*70}
>>> 🤖 MULTI-MODEL RESPONSES:

"""
    
    # Show each model's answer
    for i, result in enumerate(results, 1):
        model_name = result.get("model", f"Model {i}")
        answer = result.get("answer", "No response")
        report += f"""
┌─ {model_name} RESPONSE ───────────────────────────────────────┐
│ {answer[:400]}{'...' if len(answer) > 400 else ''}
└────────────────────────────────────────────────────────────────┘
"""
    
    # Consensus confidence
    avg_conf = consensus.get("average_confidence", 0)
    min_conf = consensus.get("min_confidence", 0)
    max_conf = consensus.get("max_confidence", 0)
    spread = consensus.get("confidence_spread", 0)
    agreement = consensus.get("agreement_level", "UNKNOWN")
    
    report += f"""
{'='*70}
>>> 📊 CROSS-MODEL CONFIDENCE ANALYSIS:

┌─ CONSENSUS CONFIDENCE ─────────────────────────────────────┐
│ Average Confidence: {avg_conf}%
│ Range: {min_conf}% - {max_conf}% (spread: {spread}%)
│ Model Agreement: {agreement}
"""
    
    if avg_conf >= 80:
        report += "│ ✓✓✓ HIGH CONSENSUS - Models strongly agree\n"
    elif avg_conf >= 50:
        report += "│ ⚠ MODERATE CONSENSUS - Some uncertainty present\n"
    else:
        report += "│ 🚨 LOW CONSENSUS - High uncertainty, verify carefully\n"
    
    if spread > 30:
        report += f"│ ⚠️ MAJOR DISAGREEMENT: {spread}% confidence spread between models!\n"
    
    report += "└────────────────────────────────────────────────────────────┘\n\n"
    
    # Individual model confidence scores
    report += "┌─ INDIVIDUAL MODEL CONFIDENCE SCORES ───────────────────────┐\n"
    for result in results:
        model = result.get("model", "Unknown")
        conf = result.get("audit", {}).get("confidence_percentage", 0)
        bar_length = int(conf / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        report += f"│ {model:12} │ {bar} │ {conf}%\n"
    report += "└────────────────────────────────────────────────────────────┘\n\n"
    
    # Aggregated audit analysis
    report += "┌─ AGGREGATED AUDIT ANALYSIS ────────────────────────────────┐\n"
    
    # Collect all "what might be wrong" from models
    concerns = []
    for result in results:
        concern = result.get("audit", {}).get("what_might_be_wrong", "")
        if concern and concern not in concerns:
            concerns.append(concern)
    
    if concerns:
        report += "│ COMMON CONCERNS ACROSS MODELS:\n"
        for i, concern in enumerate(concerns[:3], 1):  # Top 3
            report += f"│ {i}. {concern[:60]}...\n"
    
    report += "└────────────────────────────────────────────────────────────┘\n\n"
    
    # Show one detailed audit (from highest confidence model)
    best_result = max(results, key=lambda r: r.get("audit", {}).get("confidence_percentage", 0))
    audit = best_result.get("audit", {})
    
    report += f"""
┌─ DETAILED ANALYSIS (from {best_result.get('model')}) ──────────────────┐

[ What Might Be Wrong ]
{audit.get('what_might_be_wrong', 'N/A')}

[ Missing Information ]
{audit.get('uncertainty_areas', 'N/A')}

[ Alternative Interpretations ]
{audit.get('alternative_interpretation', 'N/A')}

[ Risk If Incorrect ]
{audit.get('risk_if_incorrect', 'N/A')}
└────────────────────────────────────────────────────────────┘

"""
    
    # Domain-specific warnings
    if domain == "MEDICAL":
        report += """
┌─ ⚠️ MEDICAL DISCLAIMER ─────────────────────────────────────┐
│ 🚨 This is NOT medical advice from any model               │
│ 🚨 AI cannot diagnose conditions reliably                  │
│ 🚨 See a licensed healthcare professional immediately      │
│ 🚨 For emergencies, call your local emergency number       │
└────────────────────────────────────────────────────────────┘
"""
    elif domain == "LEGAL":
        report += """
┌─ ⚠️ LEGAL DISCLAIMER ───────────────────────────────────────┐
│ 🚨 This is NOT legal advice from any model                 │
│ 🚨 AI cannot replace a licensed attorney                   │
│ 🚨 Laws vary by jurisdiction and change frequently         │
│ 🚨 Consult a qualified lawyer for your specific situation  │
└────────────────────────────────────────────────────────────┘
"""
    
    # Recommendations based on consensus
    report += "\n┌─ RECOMMENDED ACTIONS ──────────────────────────────────────┐\n"
    
    if avg_conf < 50 or agreement == "LOW":
        report += """│ 🔴 LOW CONFIDENCE / POOR AGREEMENT DETECTED                │
│ → DO NOT act on this information alone                    │
│ → Consult human experts immediately                       │
│ → Models disagree significantly - high uncertainty         │
"""
    elif avg_conf < 70:
        report += """│ 🟡 MODERATE CONFIDENCE - PROCEED WITH CAUTION              │
│ → Verify critical details before acting                   │
│ → Cross-reference with authoritative sources              │
│ → Consider professional consultation                      │
"""
    else:
        report += """│ 🟢 HIGH CONFIDENCE - Models show strong agreement          │
│ → Information appears relatively reliable                 │
│ → Still verify important claims                           │
│ → Use critical thinking when applying                     │
"""
    
    if spread > 30:
        report += """│                                                            │
│ ⚠️ WARNING: Large confidence spread between models         │
│ This suggests fundamental uncertainty about the answer    │
"""
    
    report += """└────────────────────────────────────────────────────────────┘

"""
    
    report += f"""{'='*70}
Generated by AuditTrail v8.0 - Multi-Model AI Transparency
Powered by: {', '.join(multi_model_data.get('models_used', []))}
{'='*70}
"""
    
    return report

# -------------------------------------------------
# 5. MAIN ENDPOINT
# -------------------------------------------------
@app.post("/audit", response_class=PlainTextResponse)
async def audit_question(question: str = Body(..., media_type="text/plain")):
    try:
        # Validate
        if len(question.strip()) < 5:
            return "❌ Error: Question too short. Please provide more detail."
        
        # Detect domain
        domain_info = detect_domain(question)
        logging.info(f"Domain: {domain_info['domain']}, Risk: {domain_info['risk']}")
        
        # Run multi-model audit
        logging.info("Starting multi-model audit...")
        multi_model_data = await multi_model_audit(question)
        
        if "error" in multi_model_data and "results" not in multi_model_data:
            return f"❌ Error: {multi_model_data['error']}\n\nPlease ensure API keys are configured."
        
        # Format report
        report = format_multi_model_report(question, multi_model_data, domain_info)
        
        return report
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return f"❌ System Error: {str(e)}\n\nPlease try again or contact support."

# -------------------------------------------------
# 6. HEALTH CHECK
# -------------------------------------------------
@app.get("/")
def root():
    configured_models = []
    if openai_client:
        configured_models.append("GPT-4")
    if anthropic_client:
        configured_models.append("Claude")
    if GOOGLE_API_KEY:
        configured_models.append("Gemini")
    
    return {
        "service": "AuditTrail Multi-Model",
        "version": "8.0.0",
        "status": "operational",
        "configured_models": configured_models,
        "total_models": len(configured_models)
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "openai": bool(OPENAI_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "google": bool(GOOGLE_API_KEY)
    }

# -------------------------------------------------
# 7. RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    
    print(f" AuditTrail Multi-Model v8.0")
    print(f" Endpoint: POST /audit")
    print(f" Models:")
    if openai_client:
        print("   ✓ GPT-4 (OpenAI)")
    if anthropic_client:
        print("   ✓ Claude (Anthropic)")
    if GOOGLE_API_KEY:
        print("   ✓ Gemini (Google)")
    if not any([openai_client, anthropic_client, GOOGLE_API_KEY]):
        print("    No models configured! Set API keys in .env")
    
    uvicorn.run(app, host="0.0.0.0", port=port)