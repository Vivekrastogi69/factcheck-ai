import streamlit as st
import pdfplumber
import requests
import json
import re
import time
from datetime import datetime
import os

# ============================================
# API KEYS (Consider using st.secrets for production)
# ============================================
GROQ_API_KEY = "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"
SERPER_API_KEY = "c04f1c3f9bcd7ef89ffe4e6264e672901cd94112"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title="FactCheck AI", page_icon="✅", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #1a1a4a, #24243e); color: white; }
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
    st.info("📌 Upload a PDF with claims in format: '1. \"Claim text\"'")

def serper_search(query):
    """Search the web using Serper API"""
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        # Enhance search query for better results
        enhanced_query = f"{query} statistics fact check"
        payload = {"q": enhanced_query, "num": 5}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Get organic search results
            for item in data.get("organic", [])[:5]:
                if item.get("snippet"):
                    results.append(f"Source: {item.get('link', 'Unknown')}\n{item.get('snippet')}")
            
            # Also get knowledge graph if available
            if data.get("knowledgeGraph"):
                kg = data["knowledgeGraph"]
                if kg.get("description"):
                    results.append(f"Knowledge Graph: {kg.get('description')}")
            
            return "\n\n".join(results) if results else ""
        else:
            st.warning(f"Search API returned status {response.status_code}")
            return ""
    except Exception as e:
        st.warning(f"Search error: {str(e)}")
        return ""

def verify_single_claim(claim, retry_count=0):
    """Verify single claim with proper handling and retries"""
    
    # Search web for the claim
    search_results = serper_search(claim)
    
    prompt = f"""You are a professional fact-checker. Verify this claim using the search results provided.

CLAIM: "{claim}"

SEARCH RESULTS:
{search_results if search_results else "No search results found. Use your knowledge to evaluate."}

Based on the evidence, respond with ONLY a valid JSON object in this exact format:
{{"verdict": "Verified/Inaccurate/False/Unverified", "confidence": "High/Medium/Low", "explanation": "Brief explanation of your reasoning", "correct_fact": "The correct fact if different from claim, otherwise null"}}

Rules for verdict:
- Verified: Search results directly support the claim
- Inaccurate: Claim is partially true but has errors (especially outdated stats)
- False: Claim is completely wrong or contradicts search results  
- Unverified: No clear evidence found

Keep explanations concise (1-2 sentences)."""

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # Slight randomness but still focused
            "max_tokens": 500
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=45)
        
        if response.status_code == 200:
            resp_text = response.json()["choices"][0]["message"]["content"]
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Ensure all required fields exist
                return {
                    "verdict": result.get("verdict", "Unverified"),
                    "confidence": result.get("confidence", "Low"),
                    "explanation": result.get("explanation", "Could not verify"),
                    "correct_fact": result.get("correct_fact")
                }
        elif response.status_code == 429 and retry_count < 3:
            # Rate limit - wait and retry
            time.sleep(5)
            return verify_single_claim(claim, retry_count + 1)
        else:
            st.warning(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.warning(f"Verification error: {str(e)}")
    
    return {"verdict": "Unverified", "confidence": "Low", "explanation": "Verification failed", "correct_fact": None}

def extract_pdf_text(file):
    """Extract text from PDF with better error handling"""
    try:
        text = ""
        with pdfplumber.open(file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def extract_claims(text):
    """Extract claims in format 'N. "Claim"' and smart detection"""
    claims = []
    
    # Pattern 1: Numbered claims with quotes
    pattern1 = r'(\d+)\.\s*"([^"]+)"'
    matches = re.findall(pattern1, text)
    for num, claim in matches:
        if len(claim) > 10:  # Filter out very short claims
            claims.append(claim.strip())
    
    # Pattern 2: Claims with bullet points
    pattern2 = r'[•\-*]\s*"([^"]+)"'
    matches = re.findall(pattern2, text)
    for claim in matches:
        if len(claim) > 10:
            claims.append(claim.strip())
    
    # Pattern 3: Look for statements with numbers (stats)
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        # Check if sentence contains numbers (potential stats)
        if re.search(r'\d+(?:\.\d+)?%|\$\d+|\d+\s*(?:million|billion|percent|years?)', sentence):
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:
                claims.append(sentence)
    
    # Remove duplicates and limit
    claims = list(dict.fromkeys(claims))[:15]
    return claims

# ============================================
# MAIN APPLICATION
# ============================================
st.markdown("""
<div class="hero">
    <h1>✅ FactCheck AI</h1>
    <p>Upload a PDF → Extract Claims → Live Web Verification → Get Truth Report</p>
</div>
""", unsafe_allow_html=True)

# File uploader
uploaded_file = st.file_uploader("Choose a PDF file to fact-check", type=["pdf"], help="Upload PDF containing claims in format: '1. \"Claim to verify\"'")

# Process button
if st.button("🔍 Start Fact-Checking", use_container_width=True, type="primary"):
    if not uploaded_file:
        st.error("❌ Please upload a PDF file first")
        st.stop()
    
    start_time = time.time()
    
    # Step 1: Extract text from PDF
    with st.spinner("📄 Reading PDF file..."):
        pdf_text = extract_pdf_text(uploaded_file)
    
    if not pdf_text:
        st.error("❌ Could not extract text from PDF. Please ensure the PDF contains readable text.")
        st.stop()
    
    st.success(f"✅ Extracted {len(pdf_text)} characters from PDF")
    
    # Step 2: Extract claims
    with st.spinner("🔍 Identifying factual claims..."):
        claims = extract_claims(pdf_text)
    
    if not claims:
        st.warning("⚠️ No claims found in the PDF. Please ensure claims are formatted as '1. \"Claim text\"' or contain statistical information.")
        st.info("Example format:\n1. \"The global population reached 8 billion in 2022\"\n2. \"Tesla sold 500,000 vehicles in 2020\"")
        st.stop()
    
    st.success(f"✅ Found {len(claims)} claims to verify")
    
    # Show extracted claims
    with st.expander("📋 Extracted Claims", expanded=True):
        for i, claim in enumerate(claims, 1):
            st.write(f"**{i}.** {claim}")
    
    # Step 3: Verify each claim
    st.markdown("---")
    st.markdown("## 🔎 Verification in Progress")
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, claim in enumerate(claims):
        status_text.info(f"🔄 Verifying claim {i+1}/{len(claims)}: {claim[:80]}...")
        
        result = verify_single_claim(claim)
        result["claim"] = claim
        results.append(result)
        
        progress_bar.progress((i + 1) / len(claims))
        
        # Add delay between API calls to avoid rate limiting
        if i < len(claims) - 1:
            time.sleep(2)
    
    status_text.empty()
    elapsed_time = time.time() - start_time
    
    # Step 4: Display results
    st.markdown("---")
    st.markdown("## 📊 Fact-Check Report")
    st.caption(f"⏱️ Completed in {elapsed_time:.1f} seconds")
    
    # Statistics
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        counts[r.get("verdict", "Unverified")] += 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number' style='color:#10b981'>✅ {counts['Verified']}</div>
            <div>Verified</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number' style='color:#f59e0b'>⚠️ {counts['Inaccurate']}</div>
            <div>Inaccurate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number' style='color:#ef4444'>❌ {counts['False']}</div>
            <div>False</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number' style='color:#6366f1'>❓ {counts['Unverified']}</div>
            <div>Unverified</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display detailed results
    st.markdown("### 📝 Detailed Analysis")
    
    for item in results:
        verdict = item.get("verdict", "Unverified")
        
        # Set icon and color based on verdict
        icon_map = {
            "Verified": "✅",
            "Inaccurate": "⚠️",
            "False": "❌",
            "Unverified": "❓"
        }
        icon = icon_map.get(verdict, "❓")
        css_class = verdict.lower()
        
        # Build HTML for the claim card
        correct_info = ""
        if item.get("correct_fact") and item["correct_fact"] not in [None, "null", "", "null"]:
            correct_info = f"""
            <div style='margin-top: 8px; padding: 8px; background: rgba(52, 211, 153, 0.1); border-radius: 8px;'>
                <strong>✅ Correct Fact:</strong> {item['correct_fact']}
            </div>
            """
        
        confidence_badge = {
            "High": "🟢 High",
            "Medium": "🟡 Medium",
            "Low": "🔴 Low"
        }.get(item.get("confidence", "Low"), "⚪ Unknown")
        
        st.markdown(f"""
        <div class='claim-card {css_class}'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                <span style='background: rgba(99,102,241,0.2); padding: 4px 12px; border-radius: 20px; font-size: 0.9rem;'>
                    {icon} {verdict}
                </span>
                <span style='font-size: 0.8rem; opacity: 0.7;'>{confidence_badge} confidence</span>
            </div>
            <p><strong>Claim:</strong> {item['claim']}</p>
            <p><strong>Analysis:</strong> {item.get('explanation', 'No explanation provided')}</p>
            {correct_info}
        </div>
        """, unsafe_allow_html=True)
    
    # Success message
    st.balloons()
    st.success(f"✨ Fact-checking complete! Found {counts['Inaccurate'] + counts['False']} questionable claims.")
    
    # Add download report button
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_claims": len(claims),
        "results": results
    }
    
    st.download_button(
        label="📥 Download Report (JSON)",
        data=json.dumps(report_data, indent=2),
        file_name=f"factcheck_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem;'>
    FactCheck AI uses Groq LLM and Serper API for live web verification
</div>
""", unsafe_allow_html=True)
