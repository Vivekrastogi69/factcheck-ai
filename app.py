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
# API CONFIGURATION
# ============================================

# Fixed: Correct Gemini model name
GEMINI_MODEL = "gemini-2.0-flash-exp"
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
    "gemini_live_web": "🌐 Live web fact-check (Gemini + Serper)",
    "gemini_model_only": "🤖 Model-only fallback (Gemini)",
    "serper_fallback": "🔍 Serper Web Search Fallback",
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
    page_title="FactCheck AI - Truth Layer",
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
    padding: 2.5rem 2rem;
    margin-bottom: 1.8rem;
    border: 1px solid #21497a;
    text-align: center;
}
.hero h1 { color: #fff; font-size: 2.3rem; font-weight: 700; margin: 0; }
.hero p  { color: #bfd4f3; font-size: 0.95rem; margin: 0.65rem 0 0; }

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
  <h1>🔍 FactCheck AI — Truth Layer</h1>
  <p>Upload a PDF, cross-check factual claims against the live web, and get a clean verdict report.</p>
  <p style="font-size:0.85rem;margin-top:0.75rem;">✨ Powered by Gemini AI + Serper Web Search</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style="text-align:center;margin-bottom:1.5rem;">
  <span class="step-pill">📄 1. Upload PDF</span>
  <span class="step-pill">🔑 2. API Keys Ready</span>
  <span class="step-pill">🌐 3. Verify Claims</span>
  <span class="step-pill">📊 4. Report</span>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================
# API KEY FUNCTIONS (Private via Secrets)
# ============================================

def get_gemini_key() -> str:
    """Get Gemini API key from secrets"""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "").strip()

def get_serper_key() -> str:
    """Get Serper API key from secrets"""
    try:
        if "SERPER_API_KEY" in st.secrets:
            return str(st.secrets["SERPER_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("SERPER_API_KEY", "").strip()

# ============================================
# SERPER WEB SEARCH FUNCTION
# ============================================

def serper_web_search(query: str, api_key: str) -> str:
    """Search using Serper.dev Google Search API"""
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": 5,
        "gl": "in",  # Country: India
        "hl": "en"   # Language: English
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        snippets = []
        
        # Get organic results
        for result in data.get("organic", [])[:5]:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if snippet:
                snippets.append(f"{title}: {snippet}")
        
        # Get knowledge graph if available
        knowledge = data.get("knowledgeGraph")
        if knowledge:
            description = knowledge.get("description")
            if description:
                snippets.append(f"[Knowledge Graph] {description}")
        
        if snippets:
            return "\n\n".join(snippets[:5])
        return "No search results found for this query."
        
    except requests.exceptions.RequestException as e:
        return f"Search error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

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
        return "Gemini access blocked. Enable billing or check permissions."
    if status_code == 403:
        return "Gemini permission denied. Check your API key."
    if status_code == 429 or status == "RESOURCE_EXHAUSTED":
        return "Gemini quota exceeded. Try again later or enable billing."
    if status_code == 404:
        return "Gemini model not found. Please check API key and model name."
    if status_code == 400 and "location" in normalized:
        return "Gemini not available in your region. Use VPN or enable billing."
    return f"Gemini API error ({status_code}): {message[:200]}"

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
    if re.search(r"\b(?:19|20)\d{2}\b", lowered):
        return "date"
    if re.search(r"[$€£₹]|\b(?:usd|inr|eur|gbp|crore|lakh|million|billion|revenue|profit)\b", lowered):
        return "financial"
    if re.search(r"\b(?:version|api|model|release|technical)\b", lowered):
        return "technical"
    if re.search(r"\b(?:study|survey|research|paper|experiment)\b", lowered):
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
# ANALYSIS WITH SERPER + GEMINI
# ============================================

def analyze_with_serper_and_gemini(gemini_key: str, serper_key: str, text: str) -> list[dict]:
    """First use Serper to search, then Gemini to analyze with search results"""
    
    # Step 1: Extract claims locally first
    local_claims = extract_claims_locally(text)
    if not local_claims:
        raise ValueError("No claims found in document")
    
    # Step 2: For each claim, search with Serper
    claim_analysis_results = []
    
    for claim_item in local_claims[:MAX_CLAIMS]:
        claim_text = claim_item["claim"]
        
        # Search the web for this claim
        search_results = serper_web_search(claim_text, serper_key)
        
        # Step 3: Use Gemini to verify claim with search results
        verification_prompt = f"""You are a fact-checking expert. Analyze this claim using the provided search results.

Claim: "{claim_text}"

Search Results:
{search_results}

Based ONLY on the search results above, determine if this claim is:
- Verified: The search results CONFIRM the claim is accurate
- Inaccurate: The claim is outdated, partially wrong, or numbers are off
- False: The search results CONTRADICT the claim
- Unverified: The search results don't provide enough information

Respond with a JSON object:
{{
    "claim": "{claim_text}",
    "category": "{claim_item['category']}",
    "verdict": "Verified/Inaccurate/False/Unverified",
    "confidence": "High/Medium/Low",
    "explanation": "Brief explanation based on search results",
    "correct_fact": "Correct fact if claim is wrong, otherwise null",
    "sources": ["source1", "source2"]
}}

Do not include any other text, only the JSON object."""

        try:
            data = gemini_generate(gemini_key, verification_prompt, schema=ANALYSIS_SCHEMA, temperature=0.0)
            result_text = response_text(data)
            parsed = parse_json_text(result_text)
            
            # Handle single object or array
            if isinstance(parsed, dict):
                claim_analysis_results.append(parsed)
            elif isinstance(parsed, list) and len(parsed) > 0:
                claim_analysis_results.append(parsed[0])
            else:
                raise ValueError("Invalid response format")
                
        except Exception as e:
            # Fallback: mark as unverified
            claim_analysis_results.append({
                "claim": claim_text,
                "category": claim_item["category"],
                "verdict": "Unverified",
                "confidence": "Low",
                "explanation": f"Verification failed: {str(e)[:100]}",
                "correct_fact": None,
                "sources": []
            })
    
    return normalize_analysis_results(claim_analysis_results)

def analyze_with_gemini_live(api_key: str, text: str) -> list[dict]:
    """Use Gemini's built-in Google Search"""
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
    """Use Gemini without web search"""
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
    
    # API status
    gemini_key = get_gemini_key()
    serper_key = get_serper_key()
    
    if gemini_key:
        st.success("✅ Gemini API key configured")
    else:
        st.error("❌ Gemini API key missing - Add to secrets")
    
    if serper_key:
        st.success("✅ Serper API key configured")
    else:
        st.warning("⚠️ Serper API key missing - Add for better search")
    
    st.markdown("---")
    st.markdown("### 🔍 Search Mode")
    
    # Search mode selection
    if serper_key and gemini_key:
        search_mode = st.radio(
            "Select verification method",
            ["🚀 Gemini + Built-in Search (Recommended)", "🔎 Gemini + Serper Search (Alternative)"],
            help="Built-in search uses Gemini's native Google Search. Serper is an alternative."
        )
    elif serper_key:
        search_mode = "🔎 Gemini + Serper Search (Alternative)"
        st.info("Using Serper search mode")
    else:
        search_mode = "🚀 Gemini + Built-in Search (Recommended)"
        st.info("Using Gemini built-in search")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Info box
    st.markdown('<div class="sidebar-box">', unsafe_allow_html=True)
    st.markdown("### 📊 FactCheck Features")
    st.markdown("""
    - ✅ **Verified** - Matches current evidence
    - ⚠️ **Inaccurate** - Outdated or off by numbers
    - ❌ **False** - Contradicted by evidence
    - ❓ **Unverified** - Not publicly provable
    """)
    st.markdown("---")
    st.markdown("### 🎯 Trap Document Ready")
    st.markdown("Upload a PDF with intentional lies or outdated stats. The system will flag them!")
    st.markdown('</div>', unsafe_allow_html=True)

# Main area
col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader("📄 Upload PDF", type=["pdf"], help="Upload any PDF with factual claims, stats, or dates")

with col_info:
    st.markdown(
        """
    <div class="stat-box" style="margin-bottom:0.8rem;">
      <div class="stat-num" style="color:#6366f1;">4</div>
      <div class="stat-label">Simple Steps</div>
    </div>
    <div style="background:#1e2130;border-radius:10px;padding:1rem;border:1px solid #2d3748;font-size:0.82rem;color:#94a3b8;">
      <b style="color:#e2e8f0;">How it works</b><br><br>
      1️⃣ Upload PDF with claims<br>
      2️⃣ System extracts facts & stats<br>
      3️⃣ Live web search verification<br>
      4️⃣ Get verdict with corrections<br><br>
      <span style="color:#10b981;">✨ Detects outdated & false claims</span><br>
      <span style="color:#f59e0b;">⚠️ Flags inaccurate statistics</span><br>
      <span style="color:#ef4444;">❌ Identifies fabricated facts</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

run = st.button("🚀 Analyze PDF", use_container_width=True, type="primary")

if run:
    if not uploaded_file:
        st.error("Please upload a PDF file first.")
        st.stop()
    
    # Check Gemini API key
    gemini_key = get_gemini_key()
    if not gemini_key:
        st.error("❌ Gemini API key not configured. Please add GEMINI_API_KEY to Streamlit secrets.")
        st.stop()
    
    with st.spinner("📄 Extracting text from PDF..."):
        try:
            pdf_text = extract_text_from_pdf(uploaded_file)
        except Exception as exc:
            st.error(f"PDF read error: {exc}")
            st.stop()
    
    if not pdf_text.strip():
        st.error("No text found in PDF. Please upload a text-based PDF (not scanned image).")
        st.stop()
    
    st.success(f"✅ Extracted {len(pdf_text):,} characters from PDF")
    
    analysis_mode = "local_fallback"
    analysis_error = None
    results = []
    
    # Choose analysis method based on selection
    use_serper = "Serper" in search_mode if 'search_mode' in dir() else False
    
    if use_serper and get_serper_key():
        with st.spinner("🔎 Searching web with Serper API and verifying claims..."):
            try:
                results = analyze_with_serper_and_gemini(gemini_key, get_serper_key(), pdf_text)
                analysis_mode = "serper_fallback"
            except Exception as exc:
                analysis_error = str(exc)
                st.warning(f"Serper mode failed: {analysis_error[:200]}")
    
    if not results:
        # Try Gemini built-in search
        with st.spinner("🌐 Fact-checking with Gemini + Live Web Search..."):
            try:
                results = analyze_with_gemini_live(gemini_key, pdf_text)
                analysis_mode = "gemini_live_web"
            except Exception as exc:
                analysis_error = str(exc)
        
        if not results and analysis_error:
            # Fallback to model-only
            with st.spinner("🤖 Falling back to Gemini model-only analysis..."):
                try:
                    results = analyze_with_gemini_model_only(gemini_key, pdf_text)
                    analysis_mode = "gemini_model_only"
                except Exception as exc:
                    analysis_error = str(exc)
                    local_claims = extract_claims_locally(pdf_text)
                    if not local_claims:
                        st.error(f"Analysis failed: {analysis_error}")
                        st.stop()
                    results = build_unverified_results(
                        local_claims,
                        f"AI analysis unavailable: {analysis_error[:200]}",
                    )
    
    # Show mode info
    if analysis_mode == "gemini_live_web":
        st.success(f"🎯 Live web fact-check completed for **{len(results)}** claims using Gemini + Google Search!")
    elif analysis_mode == "serper_fallback":
        st.success(f"🎯 Web fact-check completed for **{len(results)}** claims using Serper + Gemini!")
    elif analysis_mode == "gemini_model_only":
        st.warning(f"⚠️ Using Gemini fallback mode (no live web search) for {len(results)} claims")
        if analysis_error:
            st.caption(f"Live-web error: {analysis_error[:150]}")
    else:
        st.warning(f"📝 Using local fallback mode for {len(results)} claims (AI unavailable)")
        if analysis_error:
            st.caption(f"Error: {analysis_error[:150]}")
    
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
    
    # Download button
    report_json = json.dumps(
        {
            "generated_at": datetime.now().isoformat(),
            "file_name": uploaded_file.name if uploaded_file else "unknown",
            "mode": analysis_mode,
            "error": analysis_error if analysis_error else None,
            "summary": counts,
            "total_claims": len(results),
            "results": results,
        },
        indent=2,
        ensure_ascii=False,
    )
    st.download_button(
        "⬇️ Download Full Report (JSON)",
        data=report_json,
        file_name=f"factcheck_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )
