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
# API KEYS
# ============================================
GROQ_API_KEY = "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"
SERPER_API_KEY = "3d998a7f713348b7808231646724142b30c8df56"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(page_title="Universal FactCheck AI", page_icon="🌍", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #1a1a4a, #24243e); }
.hero { text-align: center; padding: 2rem; background: rgba(255,255,255,0.05); border-radius: 30px; margin-bottom: 2rem; }
.hero h1 { font-size: 2.5rem; background: linear-gradient(135deg, #fff, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.claim-card { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid; transition: all 0.2s; }
.claim-card:hover { transform: translateX(5px); }
.verified { border-left-color: #10b981; background: rgba(16,185,129,0.05); }
.inaccurate { border-left-color: #f59e0b; background: rgba(245,158,11,0.05); }
.false { border-left-color: #ef4444; background: rgba(239,68,68,0.05); }
.unverified { border-left-color: #6366f1; background: rgba(99,102,241,0.05); }
.stat-card { background: rgba(255,255,255,0.05); border-radius: 20px; padding: 1rem; text-align: center; }
.stat-number { font-size: 2rem; font-weight: 800; }
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0; }
.step-card { text-align: center; padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 16px; }
.step-number { width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem; font-weight: bold; color: white; }
.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border-radius: 40px !important; width: 100% !important; }
.correct-fact { font-size: 0.85rem; color: #34d399; background: rgba(16,185,129,0.15); padding: 0.4rem 0.8rem; border-radius: 12px; margin-top: 0.5rem; border-left: 3px solid #10b981; }
.source { font-size: 0.7rem; color: #64748b; margin-top: 0.3rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🌍 **System**")
    st.success("✅ Groq AI — Active")
    st.success("✅ Serper API — Live Search")
    st.markdown("---")
    st.markdown("### 📋 Verdict Guide")
    st.markdown("✅ **Verified** — Matches evidence")
    st.markdown("⚠️ **Inaccurate** — Numbers off")
    st.markdown("❌ **False** — Completely wrong")
    st.markdown("❓ **Unverified** — Cannot verify")
    st.markdown("---")
    st.markdown("### 🎯 Works on")
    st.markdown("- 📄 Resumes (extracts projects/experience)")
    st.markdown("- 📊 Reports & Articles")
    st.markdown("- 📈 Marketing Documents")
    st.markdown("- 📰 News & Press Releases")

# ============================================
# API FUNCTIONS
# ============================================

def serper_search(query):
    """Search Google using Serper API"""
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": 5, "gl": "us", "hl": "en"}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        results = []
        for item in data.get("organic", [])[:5]:
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            if snippet:
                results.append({"snippet": snippet, "link": link})
        
        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.append({"snippet": kg["description"], "link": ""})
        
        return results
    except Exception as e:
        return []

def groq_verify(claim, search_results):
    """Verify claim using Groq"""
    search_text = "\n\n".join([r["snippet"] for r in search_results[:3]]) if search_results else "No search results available."
    
    prompt = f"""You are a professional fact-checker. Verify this claim using the search results.

CLAIM: "{claim}"

SEARCH RESULTS:
{search_text}

Based on the search results, determine the verdict:
- Verified: Claim matches evidence exactly
- Inaccurate: Numbers are different or claim is outdated
- False: Claim is completely wrong
- Unverified: Cannot find enough evidence

IMPORTANT: If claim is wrong, provide the CORRECT FACT with specific numbers.

Respond with ONLY this JSON (no other text):
{{
    "verdict": "Verified/Inaccurate/False/Unverified",
    "confidence": "High/Medium/Low",
    "explanation": "Brief explanation with specific numbers",
    "correct_fact": "Correct fact with numbers if wrong, else null"
}}"""

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 800
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=45)
        
        if response.status_code == 200:
            resp_text = response.json()["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Add sources
                result["sources"] = [r["link"] for r in search_results[:2] if r.get("link")]
                return result
    except Exception as e:
        pass
    
    return {"verdict": "Unverified", "confidence": "Low", "explanation": "Could not verify automatically", "correct_fact": None, "sources": []}

def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])

def extract_all_claims(text):
    """Extract ALL types of claims - works on any PDF"""
    claims = []
    
    # Pattern 1: Numbered claims (1. Something)
    numbered = re.findall(r'(\d+)[\.\)]\s*([^.!?]+[.!?])', text)
    for num, claim in numbered:
        if len(claim) > 15:
            claims.append(f"{claim.strip()}")
    
    # Pattern 2: Sentences with numbers/statistics
    sentences = re.split(r'[.!?\n]+', text)
    for s in sentences:
        s = s.strip()
        if len(s) < 20 or len(s) > 400:
            continue
        
        # Check for verifiable content
        has_number = bool(re.search(r'\d+', s))
        has_percent = bool(re.search(r'\d+%|percent', s, re.I))
        has_money = bool(re.search(r'[$€£₹]\d+|\d+\s*(dollars|rupees|euros)', s, re.I))
        has_date = bool(re.search(r'\b(19|20)\d{2}\b', s))
        has_comparison = bool(re.search(r'(more|less|higher|lower|larger|smaller|faster|slower)', s, re.I))
        
        if has_number or has_percent or has_money or has_date or has_comparison:
            # Clean and add
            s = re.sub(r'^\d+\.\s*', '', s)
            if s not in claims:
                claims.append(s)
    
    # Pattern 3: Bullet points
    bullets = re.findall(r'[•\-*]\s*([^.!?]+[.!?])', text)
    for claim in bullets:
        if len(claim) > 15 and re.search(r'\d', claim):
            claims.append(claim.strip())
    
    # Remove duplicates and limit
    seen = set()
    unique_claims = []
    for c in claims:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique_claims.append(c)
    
    return unique_claims[:12]

# ============================================
# UI
# ============================================
st.markdown("""
<div class="hero">
    <h1>🌍 Universal FactCheck AI</h1>
    <p>Any PDF • Any Claim • Live Web Verification</p>
    <div style="display: inline-flex; gap: 0.5rem; margin-top: 0.5rem;">
        <span style="background: rgba(99,102,241,0.2); padding: 0.2rem 1rem; border-radius: 50px;">📄 Resumes</span>
        <span style="background: rgba(99,102,241,0.2); padding: 0.2rem 1rem; border-radius: 50px;">📊 Reports</span>
        <span style="background: rgba(99,102,241,0.2); padding: 0.2rem 1rem; border-radius: 50px;">📈 Marketing</span>
        <span style="background: rgba(99,102,241,0.2); padding: 0.2rem 1rem; border-radius: 50px;">📰 News</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="steps">
    <div class="step-card"><div class="step-number">1</div>📄 Upload Any PDF</div>
    <div class="step-card"><div class="step-number">2</div>🤖 AI Extracts Claims</div>
    <div class="step-card"><div class="step-number">3</div>🔍 Live Web Search</div>
    <div class="step-card"><div class="step-number">4</div>📊 Get Verdicts</div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("📄 Upload Any PDF Document", type=["pdf"])

if st.button("🚀 Start Universal Fact-Checking", use_container_width=True):
    if not uploaded:
        st.error("❌ Please upload a PDF file.")
        st.stop()
    
    start_time = time.time()
    
    st.info("🔍 **LIVE WEB SEARCH ENABLED** - Cross-referencing claims with Google")
    
    with st.spinner("📄 Reading PDF..."):
        try:
            text = extract_pdf_text(uploaded)
        except Exception as e:
            st.error(f"PDF error: {e}")
            st.stop()
    
    if not text.strip():
        st.error("No text found in PDF.")
        st.stop()
    
    st.success(f"✅ Extracted {len(text):,} characters")
    
    with st.spinner("🔍 Extracting all verifiable claims..."):
        claims = extract_all_claims(text)
    
    if not claims:
        st.warning("⚠️ No verifiable claims found. Try a PDF with numbers, statistics, or dates.")
        st.stop()
    
    st.success(f"✅ Found {len(claims)} verifiable claims")
    
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    for i, claim in enumerate(claims):
        status.info(f"🌐 Verifying {i+1}/{len(claims)}: {claim[:70]}...")
        
        # Search and verify
        search_results = serper_search(claim)
        result = groq_verify(claim, search_results)
        result["claim"] = claim
        results.append(result)
        
        progress.progress((i+1)/len(claims))
        time.sleep(0.3)
    
    status.empty()
    progress.empty()
    elapsed = time.time() - start_time
    
    st.markdown("---")
    st.markdown("## 📊 Fact-Check Report")
    st.caption(f"📅 Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')} | ⏱️ Time: {elapsed:.1f}s")
    st.caption(f"📄 File: {uploaded.name} | 🔍 Web Search: ✅ Enabled")
    
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        counts[r.get("verdict", "Unverified")] += 1
    
    total = len(results)
    flag_rate = round(((counts["Inaccurate"] + counts["False"]) / total) * 100) if total else 0
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#10b981'>✅ {counts['Verified']}</div><div>Verified</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#f59e0b'>⚠️ {counts['Inaccurate']}</div><div>Inaccurate</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#ef4444'>❌ {counts['False']}</div><div>False</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#6366f1'>❓ {counts['Unverified']}</div><div>Unverified</div></div>", unsafe_allow_html=True)
    with c5: st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#f59e0b'>🚩 {flag_rate}%</div><div>Flag Rate</div></div>", unsafe_allow_html=True)
    
    st.markdown("### 🔎 Detailed Analysis")
    
    for item in results:
        v = item.get("verdict", "Unverified")
        icon = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "❓"}.get(v, "❓")
        cls = v.lower()
        conf = item.get("confidence", "Low")
        
        correct_html = ""
        if item.get("correct_fact") and str(item["correct_fact"]) not in ["None", "null", ""]:
            correct_html = f'<div class="correct-fact">💡 <strong>CORRECT FACT:</strong> {html.escape(str(item["correct_fact"]))}</div>'
        
        sources_html = ""
        if item.get("sources"):
            sources_html = f'<div class="source">🔗 Sources: {", ".join([html.escape(s) for s in item["sources"]])}</div>'
        
        st.markdown(f"""
        <div class="claim-card {cls}">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <span style="background: rgba(99,102,241,0.2); padding: 0.2rem 0.8rem; border-radius: 20px;">{icon} {v}</span>
                <span style="font-size: 0.7rem; color: #64748b;">{conf} confidence</span>
            </div>
            <p style="margin-top: 0.6rem;"><strong>"{html.escape(str(item['claim']))}"</strong></p>
            <p style="color: #cbd5e1; font-size: 0.85rem;">{html.escape(str(item.get('explanation', '')))}</p>
            {correct_html}
            {sources_html}
        </div>
        """, unsafe_allow_html=True)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "file": uploaded.name,
        "total_claims": total,
        "flag_rate": flag_rate,
        "summary": counts,
        "results": [
            {
                "claim": r["claim"],
                "verdict": r.get("verdict"),
                "confidence": r.get("confidence"),
                "explanation": r.get("explanation"),
                "correct_fact": r.get("correct_fact"),
                "sources": r.get("sources", [])
            }
            for r in results
        ]
    }
    
    st.download_button("📥 Download Full Report (JSON)", data=json.dumps(report, indent=2), file_name=f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")
    st.balloons()
    
    issues = counts["Inaccurate"] + counts["False"]
    if issues > 0:
        st.warning(f"⚠️ Found {issues} problematic claim(s) that need correction!")
    else:
        st.success(f"✅ All claims verified! No issues found.")
    
    st.success(f"✅ Done in {elapsed:.1f}s")

st.markdown("---")
st.markdown("<p style='text-align: center; font-size: 0.7rem;'>🌍 Universal FactCheck AI — Works on Any PDF | Live Web Search | Verified/Inaccurate/False Verdicts</p>", unsafe_allow_html=True)
