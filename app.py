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
# GROQ API CONFIGURATION - ONLY GROQ
# ============================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Document limits
DOCUMENT_CHAR_LIMIT = 12000
MAX_CLAIMS = 6
MAX_SOURCES = 3
VALID_VERDICTS = {"Verified", "Inaccurate", "False", "Unverified"}
VALID_CONFIDENCE = {"High", "Medium", "Low"}
MIN_CLAIM_LENGTH = 25
MAX_CLAIM_LENGTH = 280

ANALYSIS_MODE_LABELS = {
    "groq_web_search": "🌐 Live web fact-check (Groq + Serper)",
    "groq_model_only": "🤖 Model-only analysis (Groq)",
    "local_fallback": "📝 Local fallback (No AI)",
}

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
        "required": ["claim", "category", "verdict", "confidence", "explanation", "correct_fact", "sources"],
    },
}

# ============================================
# PAGE CONFIGURATION
# ============================================

st.set_page_config(
    page_title="FactCheck AI - Groq Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #0f1117; }
.hero {
    background: linear-gradient(135deg, #0a0a2a 0%, #1a1a4a 45%, #2a2a5a 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    margin-bottom: 1.8rem;
    border: 1px solid #4a4a8a;
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
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
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

st.markdown(
    """
<div class="hero">
  <h1>⚡ FactCheck AI — Groq Edition</h1>
  <p>Upload a PDF, cross-check factual claims against the live web, and get a clean verdict report.</p>
  <p style="font-size:0.85rem;margin-top:0.75rem;">✨ Powered by Groq LPU (Ultra-Fast Inference)</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style="text-align:center;margin-bottom:1.5rem;">
  <span class="step-pill">📄 1. Upload PDF</span>
  <span class="step-pill">⚡ 2. Groq AI</span>
  <span class="step-pill">🌐 3. Verify Claims</span>
  <span class="step-pill">📊 4. Report</span>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================
# API KEY FUNCTIONS
# ============================================

def get_groq_key() -> str:
    """Get Groq API key from secrets"""
    try:
        if "GROQ_API_KEY" in st.secrets:
            return str(st.secrets["GROQ_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "").strip()

def get_serper_key() -> str:
    """Get Serper API key from secrets"""
    try:
        if "SERPER_API_KEY" in st.secrets:
            return str(st.secrets["SERPER_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("SERPER_API_KEY", "").strip()

# ============================================
# SERPER WEB SEARCH
# ============================================

def serper_web_search(query: str, api_key: str) -> str:
    if not api_key:
        return ""
    
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 3}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        snippets = [r.get("snippet", "") for r in data.get("organic", [])[:3] if r.get("snippet")]
        return "\n\n".join(snippets) if snippets else ""
    except Exception:
        return ""

# ============================================
# GROQ API FUNCTIONS
# ============================================

def groq_generate(api_key: str, prompt: str, temperature: float = 0.0) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 4096,
    }
    
    response = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=60)
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Empty response from Groq API")
    return content

def parse_json_text(text: str):
    cleaned = text.strip()
    json_match = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(1)
    if cleaned.startswith('[') or cleaned.startswith('{'):
        return json.loads(cleaned)
    json_match2 = re.search(r'(\[.*\]|\{.*\})', cleaned, re.DOTALL)
    if json_match2:
        return json.loads(json_match2.group(1))
    raise ValueError("Could not parse JSON")

def extract_text_from_pdf(uploaded_file) -> str:
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)

def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]

def infer_claim_category(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(?:19|20)\d{2}\b", lowered):
        return "date"
    if re.search(r"[$€£₹]|\b(?:million|billion|crore)\b", lowered):
        return "financial"
    if re.search(r"\b(?:version|api|model|technical)\b", lowered):
        return "technical"
    if re.search(r"\b(?:study|survey|research)\b", lowered):
        return "research"
    if re.search(r"\d|%", lowered):
        return "statistic"
    return "other"

def looks_like_claim(text: str) -> bool:
    cleaned = " ".join(text.split())
    if len(cleaned) < MIN_CLAIM_LENGTH or len(cleaned) > MAX_CLAIM_LENGTH:
        return False
    if not re.search(r"\d|%|[$€£₹]|\b(?:million|billion|crore|version|study|research)\b", cleaned, re.IGNORECASE):
        return False
    return True

def extract_claims_locally(text: str) -> list[dict]:
    claims = []
    seen = set()
    for sentence in split_sentences(text):
        candidate = " ".join(sentence.split())
        if not looks_like_claim(candidate) or candidate.casefold() in seen:
            continue
        seen.add(candidate.casefold())
        claims.append({"id": len(claims)+1, "claim": candidate, "category": infer_claim_category(candidate)})
        if len(claims) >= MAX_CLAIMS:
            break
    return claims

def normalize_verdict(value) -> str:
    verdict = str(value or "Unverified").strip().title()
    mapping = {"True": "Verified", "Mostly True": "Inaccurate", "Partly True": "Inaccurate", "Misleading": "Inaccurate", "Incorrect": "False"}
    verdict = mapping.get(verdict, verdict)
    return verdict if verdict in VALID_VERDICTS else "Unverified"

def normalize_confidence(value) -> str:
    conf = str(value or "Low").strip().title()
    return conf if conf in VALID_CONFIDENCE else "Low"

def normalize_analysis_results(payload) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError("Expected JSON array")
    results = []
    seen = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        claim_text = str(item.get("claim", "")).strip()
        if not claim_text or claim_text.casefold() in seen:
            continue
        seen.add(claim_text.casefold())
        results.append({
            "id": len(results)+1,
            "claim": claim_text,
            "category": str(item.get("category", "other")).strip().lower(),
            "verdict": normalize_verdict(item.get("verdict")),
            "confidence": normalize_confidence(item.get("confidence")),
            "explanation": str(item.get("explanation", "No explanation.")).strip(),
            "correct_fact": str(item.get("correct_fact")).strip() if item.get("correct_fact") else None,
            "sources": [str(s).strip() for s in (item.get("sources", []) if isinstance(item.get("sources"), list) else [])][:MAX_SOURCES],
        })
        if len(results) >= MAX_CLAIMS:
            break
    if not results:
        raise ValueError("No valid claims found")
    return results

def build_unverified_results(claims, reason):
    return [{
        "id": c["id"], "claim": c["claim"], "category": c["category"],
        "verdict": "Unverified", "confidence": "Low", "explanation": reason,
        "correct_fact": None, "sources": []
    } for c in claims]

# ============================================
# ANALYSIS FUNCTIONS
# ============================================

def analyze_with_groq(groq_key: str, serper_key: str, text: str) -> list[dict]:
    local_claims = extract_claims_locally(text)
    if not local_claims:
        raise ValueError("No claims found")
    
    results = []
    for claim_item in local_claims[:MAX_CLAIMS]:
        claim_text = claim_item["claim"]
        search_results = serper_web_search(claim_text, serper_key) if serper_key else ""
        
        prompt = f"""You are a fact-checking expert.

Claim: "{claim_text}"

{f'Search Results:\n{search_results}' if search_results else 'No search results. Use your knowledge.'}

Respond with ONLY JSON (no other text):
{{
    "claim": "{claim_text}",
    "category": "{claim_item['category']}",
    "verdict": "Verified/Inaccurate/False/Unverified",
    "confidence": "High/Medium/Low",
    "explanation": "Brief explanation",
    "correct_fact": "Correct fact if wrong, else null",
    "sources": ["source or null"]
}}"""
        
        try:
            result_text = groq_generate(groq_key, prompt, temperature=0.0)
            parsed = parse_json_text(result_text)
            if isinstance(parsed, dict):
                results.append(parsed)
            elif isinstance(parsed, list) and parsed:
                results.append(parsed[0])
        except Exception as e:
            results.append({"claim": claim_text, "category": claim_item["category"], "verdict": "Unverified", "confidence": "Low", "explanation": f"Error: {str(e)[:100]}", "correct_fact": None, "sources": []})
    
    return normalize_analysis_results(results)

# ============================================
# UI FUNCTIONS
# ============================================

def badge_html(verdict: str) -> str:
    mapping = {"Verified": ("verified", "✅ Verified"), "Inaccurate": ("inaccurate", "⚠️ Inaccurate"), "False": ("false", "❌ False"), "Unverified": ("unverified", "❓ Unverified")}
    cls, label = mapping.get(verdict, ("unverified", verdict))
    return f'<span class="badge badge-{cls}">{label}</span>'

def render_claim_card(result: dict) -> None:
    verdict = result.get("verdict", "Unverified")
    card_cls = {"Verified": "verified", "Inaccurate": "inaccurate", "False": "false", "Unverified": "unverified"}.get(verdict, "unverified")
    
    claim_text = html.escape(str(result.get("claim", "")).strip())
    explanation = html.escape(str(result.get("explanation", "")).strip())
    confidence = str(result.get("confidence", "?")).strip().title()
    category = html.escape(str(result.get("category", "")).strip().upper())
    
    correct_html = f"<p class='correct-fact'>✅ Correct fact: {html.escape(str(result['correct_fact']))}</p>" if result.get("correct_fact") else ""
    sources_html = ""
    if result.get("sources"):
        source_tags = [f"<span class='source-link'>{html.escape(str(s))}</span>" for s in result["sources"][:3]]
        sources_html = f"<p style='margin-top:0.4rem;'>{' · '.join(source_tags)}</p>"
    
    st.markdown(f"""
    <div class="claim-card {card_cls}">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
        {badge_html(verdict)}
        <span style="font-size:0.75rem;font-weight:600;">{confidence} confidence · {category}</span>
      </div>
      <p class="claim-text">"{claim_text}"</p>
      <p class="verdict-text">{explanation}</p>
      {correct_html}
      {sources_html}
    </div>
    """, unsafe_allow_html=True)

# ============================================
# MAIN APP
# ============================================

with st.sidebar:
    st.markdown('<div class="sidebar-box">', unsafe_allow_html=True)
    st.markdown("### ⚡ Groq API")
    
    groq_key = get_groq_key()
    serper_key = get_serper_key()
    
    if groq_key:
        st.success(f"✅ Groq API key configured\nModel: {GROQ_MODEL}")
    else:
        st.error("❌ Groq API key missing - Add to secrets")
    
    if serper_key:
        st.success("✅ Serper API key configured (Web Search)")
    else:
        st.info("ℹ️ Serper key optional - add for web search")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-box">', unsafe_allow_html=True)
    st.markdown("### 📊 Verdict Guide")
    st.markdown("✅ **Verified** - Matches evidence\n⚠️ **Inaccurate** - Outdated/wrong\n❌ **False** - Contradicted\n❓ **Unverified** - Can't verify")
    st.markdown('</div>', unsafe_allow_html=True)

col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader("📄 Upload PDF", type=["pdf"])

with col_info:
    st.markdown("""
    <div class="stat-box" style="margin-bottom:0.8rem;">
      <div class="stat-num" style="color:#6366f1;">⚡</div>
      <div class="stat-label">Groq LPU - Ultra Fast</div>
    </div>
    <div style="background:#1e2130;border-radius:10px;padding:1rem;border:1px solid #2d3748;font-size:0.82rem;">
      <b>How it works</b><br><br>1. Upload PDF<br>2. Groq AI extracts claims<br>3. Web search verification<br>4. Get verdict report
    </div>
    """, unsafe_allow_html=True)

run = st.button("🚀 Analyze PDF", use_container_width=True, type="primary")

if run:
    if not uploaded_file:
        st.error("Please upload a PDF file.")
        st.stop()
    
    groq_key = get_groq_key()
    if not groq_key:
        st.error("❌ Groq API key not configured! Add GROQ_API_KEY to secrets.")
        st.stop()
    
    with st.spinner("📄 Extracting text from PDF..."):
        try:
            pdf_text = extract_text_from_pdf(uploaded_file)
        except Exception as e:
            st.error(f"PDF error: {e}")
            st.stop()
    
    if not pdf_text.strip():
        st.error("No text found in PDF.")
        st.stop()
    
    st.success(f"✅ Extracted {len(pdf_text):,} characters")
    
    with st.spinner("⚡ Analyzing with Groq (ultra-fast)..."):
        try:
            results = analyze_with_groq(groq_key, serper_key, pdf_text)
            mode = "groq_web_search" if serper_key else "groq_model_only"
        except Exception as e:
            local_claims = extract_claims_locally(pdf_text)
            if not local_claims:
                st.error(f"Analysis failed: {e}")
                st.stop()
            results = build_unverified_results(local_claims, f"AI unavailable: {str(e)[:100]}")
            mode = "local_fallback"
    
    st.success(f"✅ Analysis complete for {len(results)} claims!")
    
    st.markdown("---")
    st.markdown("## 📊 Analysis Report")
    st.caption(f"Mode: {ANALYSIS_MODE_LABELS.get(mode, mode)} | Model: {GROQ_MODEL}")
    st.markdown(f"*Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*")
    
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        counts[r.get("verdict", "Unverified")] += 1
    
    c1, c2, c3, c4 = st.columns(4)
    for col, (label, color, icon) in zip([c1, c2, c3, c4], [("Verified", "#10b981", "✅"), ("Inaccurate", "#f59e0b", "⚠️"), ("False", "#ef4444", "❌"), ("Unverified", "#6366f1", "❓")]):
        with col:
            st.markdown(f"<div class='stat-box'><div class='stat-num' style='color:{color};'>{icon} {counts[label]}</div><div class='stat-label'>{label}</div></div>", unsafe_allow_html=True)
    
    st.markdown("### 🔎 Detailed Results")
    for item in results:
        render_claim_card(item)
    
    report_json = json.dumps({"generated_at": datetime.now().isoformat(), "model": GROQ_MODEL, "mode": mode, "summary": counts, "results": results}, indent=2)
    st.download_button("⬇️ Download JSON Report", data=report_json, file_name="factcheck_report.json", mime="application/json")