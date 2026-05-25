import streamlit as st
import pdfplumber
import requests
import json
import re
import time
from datetime import datetime
import html

# ============================================
# API KEYS
# ============================================
GROQ_API_KEY = "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"
SERPER_API_KEY = "c04f1c3f9bcd7ef89ffe4e6264e672901cd94112"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title="FactCheck AI", page_icon="✅", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #1a1a4a, #24243e); }
.hero { text-align: center; padding: 2rem; background: rgba(255,255,255,0.05); border-radius: 30px; margin-bottom: 2rem; }
.hero h1 { font-size: 2.5rem; background: linear-gradient(135deg, #fff, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.claim-card { background: rgba(255,255,255,0.08); border-radius: 16px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid; }
.verified { border-left-color: #10b981; }
.inaccurate { border-left-color: #f59e0b; }
.false { border-left-color: #ef4444; }
.unverified { border-left-color: #6366f1; }
.stat-card { background: rgba(255,255,255,0.08); border-radius: 20px; padding: 1rem; text-align: center; }
.stat-number { font-size: 2rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ✅ System Status")
    st.success("✅ Groq AI — Active")
    st.success("✅ Serper API — Live Search")

def serper_search(query):
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": 5}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        results = [item.get("snippet", "") for item in data.get("organic", [])[:5] if item.get("snippet")]
        return "\n\n".join(results) if results else ""
    except:
        return ""

def verify_single_claim(claim):
    """Verify single claim with proper handling"""
    
    # Search web
    search_results = serper_search(claim)
    
    prompt = f"""Fact-check this claim using search results.

CLAIM: "{claim}"

SEARCH RESULTS:
{search_results if search_results else "No results"}

Based on the search results, respond with JSON:
{{"verdict": "Verified/Inaccurate/False/Unverified", "confidence": "High/Medium/Low", "explanation": "...", "correct_fact": "correct fact or null"}}"""

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 500
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=45)
        
        if response.status_code == 200:
            resp_text = response.json()["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        elif response.status_code == 429:
            time.sleep(5)
            return verify_single_claim(claim)
    except:
        pass
    
    return {"verdict": "Unverified", "confidence": "Low", "explanation": "Could not verify", "correct_fact": None}

def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() or "" for p in pdf.pages])

def extract_claims(text):
    claims = []
    pattern = r'(\d+)\.\s*"([^"]+)"'
    matches = re.findall(pattern, text)
    for num, claim in matches:
        if len(claim) > 10:
            claims.append(claim.strip())
    return claims[:10]

# ============================================
# MAIN
# ============================================
st.markdown("""
<div class="hero">
    <h1>✅ FactCheck AI</h1>
    <p>Upload PDF → Live Web Search → Get Verdicts</p>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload caheck.pdf", type=["pdf"])

if st.button("Start Fact-Checking", use_container_width=True):
    if not uploaded:
        st.error("Upload PDF first")
        st.stop()
    
    start = time.time()
    
    # Extract text
    with st.spinner("Reading PDF..."):
        text = extract_pdf_text(uploaded)
    
    st.success(f"✅ {len(text)} characters")
    
    # Extract claims
    with st.spinner("Extracting claims..."):
        claims = extract_claims(text)
    
    st.success(f"✅ {len(claims)} claims found")
    
    with st.expander("Extracted Claims"):
        for i, c in enumerate(claims, 1):
            st.write(f"{i}. {c}")
    
    # Verify claims one by one with longer delay
    results = []
    progress = st.progress(0)
    
    for i, claim in enumerate(claims):
        st.info(f"Verifying {i+1}/{len(claims)}: {claim[:50]}...")
        
        result = verify_single_claim(claim)
        result["claim"] = claim
        results.append(result)
        
        progress.progress((i+1)/len(claims))
        time.sleep(3)  # 3 second delay between claims
    
    elapsed = time.time() - start
    
    # Display results
    st.markdown("---")
    st.markdown("## 📊 Report")
    st.caption(f"Time: {elapsed:.1f}s")
    
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
        icon = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "❓"}.get(v, "❓")
        cls = v.lower()
        
        correct_html = ""
        if item.get("correct_fact") and item["correct_fact"] not in [None, "null", ""]:
            correct_html = f"<p style='color:#34d399'><strong>✅ CORRECT:</strong> {item['correct_fact']}</p>"
        
        st.markdown(f"""
        <div class="claim-card {cls}">
            <div><span style="background:rgba(99,102,241,0.2); padding:0.2rem 0.8rem; border-radius:20px;">{icon} {v}</span></div>
            <p><strong>"{item['claim']}"</strong></p>
            <p>{item.get('explanation', '')}</p>
            {correct_html}
        </div>
        """, unsafe_allow_html=True)
    
    st.balloons()
    st.success(f"Done in {elapsed:.1f}s!")
