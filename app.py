import streamlit as st
import pdfplumber
import requests
import json
import re
import os
import time
from datetime import datetime
import html

# ============================================
# API KEY CONFIGURATION (Streamlit Secrets Ready)
# ============================================

def get_groq_key():
    """Get Groq API key from secrets or environment"""
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except:
        pass
    return os.getenv("GROQ_API_KEY", "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")

def get_serper_key():
    """Get Serper API key from secrets or environment"""
    try:
        if "SERPER_API_KEY" in st.secrets:
            return st.secrets["SERPER_API_KEY"]
    except:
        pass
    return os.getenv("SERPER_API_KEY", "3d998a7f713348b7808231646724142b30c8df56")

GROQ_API_KEY = get_groq_key()
SERPER_API_KEY = get_serper_key()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="FactCheck AI — Truth Layer",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CSS STYLING
# ============================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29, #1a1a4a, #24243e); }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.hero {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px);
    border-radius: 32px;
    padding: 2.5rem;
    margin-bottom: 2rem;
    text-align: center;
    border: 1px solid rgba(99,102,241,0.3);
}
.hero h1 {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #fff, #a5b4fc, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.5rem 0;
}
.steps {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin: 2rem 0;
}
.step-card {
    text-align: center;
    padding: 1rem;
    background: rgba(255,255,255,0.03);
    border-radius: 20px;
    border: 1px solid rgba(99,102,241,0.2);
    color: #94a3b8;
}
.step-number {
    width: 45px; height: 45px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 25px;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 0.8rem;
    font-weight: bold; font-size: 1.2rem; color: white;
}
.claim-card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    border-left: 4px solid;
    transition: transform 0.2s;
}
.claim-card:hover { transform: translateX(5px); }
.verified { border-left-color: #10b981; }
.inaccurate { border-left-color: #f59e0b; }
.false { border-left-color: #ef4444; }
.unverified { border-left-color: #6366f1; }
.stat-card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 1rem;
    text-align: center;
    color: #e2e8f0;
}
.stat-number { font-size: 2.2rem; font-weight: 800; }
.badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    padding: 0.25rem 0.85rem;
    border-radius: 40px;
    font-size: 0.72rem; font-weight: 600;
}
.bg-verified { background: rgba(16,185,129,0.2); color: #34d399; }
.bg-inaccurate { background: rgba(245,158,11,0.2); color: #fbbf24; }
.bg-false { background: rgba(239,68,68,0.2); color: #f87171; }
.bg-unverified { background: rgba(99,102,241,0.2); color: #a5b4fc; }
.correct-fact {
    font-size: 0.82rem; color: #34d399;
    background: rgba(16,185,129,0.1);
    padding: 0.4rem 0.8rem;
    border-radius: 12px; margin-top: 0.6rem;
}
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 40px !important;
    font-weight: 600 !important;
    padding: 0.7rem 2rem !important;
    width: 100% !important;
    font-size: 1rem !important;
}
[data-testid="stSidebar"] {
    background: rgba(0,0,0,0.5) !important;
    backdrop-filter: blur(20px) !important;
}
.stProgress > div > div { background: linear-gradient(90deg, #6366f1, #8b5cf6); }
</style>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("## 🎯 **System Status**")
    st.markdown("---")
    groq_ok = bool(GROQ_API_KEY)
    serper_ok = bool(SERPER_API_KEY)
    
    if groq_ok:
        st.success("✅ **Groq AI** — Active\n`llama-3.3-70b-versatile`")
    else:
        st.error("❌ Groq API key missing")
    
    if serper_ok:
        st.success("✅ **Serper API** — Active\n🔍 Live Google Search")
    else:
        st.error("❌ Serper API key missing")
    
    st.markdown("---")
    st.markdown("### 📋 **Verdict Guide**")
    st.markdown("✅ **Verified** — Matches current evidence")
    st.markdown("⚠️ **Inaccurate** — Outdated or numbers off")
    st.markdown("❌ **False** — Completely incorrect / fabricated")
    st.markdown("❓ **Unverified** — Cannot find reliable evidence")
    st.markdown("---")
    st.markdown("### 🎯 **Features**")
    st.markdown("- PDF Upload & Text Extraction")
    st.markdown("- AI-Powered Claim Identification")
    st.markdown("- Live Web Search (Google via Serper)")
    st.markdown("- Verdict with Correct Facts")
    st.markdown("- JSON Report Download")

# ============================================
# API FUNCTIONS
# ============================================

def serper_search(query, num_results=5):
    """Search Google using Serper API"""
    if not SERPER_API_KEY:
        return []
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": num_results, "gl": "us", "hl": "en"}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            snippet = item.get("snippet", "")
            title = item.get("title", "")
            if snippet:
                results.append({"title": title, "snippet": snippet})

        # Knowledge graph
        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.insert(0, {"title": kg.get("title", ""), "snippet": kg["description"]})

        return results
    except Exception as e:
        return []

def format_search_for_prompt(results):
    if not results:
        return "No search results available."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\n{r['snippet']}")
    return "\n\n".join(lines)

def groq_call(system_prompt, user_prompt, max_tokens=2000, retry=0):
    if not GROQ_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0,
            "max_tokens": max_tokens
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=90)

        if response.status_code == 429:
            if retry < 4:
                wait_time = (retry + 1) * 6
                time.sleep(wait_time)
                return groq_call(system_prompt, user_prompt, max_tokens, retry + 1)
            return None

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        if retry < 2:
            time.sleep(4)
            return groq_call(system_prompt, user_prompt, max_tokens, retry + 1)
        return None

def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])

def extract_claims_with_llm(text, max_claims=12):
    truncated = text[:6000] if len(text) > 6000 else text

    system = """You are an expert fact-checker. Identify specific, verifiable factual claims.

Focus on: statistics, numbers, dates, financial figures, company facts, rankings.

Respond ONLY with JSON array: [{"claim": "...", "category": "statistic/date/financial/other"}]"""

    user = f"""Extract up to {max_claims} verifiable claims from this document.

DOCUMENT:
{truncated}

Return JSON array only."""

    response = groq_call(system, user, max_tokens=2000)

    if response:
        clean = re.sub(r"```(?:json)?", "", response).strip().rstrip("`").strip()
        match = re.search(r'\[.*\]', clean, re.DOTALL)
        if match:
            try:
                claims = json.loads(match.group())
                valid = []
                for c in claims:
                    if isinstance(c, dict) and "claim" in c and len(str(c["claim"])) > 15:
                        valid.append({
                            "claim": str(c["claim"]).strip(),
                            "category": str(c.get("category", "statistic")).lower()
                        })
                return valid[:max_claims]
            except json.JSONDecodeError:
                pass

    # Fallback to regex
    return extract_claims_regex(text, max_claims)

def extract_claims_regex(text, max_claims=12):
    claims = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    keywords = ['million', 'billion', 'percent', '%', '$', '₹', 'revenue', 'profit', 'employees', 'population']
    for s in sentences:
        s = s.strip()
        if len(s) < 20 or len(s) > 400:
            continue
        if re.search(r'\d+', s) or any(kw in s.lower() for kw in keywords):
            s_clean = re.sub(r'^\d+[\.\)]\s*', '', s)
            claims.append({"claim": s_clean, "category": "statistic"})
        if len(claims) >= max_claims:
            break
    return claims

def verify_claim(claim_text):
    # Build search query
    tokens = re.findall(r'\b\w+\b', claim_text)
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'has', 'have', 'had', 'that', 'this', 'with', 'for', 'and', 'or', 'but', 'in', 'on', 'at', 'of', 'to', 'from', 'by'}
    query_tokens = [t for t in tokens[:12] if t.lower() not in stopwords]
    search_query = " ".join(query_tokens)
    
    search_results = serper_search(search_query, num_results=5)
    search_text = format_search_for_prompt(search_results)
    current_year = datetime.now().year

    system = """You are a rigorous fact-checker. Verify claims against search results.

Rules:
- Verified: Claim matches evidence
- Inaccurate: Wrong numbers or outdated
- False: Completely fabricated
- Unverified: Cannot find evidence

Respond ONLY with JSON:
{"verdict": "Verified/Inaccurate/False/Unverified", "confidence": "High/Medium/Low", "explanation": "...", "correct_fact": "correct info or null"}"""

    user = f"""Fact-check this claim.

CLAIM: "{claim_text}"

SEARCH RESULTS ({current_year}):
{search_text}

Return JSON only."""

    response = groq_call(system, user, max_tokens=800)

    result = {
        "verdict": "Unverified",
        "confidence": "Low",
        "explanation": "Could not verify automatically.",
        "correct_fact": None
    }

    if response:
        clean = re.sub(r"```(?:json)?", "", response).strip().rstrip("`").strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                result.update(parsed)
            except json.JSONDecodeError:
                pass

    return result

# ============================================
# MAIN UI
# ============================================
st.markdown("""
<div class="hero">
    <h1>✅ FactCheck AI</h1>
    <p style="color: #94a3b8; font-size: 1.1rem;">Automated Claim Verification with Live Web Search</p>
    <div style="display: inline-flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center;">
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px;">⚡ Groq LPU</span>
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px;">🔍 Google Search</span>
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px;">📊 Real-time Facts</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="steps">
    <div class="step-card"><div class="step-number">1</div><strong>Upload PDF</strong><br><span style="font-size:0.8rem;">Any text-based PDF</span></div>
    <div class="step-card"><div class="step-number">2</div><strong>AI Extracts Claims</strong><br><span style="font-size:0.8rem;">Identifies verifiable facts</span></div>
    <div class="step-card"><div class="step-number">3</div><strong>Live Web Verify</strong><br><span style="font-size:0.8rem;">Google search cross-reference</span></div>
    <div class="step-card"><div class="step-number">4</div><strong>Detailed Report</strong><br><span style="font-size:0.8rem;">Verdicts + correct facts</span></div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📄 Upload PDF Document", type=["pdf"])

if st.button("🚀 Start Fact-Checking", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Please upload a PDF file.")
        st.stop()

    if not GROQ_API_KEY:
        st.error("❌ Groq API key missing. Add GROQ_API_KEY to secrets.")
        st.stop()

    st.info("🌐 **LIVE WEB SEARCH ENABLED** — Cross-referencing claims against real-time Google results")

    with st.spinner("📄 Reading PDF..."):
        try:
            pdf_text = extract_pdf_text(uploaded_file)
        except Exception as e:
            st.error(f"PDF error: {e}")
            st.stop()

    if not pdf_text.strip():
        st.error("No text found in PDF.")
        st.stop()

    st.success(f"✅ Extracted {len(pdf_text):,} characters")

    with st.spinner("🔍 Extracting claims..."):
        claims = extract_claims_with_llm(pdf_text, max_claims=12)

    if not claims:
        st.error("No verifiable claims found.")
        st.stop()

    st.success(f"✅ Found {len(claims)} claims")

    results = []
    progress = st.progress(0)

    for i, claim_obj in enumerate(claims):
        st.caption(f"Verifying {i+1}/{len(claims)}: {claim_obj['claim'][:60]}...")
        result = verify_claim(claim_obj["claim"])
        result["claim"] = claim_obj["claim"]
        result["category"] = claim_obj.get("category", "statistic")
        results.append(result)
        progress.progress((i+1)/len(claims))
        time.sleep(1)

    progress.empty()

    st.markdown("---")
    st.markdown("## 📊 Fact-Check Report")
    st.caption(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}")

    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        counts[r.get("verdict", "Unverified")] += 1

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#10b981'>✅ {counts['Verified']}</div><div>Verified</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#f59e0b'>⚠️ {counts['Inaccurate']}</div><div>Inaccurate</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#ef4444'>❌ {counts['False']}</div><div>False</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#6366f1'>❓ {counts['Unverified']}</div><div>Unverified</div></div>", unsafe_allow_html=True)

    for item in results:
        v = item.get("verdict", "Unverified")
        icon = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌"}.get(v, "❓")
        cls = v.lower()
        
        correct_html = ""
        if item.get("correct_fact") and str(item["correct_fact"]) not in ["None", "null", ""]:
            correct_html = f'<div class="correct-fact">💡 CORRECT FACT: {html.escape(str(item["correct_fact"]))}</div>'
        
        st.markdown(f"""
        <div class="claim-card {cls}">
            <div><span class="badge bg-{cls}">{icon} {v}</span> <span style="font-size:0.7rem;">{item.get('confidence', 'Low')} confidence | {item.get('category', 'statistic').upper()}</span></div>
            <p><strong>"{item['claim']}"</strong></p>
            <p>{item.get('explanation', '')}</p>
            {correct_html}
        </div>
        """, unsafe_allow_html=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "file": uploaded_file.name,
        "web_search": True,
        "summary": counts,
        "results": results
    }
    st.download_button("📥 Download JSON", data=json.dumps(report, indent=2), file_name="factcheck.json", mime="application/json")
    st.balloons()
    st.success("✅ Done!")

st.markdown("---")
st.markdown("<p style='text-align:center;'>✅ FactCheck AI — Truth Layer</p>", unsafe_allow_html=True)
