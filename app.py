import streamlit as st
import pdfplumber
import requests
import json
import re
import os
import time
from datetime import datetime
import html
from concurrent.futures import ThreadPoolExecutor

# ============================================
# API KEYS
# ============================================

def get_groq_key():
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except:
        pass
    return os.getenv("GROQ_API_KEY", "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")

def get_serper_key():
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
# PAGE CONFIG
# ============================================
st.set_page_config(page_title="FactCheck AI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #1a1a4a, #24243e); }
.hero { text-align: center; padding: 2rem; background: rgba(255,255,255,0.05); border-radius: 30px; margin-bottom: 2rem; }
.hero h1 { font-size: 3rem; background: linear-gradient(135deg, #fff, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.claim-card { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid; }
.verified { border-left-color: #10b981; }
.inaccurate { border-left-color: #f59e0b; }
.false { border-left-color: #ef4444; }
.unverified { border-left-color: #6366f1; }
.stat-card { background: rgba(255,255,255,0.05); border-radius: 20px; padding: 1rem; text-align: center; }
.stat-number { font-size: 2rem; font-weight: 800; }
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0; }
.step-card { text-align: center; padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 16px; }
.step-number { width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem; font-weight: bold; color: white; }
.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border-radius: 40px !important; width: 100% !important; }
.correct-fact { font-size: 0.8rem; color: #34d399; background: rgba(16,185,129,0.1); padding: 0.3rem 0.7rem; border-radius: 12px; margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚡ **Status**")
    st.success("✅ Groq AI Active")
    st.success("✅ Serper API Active")
    st.markdown("---")
    st.markdown("### Verdict Guide")
    st.markdown("✅ Verified - Matches evidence")
    st.markdown("⚠️ Inaccurate - Numbers off")
    st.markdown("❌ False - Wrong")
    st.markdown("❓ Unverified - Cannot verify")

# ============================================
# FAST API FUNCTIONS
# ============================================

def serper_search_fast(query):
    """Fast search - fewer results"""
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 2},
            timeout=15
        )
        data = r.json()
        snippets = [item.get("snippet", "") for item in data.get("organic", [])[:2] if item.get("snippet")]
        return "\n\n".join(snippets) if snippets else ""
    except:
        return ""

def groq_call_fast(prompt):
    """Fast Groq call - smaller tokens"""
    try:
        r = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 600},
            timeout=25
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None

def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() or "" for p in pdf.pages])

def extract_claims_fast(text):
    """Fast regex extraction - no LLM call"""
    claims = []
    sentences = re.split(r'[.!?\n]+', text)
    
    for s in sentences:
        s = s.strip()
        if not s or len(s) < 15 or len(s) > 300:
            continue
        if re.search(r'\d+|million|billion|crore|percent|%|\$|₹|revenue|profit|sold|employees|population', s, re.I):
            s = re.sub(r'^\d+\.\s*', '', s)
            claims.append({"id": len(claims)+1, "claim": s, "category": "statistic"})
        if len(claims) >= 10:
            break
    return claims

def verify_claim_fast(claim_text):
    """Fast verification - optimized prompt"""
    search_results = serper_search_fast(claim_text)
    
    prompt = f"""Fact check: "{claim_text}"

{f'Search: {search_results}' if search_results else 'No results'}

Respond JSON: {{"verdict": "Verified/Inaccurate/False", "explanation": "short", "correct_fact": "correct or null"}}"""

    resp = groq_call_fast(prompt)
    
    if resp:
        match = re.search(r'\{.*\}', resp, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    
    return {"verdict": "Unverified", "explanation": "Could not verify", "correct_fact": None}

# ============================================
# PARALLEL VERIFICATION
# ============================================

def verify_single(claim_obj):
    """Single claim verification for parallel processing"""
    result = verify_claim_fast(claim_obj["claim"])
    result["claim"] = claim_obj["claim"]
    result["category"] = claim_obj.get("category", "statistic")
    return result

# ============================================
# UI
# ============================================
st.markdown("""
<div class="hero">
    <h1>⚡ FactCheck AI</h1>
    <p>Ultra-Fast Claim Verification | 10 claims in ~15 seconds</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="steps">
    <div class="step-card"><div class="step-number">1</div>📄 Upload PDF</div>
    <div class="step-card"><div class="step-number">2</div>🤖 Extract Claims</div>
    <div class="step-card"><div class="step-number">3</div>⚡ Parallel Verify</div>
    <div class="step-card"><div class="step-number">4</div>📊 Report</div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("", type=["pdf"], label_visibility="collapsed")

if st.button("🚀 Start Fact-Checking", use_container_width=True):
    if not uploaded:
        st.error("Upload PDF first")
        st.stop()
    
    start_time = time.time()
    
    # Extract text
    with st.spinner("📄 Reading PDF..."):
        text = extract_pdf_text(uploaded)
    
    if not text.strip():
        st.error("No text found")
        st.stop()
    
    st.success(f"✅ {len(text)} chars")
    
    # Extract claims
    with st.spinner("🔍 Extracting claims..."):
        claims = extract_claims_fast(text)
    
    if not claims:
        st.error("No claims found")
        st.stop()
    
    st.success(f"✅ {len(claims)} claims found")
    
    # PARALLEL verification (3x faster)
    with st.spinner(f"⚡ Verifying {len(claims)} claims in parallel..."):
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(verify_single, claims))
    
    elapsed = time.time() - start_time
    st.info(f"⚡ Completed in {elapsed:.1f} seconds")
    
    # Display results
    st.markdown("---")
    st.markdown("## 📊 Report")
    st.caption(f"Generated: {datetime.now().strftime('%H:%M:%S')} | Time: {elapsed:.1f}s")
    
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        counts[r.get("verdict", "Unverified")] += 1
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#10b981'>✅ {counts['Verified']}</div><div>Verified</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#f59e0b'>⚠️ {counts['Inaccurate']}</div><div>Inaccurate</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#ef4444'>❌ {counts['False']}</div><div>False</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#6366f1'>❓ {counts['Unverified']}</div><div>Unverified</div></div>", unsafe_allow_html=True)
    
    st.markdown("### Detailed Results")
    for item in results:
        v = item.get("verdict", "Unverified")
        icon = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌"}.get(v, "❓")
        cls = v.lower()
        
        correct_html = ""
        if item.get("correct_fact") and str(item["correct_fact"]) not in ["None", "null", ""]:
            correct_html = f'<div class="correct-fact">💡 Correct: {html.escape(str(item["correct_fact"]))}</div>'
        
        st.markdown(f"""
        <div class="claim-card {cls}">
            <div><span style="background:rgba(99,102,241,0.2); padding:0.2rem 0.8rem; border-radius:20px;">{icon} {v}</span>
            <span style="margin-left:0.5rem;">{item.get('confidence', 'Low')}</span></div>
            <p><strong>"{item['claim']}"</strong></p>
            <p>{item.get('explanation', '')}</p>
            {correct_html}
        </div>
        """, unsafe_allow_html=True)
    
    # Download
    report = {"timestamp": datetime.now().isoformat(), "time_seconds": elapsed, "summary": counts, "results": results}
    st.download_button("📥 JSON", data=json.dumps(report, indent=2), file_name="factcheck.json", mime="application/json")
    st.balloons()
    st.success(f"✅ Done in {elapsed:.1f}s!")

st.markdown("---")
st.markdown("<p style='text-align:center'>⚡ Ultra-Fast FactCheck AI</p>", unsafe_allow_html=True)
