import html
import json
import os
import re
from datetime import datetime
from typing import Any

import pdfplumber
import requests
import streamlit as st

# ============================================
# API CONFIGURATION - MULTI API SUPPORT
# ============================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Document limits
DOCUMENT_CHAR_LIMIT = 16000
MAX_CLAIMS = 6
MAX_SOURCES = 3
VALID_VERDICTS = {"Verified", "Inaccurate", "False", "Unverified"}
VALID_CONFIDENCE = {"High", "Medium", "Low"}
MIN_CLAIM_LENGTH = 25
MAX_CLAIM_LENGTH = 280

ANALYSIS_MODE_LABELS = {
    "gemini_live_web": "🌐 Live web fact-check (Gemini)",
    "gemini_model_only": "🤖 Model-only fallback (Gemini)",
    "anthropic_live_web": "🌐 Live web fact-check (Claude)",
    "anthropic_model_only": "🤖 Model-only fallback (Claude)",
    "local_fallback": "📝 Local fallback (No AI)",
}

# JSON Schema for fact-checking
ANALYSIS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "claim": {"type": "string"},
            "category": {"type": "string"},
            "verdict": {"type": "string"},
            "confidence": {"type": "string"},
            "explanation": {"type": "string"},
            "correct_fact": {"type": ["string", "null"]},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "claim",
            "category",
            "verdict",
            "confidence",
            "explanation",
            "correct_fact",
            "sources",
        ],
    },
}

# ============================================
# PAGE CONFIGURATION
# ============================================

st.set_page_config(
    page_title="FactCheck AI - Multi API",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #0f1117; }

.hero {
    background: linear-gradient(135deg, #112449 0%, #12335f 45%, #0d4d83 100%);
    border-radius: 20px;
    padding: 2.8rem 2rem;
    margin-bottom: 1.8rem;
    border: 1px solid #21497a;
    text-align: center;
}
.hero h1 { color: #fff; font-size: 2.55rem; font-weight: 700; margin: 0; }
.hero p  { color: #bfd4f3; font-size: 1rem; margin: 0.65rem 0 0; }

.claim-card {
    background: #1e2130;
    border-radius: 14px;
    padding: 1.25rem 1.45rem;
    margin-bottom: 1rem;
    border-left: 4px solid #334155;
}
.claim-card.verified   { border-left-color: #10b981; background: #0d2b1f; }
.claim-card.inaccurate { border-left-color: #f59e0b; background: #302109; }
.claim-card.false      { border-left-color: #ef4444; background: #310d13; }
.claim-card.unverified { border-left-color: #6366f1; background: #1a1b2e; }

.badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-verified   { background: #065f46; color: #6ee7b7; }
.badge-inaccurate { background: #78350f; color: #fcd34d; }
.badge-false      { background: #7f1d1d; color: #fca5a5; }
.badge-unverified { background: #312e81; color: #a5b4fc; }

.claim-text   { color: #e2e8f0; font-size: 0.95rem; margin: 0.4rem 0; }
.verdict-text { color: #b0bdd2; font-size: 0.86rem; margin-top: 0.5rem; }
.correct-fact { color: #34d399; font-size: 0.85rem; font-weight: 500; margin-top: 0.35rem; }
.source-link  { color: #93c5fd; font-size: 0.78rem; }

.stat-box {
    background: #1e2130;
    border-radius: 14px;
    padding: 1rem;
    text-align: center;
    border: 1px solid #2d3748;
}
.stat-num  { font-size: 2rem; font-weight: 700; }
.stat-label{ color: #94a3b8; font-size: 0.8rem; margin-top: 2px; }

.step-pill {
    display: inline-block;
    background: #1e2130;
    border: 1px solid #334155;
    border-radius: 999px;
    padding: 4px 14px;
    font-size: 0.78rem;
    color: #94a3b8;
    margin: 3px;
}

.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #8b5cf6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.75rem 2rem !important;
    font-size: 1rem !important;
}

.sidebar-box {
    background: #1e2130;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    border: 1px solid #2d3748;
}
</style>
""",
    unsafe_allow_html=True,
)

# Hero section
st.markdown(
    """
<div class="hero">
  <h1>🔍 FactCheck AI</h1>
  <p>Upload a PDF, cross-check factual claims against the live web, and get a clean verdict report.</p>
  <p style="font-size:0.85rem;margin-top:0.75rem;">✨ Supports Gemini & Claude API | Live Web Search</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style="text-align:center;margin-bottom:1.5rem;">
  <span class="step-pill">📄 1. Upload PDF</span>
  <span class="step-pill">🔑 2. Choose API</span>
  <span class="step-pill">🌐 3. Verify Claims</span>
  <span class="step-pill">📊 4. Report</span>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================
# API KEY FUNCTIONS
# ============================================

def get_gemini_key() -> str:
    """Get Gemini API key from secrets or env"""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "").strip()

def get_anthropic_key() -> str:
    """Get Anthropic API key from secrets or env"""
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("ANTHROPIC_API_KEY", "").strip()

def get_google_api_key() -> str:
    """Get Google Search API key"""
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return str(st.secrets["GOOGLE_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("GOOGLE_API_KEY", "").strip()

def get_google_cse_id() -> str:
    """Get Google CSE ID"""
    try:
        if "GOOGLE_CSE_ID" in st.secrets:
            return str(st.secrets["GOOGLE_CSE_ID"]).strip()
    except Exception:
        pass
    return os.getenv("GOOGLE_CSE_ID", "").strip()

# ============================================
# GEMINI API FUNCTIONS
# ============================================

def parse_backend_error(response: requests.Response) -> tuple[int, str, str]:
    status_code = response.status_code
    status = ""
    message = response.text.strip()

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            status = str(error.get("status") or "").strip()
            message = str(error.get("message") or message).strip()

    return status_code, status, message

def format_backend_error(response: requests.Response) -> str:
    status_code, status, message = parse_backend_error(response)
    normalized = message.lower()

    if status_code == 403 and "denied access" in normalized:
        return "Gemini access is blocked for this Google project."
    if status_code == 403:
        return "Gemini permission denied for this API key or project."
    if status_code == 429 or status == "RESOURCE_EXHAUSTED":
        return "Gemini quota or rate limit has been reached for this project."
    if status_code == 400 and status == "FAILED_PRECONDITION":
        return "Gemini is not available for this project or region in the current plan."
    return f"Gemini API error ({status_code} {status or 'UNKNOWN'}): {message}"

def gemini_generate(
    api_key: str,
    prompt: str,
    *,
    schema: dict | None = None,
    use_search: bool = False,
    temperature: float = 0.0,
) -> dict:
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    if use_search:
        body["tools"] = [{"google_search": {}}]

    if schema is not None:
        body["generationConfig"].update(
            {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            }
        )

    try:
        response = requests.post(
            GEMINI_API_URL.format(model=GEMINI_MODEL),
            headers=headers,
            json=body,
            timeout=90,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        if exc.response is not None:
            raise RuntimeError(format_backend_error(exc.response)) from exc
        raise RuntimeError(f"Gemini API error: {exc}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Gemini request failed: {exc}") from exc

    data = response.json()
    if data.get("candidates"):
        return data

    feedback = data.get("promptFeedback") or {}
    block_reason = feedback.get("blockReason")
    if block_reason:
        raise RuntimeError(f"Gemini blocked the prompt: {block_reason}")

    raise RuntimeError("Gemini returned no candidates.")

# ============================================
# ANTHROPIC (CLAUDE) API FUNCTIONS
# ============================================

def anthropic_generate(
    api_key: str,
    prompt: str,
    *,
    use_search: bool = False,
    temperature: float = 0.0,
) -> str:
    """Call Anthropic Claude API"""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    
    body = {
        "model": "claude-3-sonnet-20241022",
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    
    # Add web search tool if requested
    if use_search:
        body["tools"] = [{"type": "web_search_20250305"}]
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract text from response
        content = data.get("content", [])
        for block in content:
            if block.get("type") == "text":
                return block.get("text", "")
        return ""
    except requests.HTTPError as exc:
        if exc.response is not None:
            error_data = exc.response.json()
            error_msg = error_data.get("error", {}).get("message", str(exc))
            raise RuntimeError(f"Claude API error: {error_msg}") from exc
        raise RuntimeError(f"Claude API error: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Claude request failed: {exc}") from exc

# ============================================
# COMMON FUNCTIONS
# ============================================

def response_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = []
    for part in parts:
        text = part.get("text")
        if text:
            text_parts.append(text)
    return "\n".join(text_parts).strip()

def parse_json_text(text: str) -> Any:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Empty model response.")
    # Extract JSON if wrapped in markdown
    json_match = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(1)
    return json.loads(cleaned)

def extract_text_from_pdf(uploaded_file) -> str:
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)

def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" -\t\r") for part in parts if part and part.strip()]

def infer_claim_category(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(?:19|20)\d{2}\b|\bjan(?:uary)?\b|\bfeb(?:ruary)?\b|\bmar(?:ch)?\b|\bapr(?:il)?\b|\bmay\b|\bjun(?:e)?\b|\bjul(?:y)?\b|\baug(?:ust)?\b|\bsep(?:tember)?\b|\boct(?:ober)?\b|\bnov(?:ember)?\b|\bdec(?:ember)?\b", lowered):
        return "date"
    if re.search(r"[$€£₹]|\b(?:usd|inr|eur|gbp|crore|lakh|million|billion|revenue|profit|income|funding|market cap)\b", lowered):
        return "financial"
    if re.search(r"\b(?:version|api|model|release|technical|spec)\b", lowered):
        return "technical"
    if re.search(r"\b(?:study|survey|research|paper|experiment|trial)\b", lowered):
        return "research"
    if re.search(r"\d|%|\b(?:percent|percentage|users|people|population|growth)\b", lowered):
        return "statistic"
    return "other"

def looks_like_claim(text: str) -> bool:
    cleaned = " ".join(text.split())
    if len(cleaned) < MIN_CLAIM_LENGTH or len(cleaned) > MAX_CLAIM_LENGTH:
        return False
    if not re.search(
        r"\d|%|[$€£₹]|\b(?:million|billion|crore|lakh|version|study|survey|research|users|people|founded|released|launched|grew|increased|decreased)\b",
        cleaned,
        flags=re.IGNORECASE,
    ):
        return False
    if cleaned.endswith(":"):
        return False
    return True

def extract_claims_locally(text: str) -> list[dict]:
    claims = []
    seen_claims = set()

    for sentence in split_sentences(text):
        candidate = " ".join(sentence.split())
        if not looks_like_claim(candidate):
            continue

        claim_key = candidate.casefold()
        if claim_key in seen_claims:
            continue
        seen_claims.add(claim_key)

        claims.append(
            {
                "id": len(claims) + 1,
                "claim": candidate,
                "category": infer_claim_category(candidate),
            }
        )

        if len(claims) >= MAX_CLAIMS:
            break

    return claims

def normalize_verdict(value: Any) -> str:
    verdict = str(value or "Unverified").strip().title()
    mapping = {
        "True": "Verified",
        "Mostly True": "Inaccurate",
        "Partly True": "Inaccurate",
        "Partial": "Inaccurate",
        "Partially True": "Inaccurate",
        "Misleading": "Inaccurate",
        "Incorrect": "False",
    }
    verdict = mapping.get(verdict, verdict)
    if verdict not in VALID_VERDICTS:
        verdict = "Unverified"
    return verdict

def normalize_confidence(value: Any) -> str:
    confidence = str(value or "Low").strip().title()
    if confidence not in VALID_CONFIDENCE:
        confidence = "Low"
    return confidence

def normalize_analysis_results(payload: Any) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError("Analysis did not return a JSON array.")

    results = []
    seen_claims = set()

    for item in payload:
        if not isinstance(item, dict):
            continue

        claim_text = str(item.get("claim", "")).strip()
        if not claim_text:
            continue

        claim_key = claim_text.casefold()
        if claim_key in seen_claims:
            continue
        seen_claims.add(claim_key)

        verdict = normalize_verdict(item.get("verdict"))
        confidence = normalize_confidence(item.get("confidence"))
        explanation = str(item.get("explanation", "")).strip() or "No explanation returned."
        category = str(item.get("category", "other")).strip().lower() or "other"

        correct_fact = item.get("correct_fact")
        if correct_fact is not None:
            correct_fact = str(correct_fact).strip() or None

        sources = item.get("sources", [])
        if isinstance(sources, str):
            sources = [sources]
        if not isinstance(sources, list):
            sources = []

        cleaned_sources = []
        seen_sources = set()
        for source in sources:
            source_text = str(source).strip()
            if not source_text:
                continue
            source_key = source_text.casefold()
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            cleaned_sources.append(source_text)
            if len(cleaned_sources) >= MAX_SOURCES:
                break

        results.append(
            {
                "id": len(results) + 1,
                "claim": claim_text,
                "category": category,
                "verdict": verdict,
                "confidence": confidence,
                "explanation": explanation,
                "correct_fact": correct_fact,
                "sources": cleaned_sources,
            }
        )

        if len(results) >= MAX_CLAIMS:
            break

    if not results:
        raise ValueError("No claim analysis results were returned.")

    return results

def build_unverified_results(claims: list[dict], reason: str) -> list[dict]:
    results = []
    for claim in claims:
        results.append(
            {
                "id": claim["id"],
                "claim": claim["claim"],
                "category": claim["category"],
                "verdict": "Unverified",
                "confidence": "Low",
                "explanation": reason,
                "correct_fact": None,
                "sources": [],
            }
        )
    return results

# ============================================
# GEMINI ANALYSIS FUNCTIONS
# ============================================

def analyze_with_gemini_live(api_key: str, text: str) -> list[dict]:
    prompt = f"""You are a fact-checking web agent for uploaded PDFs.

Your job is to:
1. Extract up to {MAX_CLAIMS} explicit factual claims from the document that are worth checking on the public web.
2. Use live Google Search results to verify each claim against current information.
3. Return one JSON array only.

For each item return:
- claim
- category
- verdict
- confidence
- explanation
- correct_fact
- sources

Use these exact verdict labels:
- Verified = the claim matches current public evidence
- Inaccurate = the claim is outdated, incomplete, or numerically off
- False = reliable public evidence contradicts the claim or there is no credible support
- Unverified = the claim is private, resume-style, or not publicly provable

Rules:
- prioritize stats, dates, financial figures, technical details, rankings, company facts
- prefer official, primary, or highly authoritative sources
- include 1 to {MAX_SOURCES} short source labels or URLs when available
- if a claim is wrong or outdated, include the corrected real fact in correct_fact
- do not return more than {MAX_CLAIMS} claims

DOCUMENT:
{text[:DOCUMENT_CHAR_LIMIT]}
"""
    data = gemini_generate(api_key, prompt, schema=ANALYSIS_SCHEMA, use_search=True, temperature=0.0)
    return normalize_analysis_results(parse_json_text(response_text(data)))

def analyze_with_gemini_model_only(api_key: str, text: str) -> list[dict]:
    prompt = f"""You are a document analysis assistant.

Read the uploaded PDF text and extract up to {MAX_CLAIMS} explicit factual claims worth reviewing.
For each claim:
- assign a short category
- assign one verdict using exactly one of these labels: Verified, Inaccurate, False, or Unverified
- assign one confidence: High, Medium, or Low
- write a short explanation
- include a corrected fact when the claim is wrong or outdated, otherwise null
- include a short list of sources only when you are highly confident; otherwise use []

Important rules:
- analyze only claims that actually appear in the document
- use your general model knowledge and the uploaded document
- do not use live web search in this fallback mode
- if you are unsure, prefer Unverified
- do not return more than {MAX_CLAIMS} items

DOCUMENT:
{text[:DOCUMENT_CHAR_LIMIT]}
"""
    data = gemini_generate(api_key, prompt, schema=ANALYSIS_SCHEMA, temperature=0.0)
    return normalize_analysis_results(parse_json_text(response_text(data)))

# ============================================
# ANTHROPIC (CLAUDE) ANALYSIS FUNCTIONS
# ============================================

def analyze_with_claude_live(api_key: str, text: str) -> list[dict]:
    prompt = f"""You are a fact-checking web agent for uploaded PDFs.

Your job is to:
1. Extract up to {MAX_CLAIMS} explicit factual claims from the document that are worth checking on the public web.
2. Use live web search to verify each claim against current information.
3. Return one JSON array only.

For each item return:
- claim
- category
- verdict
- confidence
- explanation
- correct_fact
- sources

Use these exact verdict labels:
- Verified = the claim matches current public evidence
- Inaccurate = the claim is outdated, incomplete, or numerically off
- False = reliable public evidence contradicts the claim or there is no credible support
- Unverified = the claim is private, resume-style, or not publicly provable

Rules:
- prioritize stats, dates, financial figures, technical details, rankings, company facts
- prefer official, primary, or highly authoritative sources
- include 1 to {MAX_SOURCES} short source labels or URLs when available
- if a claim is wrong or outdated, include the corrected real fact in correct_fact
- do not return more than {MAX_CLAIMS} claims

Return ONLY valid JSON array. Do not include any other text.

DOCUMENT:
{text[:DOCUMENT_CHAR_LIMIT]}
"""
    response_text_content = anthropic_generate(api_key, prompt, use_search=True, temperature=0.0)
    return normalize_analysis_results(parse_json_text(response_text_content))

def analyze_with_claude_model_only(api_key: str, text: str) -> list[dict]:
    prompt = f"""You are a document analysis assistant.

Read the uploaded PDF text and extract up to {MAX_CLAIMS} explicit factual claims worth reviewing.
For each claim:
- assign a short category
- assign one verdict using exactly one of these labels: Verified, Inaccurate, False, or Unverified
- assign one confidence: High, Medium, or Low
- write a short explanation
- include a corrected fact when the claim is wrong or outdated, otherwise null
- include a short list of sources only when you are highly confident; otherwise use []

Important rules:
- analyze only claims that actually appear in the document
- use your general model knowledge and the uploaded document
- do not use live web search in this fallback mode
- if you are unsure, prefer Unverified
- do not return more than {MAX_CLAIMS} items

Return ONLY valid JSON array. Do not include any other text.

DOCUMENT:
{text[:DOCUMENT_CHAR_LIMIT]}
"""
    response_text_content = anthropic_generate(api_key, prompt, use_search=False, temperature=0.0)
    return normalize_analysis_results(parse_json_text(response_text_content))

# ============================================
# UI FUNCTIONS
# ============================================

def badge_html(verdict: str) -> str:
    mapping = {
        "Verified": ("verified", "✅ Verified"),
        "Inaccurate": ("inaccurate", "⚠️ Inaccurate"),
        "False": ("false", "❌ False"),
        "Unverified": ("unverified", "❓ Unverified"),
    }
    cls, label = mapping.get(verdict, ("unverified", verdict))
    return f'<span class="badge badge-{cls}">{label}</span>'

def render_claim_card(result: dict) -> None:
    verdict = result.get("verdict", "Unverified")
    card_cls = {
        "Verified": "verified",
        "Inaccurate": "inaccurate",
        "False": "false",
        "Unverified": "unverified",
    }.get(verdict, "unverified")

    claim_text = html.escape(str(result.get("claim", "")).strip())
    explanation = html.escape(str(result.get("explanation", "")).strip())
    confidence = str(result.get("confidence", "?")).strip().title()
    category = html.escape(str(result.get("category", "")).strip().upper())
    claim_id = html.escape(str(result.get("id", "")).strip())

    correct_html = ""
    if result.get("correct_fact"):
        correct_fact = html.escape(str(result["correct_fact"]).strip())
        correct_html = f"<p class=\"correct-fact\">✅ Correct fact: {correct_fact}</p>"

    sources_html = ""
    if result.get("sources"):
        source_tags = []
        for source in result["sources"][:MAX_SOURCES]:
            source_tags.append(f"<span class=\"source-link\">{html.escape(str(source))}</span>")
        sources_html = f"<p style=\"margin-top:0.4rem;\">{' · '.join(source_tags)}</p>"

    conf_color = {
        "High": "#10b981",
        "Medium": "#f59e0b",
        "Low": "#ef4444",
    }.get(confidence, "#94a3b8")

    st.markdown(
        f"""
    <div class="claim-card {card_cls}">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
        {badge_html(verdict)}
        <span style="font-size:0.75rem;color:{conf_color};font-weight:600;">
          {html.escape(confidence)} confidence &nbsp;·&nbsp; #{claim_id} &nbsp;·&nbsp; {category}
        </span>
      </div>
      <p class="claim-text">"{claim_text}"</p>
      <p class="verdict-text">{explanation}</p>
      {correct_html}
      {sources_html}
    </div>
    """,
        unsafe_allow_html=True,
    )

# ============================================
# MAIN APP
# ============================================

# Sidebar for API Configuration
with st.sidebar:
    st.markdown('<div class="sidebar-box">', unsafe_allow_html=True)
    st.markdown("### 🔑 API Configuration")
    
    # API Provider Selection
    api_provider = st.selectbox(
        "Select AI Provider",
        ["Gemini (Google)", "Anthropic (Claude)"],
        help="Gemini is free with limitations. Claude has better web search."
    )
    
    st.markdown("---")
    
    # Gemini API Key
    if api_provider == "Gemini (Google)":
        gemini_key = get_gemini_key()
        if not gemini_key:
            gemini_key = st.text_input(
                "🔐 Gemini API Key",
                type="password",
                help="Get from https://aistudio.google.com/app/apikey"
            )
        if gemini_key:
            st.success("✅ Gemini API key configured")
        else:
            st.warning("⚠️ Please enter Gemini API key")
    
    # Anthropic API Key
    else:
        anthropic_key = get_anthropic_key()
        if not anthropic_key:
            anthropic_key = st.text_input(
                "🔐 Anthropic API Key",
                type="password",
                help="Get from https://console.anthropic.com/"
            )
        if anthropic_key:
            st.success("✅ Anthropic API key configured")
        else:
            st.warning("⚠️ Please enter Anthropic API key")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Optional Google Search API (Backup)
    st.markdown('<div class="sidebar-box">', unsafe_allow_html=True)
    st.markdown("### 🔍 Optional: Google Search API")
    st.caption("Better fact-checking results with custom search")
    
    use_google_backup = st.checkbox("Enable Google Search backup", value=False)
    if use_google_backup:
        google_key = get_google_api_key()
        if not google_key:
            google_key = st.text_input("Google API Key", type="password")
        
        google_cse = get_google_cse_id()
        if not google_cse:
            google_cse = st.text_input("Google CSE ID")
        
        if google_key and google_cse:
            st.success("✅ Google Search configured")
        else:
            st.info("Get from https://programmablesearchengine.google.com/")
    st.markdown('</div>', unsafe_allow_html=True)

# Main area
col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader("📄 Upload PDF", type=["pdf"])

with col_info:
    st.markdown(
        f"""
    <div class="stat-box" style="margin-bottom:0.8rem;">
      <div class="stat-num" style="color:#6366f1;">4</div>
      <div class="stat-label">Simple Steps</div>
    </div>
    <div style="background:#1e2130;border-radius:10px;padding:1rem;border:1px solid #2d3748;font-size:0.82rem;color:#94a3b8;">
      <b style="color:#e2e8f0;">Features</b><br><br>
      ✅ Multi-API Support (Gemini + Claude)<br>
      ✅ Live Web Fact-Checking<br>
      ✅ PDF Text Extraction<br>
      ✅ JSON Report Export<br><br>
      <span style="color:#cbd5e1;">Current: {api_provider}</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

run = st.button("🚀 Analyze PDF", use_container_width=True)

if run:
    if not uploaded_file:
        st.error("Please upload a PDF file.")
        st.stop()
    
    # Check API key based on provider
    if api_provider == "Gemini (Google)":
        if 'gemini_key' not in locals() or not gemini_key:
            st.error("Please enter your Gemini API key in the sidebar.")
            st.stop()
        api_key = gemini_key
    else:
        if 'anthropic_key' not in locals() or not anthropic_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            st.stop()
        api_key = anthropic_key
    
    with st.spinner("📄 Extracting text from PDF..."):
        try:
            pdf_text = extract_text_from_pdf(uploaded_file)
        except Exception as exc:
            st.error(f"PDF read error: {exc}")
            st.stop()
    
    if not pdf_text.strip():
        st.error("No text found in PDF. Try a text-based PDF.")
        st.stop()
    
    st.success(f"✅ Extracted {len(pdf_text):,} characters from PDF")
    
    analysis_mode = "local_fallback"
    analysis_error = None
    
    # Analyze based on selected provider
    if api_provider == "Gemini (Google)":
        with st.spinner("🌐 Fact-checking with Gemini + Live Web Search..."):
            try:
                results = analyze_with_gemini_live(api_key, pdf_text)
                analysis_mode = "gemini_live_web"
            except Exception as exc:
                analysis_error = str(exc)
        
        if analysis_error:
            with st.spinner("🤖 Falling back to Gemini model-only analysis..."):
                try:
                    results = analyze_with_gemini_model_only(api_key, pdf_text)
                    analysis_mode = "gemini_model_only"
                except Exception as exc:
                    analysis_error = str(exc)
                    local_claims = extract_claims_locally(pdf_text)
                    if not local_claims:
                        st.error(f"Analysis failed: {analysis_error}")
                        st.stop()
                    results = build_unverified_results(
                        local_claims,
                        f"AI analysis unavailable: {analysis_error}",
                    )
    else:
        # Anthropic (Claude)
        with st.spinner("🌐 Fact-checking with Claude + Live Web Search..."):
            try:
                results = analyze_with_claude_live(api_key, pdf_text)
                analysis_mode = "anthropic_live_web"
            except Exception as exc:
                analysis_error = str(exc)
        
        if analysis_error:
            with st.spinner("🤖 Falling back to Claude model-only analysis..."):
                try:
                    results = analyze_with_claude_model_only(api_key, pdf_text)
                    analysis_mode = "anthropic_model_only"
                except Exception as exc:
                    analysis_error = str(exc)
                    local_claims = extract_claims_locally(pdf_text)
                    if not local_claims:
                        st.error(f"Analysis failed: {analysis_error}")
                        st.stop()
                    results = build_unverified_results(
                        local_claims,
                        f"AI analysis unavailable: {analysis_error}",
                    )
    
    # Show mode info
    if analysis_mode in ["gemini_live_web", "anthropic_live_web"]:
        st.info(
            f"🎯 Live web fact-check completed for **{len(results)}** claims using {api_provider}. "
            "Best for public stats, dates, and factual claims."
        )
    elif analysis_mode in ["gemini_model_only", "anthropic_model_only"]:
        st.warning(
            f"Live web fact-checking was unavailable, using {api_provider} fallback mode. "
            "Public claims may still be useful, but less accurate than live web verification."
        )
        if analysis_error:
            st.caption(f"Fallback reason: {analysis_error}")
    else:
        st.warning(
            "AI analysis unavailable, using local fallback. "
            "Claims extracted but marked unverified."
        )
        if analysis_error:
            st.caption(f"Fallback reason: {analysis_error}")
    
    # Display results
    st.markdown("---")
    st.markdown("## 📊 Analysis Report")
    st.caption(f"Mode: {ANALYSIS_MODE_LABELS.get(analysis_mode, analysis_mode)}")
    st.markdown(f"*Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*")
    
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for result in results:
        verdict = result.get("verdict", "Unverified")
        if verdict not in counts:
            verdict = "Unverified"
        counts[verdict] += 1
    
    c1, c2, c3, c4 = st.columns(4)
    for col, (label, color, icon) in zip(
        [c1, c2, c3, c4],
        [
            ("Verified", "#10b981", "✅"),
            ("Inaccurate", "#f59e0b", "⚠️"),
            ("False", "#ef4444", "❌"),
            ("Unverified", "#6366f1", "❓"),
        ],
    ):
        with col:
            st.markdown(
                f"""
            <div class="stat-box">
              <div class="stat-num" style="color:{color};">{icon} {counts[label]}</div>
              <div class="stat-label">{label}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
    
    st.markdown("### 🔎 Detailed Results")
    tabs = st.tabs(["All Claims", "✅ Verified", "⚠️ Inaccurate", "❌ False", "❓ Unverified"])
    groups = {
        "All Claims": results,
        "✅ Verified": [item for item in results if item["verdict"] == "Verified"],
        "⚠️ Inaccurate": [item for item in results if item["verdict"] == "Inaccurate"],
        "❌ False": [item for item in results if item["verdict"] == "False"],
        "❓ Unverified": [item for item in results if item["verdict"] == "Unverified"],
    }
    
    for tab, (_, items) in zip(tabs, groups.items()):
        with tab:
            if not items:
                st.info("No claims in this category.")
            for item in items:
                render_claim_card(item)
    
    report_json = json.dumps(
        {
            "generated_at": datetime.now().isoformat(),
            "api_provider": api_provider,
            "mode": analysis_mode,
            "error": analysis_error,
            "summary": counts,
            "results": results,
        },
        indent=2,
        ensure_ascii=False,
    )
    st.download_button(
        "⬇️ Download Report (JSON)",
        data=report_json,
        file_name="factcheck_report.json",
        mime="application/json",
    )
