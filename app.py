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
# CONFIGURATION
# ============================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "3d998a7f713348b7808231646724142b30c8df56")
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
.source-link {
    font-size: 0.75rem; color: #a5b4fc;
    background: rgba(99,102,241,0.1);
    padding: 0.3rem 0.7rem;
    border-radius: 10px; margin-top: 0.4rem;
    display: inline-block;
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
.search-snippet {
    font-size: 0.75rem; color: #64748b;
    background: rgba(255,255,255,0.03);
    border-radius: 8px; padding: 0.4rem 0.7rem;
    margin-top: 0.4rem; font-style: italic;
}
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
    st.success("✅ **Groq AI** — Active\n`llama-3.3-70b-versatile`") if groq_ok else st.error("❌ Groq API key missing")
    st.success("✅ **Serper API** — Active\n🔍 Live Google Search") if serper_ok else st.error("❌ Serper API key missing")
    st.markdown("---")
    st.markdown("### 📋 **Verdict Guide**")
    st.markdown("✅ **Verified** — Matches current evidence")
    st.markdown("⚠️ **Inaccurate** — Outdated or numbers off")
    st.markdown("❌ **False** — Completely incorrect / fabricated")
    st.markdown("❓ **Unverified** — Cannot find reliable evidence")
    st.markdown("---")
    st.markdown("### ⚙️ **Settings**")
    max_claims = st.slider("Max Claims to Check", 5, 20, 12)
    show_snippets = st.checkbox("Show Web Search Snippets", value=False)
    st.markdown("---")
    st.markdown("### 🎯 **Features**")
    st.markdown("- PDF Upload & Text Extraction")
    st.markdown("- AI-Powered Claim Identification")
    st.markdown("- Live Web Search (Google via Serper)")
    st.markdown("- Verdict with Correct Facts")
    st.markdown("- Source URLs in report")
    st.markdown("- JSON Report Download")

# ============================================
# API FUNCTIONS
# ============================================

def serper_search(query, num_results=5):
    """Search Google using Serper API, return snippets + source URLs"""
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": num_results, "gl": "us", "hl": "en"}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            title = item.get("title", "")
            if snippet:
                results.append({"title": title, "snippet": snippet, "link": link})

        # Also grab knowledge graph if present
        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.insert(0, {"title": kg.get("title", ""), "snippet": kg["description"], "link": ""})

        return results
    except Exception as e:
        return []


def format_search_for_prompt(results):
    """Format search results into a string for the LLM prompt"""
    if not results:
        return "No search results available."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\n{r['snippet']}")
    return "\n\n".join(lines)


def groq_call(system_prompt, user_prompt, max_tokens=2000, retry=0):
    """Call Groq API with system+user messages and retry on rate limit"""
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
    """Extract all text from uploaded PDF"""
    pages_text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return "\n\n".join(pages_text)


# ============================================
# CLAIM EXTRACTION (LLM-powered, not just regex)
# ============================================

def extract_claims_with_llm(text, max_claims=12):
    """Use LLM to identify verifiable factual claims from document text"""

    # Truncate text if too long
    truncated = text[:6000] if len(text) > 6000 else text

    system = """You are an expert fact-checker. Your job is to identify specific, verifiable factual claims from documents.

Focus on:
- Statistics and numbers (percentages, counts, revenue figures)
- Dates and timelines (founded year, launch date, milestones)
- Rankings and positions ("world's largest", "#1 in...")
- Named facts about companies, countries, people
- Scientific or technical figures
- Market size or share claims
- Growth rates and projections

AVOID extracting:
- Vague opinions or predictions without numbers
- Marketing slogans or subjective claims
- Very obvious/trivially true statements

Respond ONLY with a valid JSON array. No extra text."""

    user = f"""Extract up to {max_claims} specific, verifiable factual claims from this document. Each claim must be a complete sentence that can be independently fact-checked.

DOCUMENT:
{truncated}

Return JSON array:
[
  {{"claim": "The full claim sentence", "category": "statistic|date|ranking|technical|financial|other"}},
  ...
]"""

    response = groq_call(system, user, max_tokens=2000)

    if response:
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?", "", response).strip().rstrip("`").strip()
        # Find JSON array
        match = re.search(r'\[.*\]', clean, re.DOTALL)
        if match:
            try:
                claims = json.loads(match.group())
                # Validate structure
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

    # Fallback to regex-based extraction
    return extract_claims_regex(text, max_claims)


def extract_claims_regex(text, max_claims=12):
    """Fallback regex-based claim extraction"""
    claims = []
    sentences = re.split(r'(?<=[.!?])\s+', text)

    keywords = [
        'million', 'billion', 'crore', 'lakh', 'trillion',
        'percent', '%', '$', '₹', '€', '£',
        'revenue', 'profit', 'loss', 'earnings', 'valuation',
        'employees', 'workforce', 'subscribers', 'users',
        'founded', 'launched', 'released', 'established',
        'largest', 'biggest', 'fastest', 'first', 'leading',
        'population', 'ranked', 'position', 'market share',
        'growth', 'increase', 'decrease', 'declined', 'rose'
    ]

    for s in sentences:
        s = s.strip()
        if len(s) < 20 or len(s) > 400:
            continue
        has_number = bool(re.search(r'\d+', s))
        has_keyword = any(kw in s.lower() for kw in keywords)
        if has_number or has_keyword:
            s_clean = re.sub(r'^\d+[\.\)]\s*', '', s)
            claims.append({"claim": s_clean, "category": "statistic"})
        if len(claims) >= max_claims:
            break

    return claims


# ============================================
# CLAIM VERIFICATION
# ============================================

def build_search_query(claim):
    """Build an optimised search query from the claim"""
    # Remove filler words, keep key nouns/numbers
    stop = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'has', 'have', 'had',
            'that', 'this', 'with', 'for', 'and', 'or', 'but', 'in', 'on', 'at'}
    tokens = [t for t in re.findall(r'\b\w+\b', claim) if t.lower() not in stop]
    query = " ".join(tokens[:12])
    return query + " fact check"


def verify_claim(claim_text, show_snippet=False):
    """Verify a single claim using web search + Groq LLM"""

    search_query = build_search_query(claim_text)
    search_results = serper_search(search_query, num_results=5)
    search_text = format_search_for_prompt(search_results)
    current_year = datetime.now().year

    system = """You are a rigorous, unbiased fact-checker. You verify claims against real-world evidence from web search results.

Rules:
- Verified: The claim's core facts match current search evidence
- Inaccurate: The claim has wrong numbers, wrong dates, or is significantly outdated
- False: The claim is completely fabricated or contradicts all evidence
- Unverified: Cannot find sufficient evidence to confirm or deny

Be especially strict about:
- Numbers and statistics (even small differences matter)
- Dates and years
- Superlatives like "world's largest" or "first ever"
- Market share or ranking claims

Always provide the correct fact with specific numbers if the claim is wrong. Respond ONLY with valid JSON."""

    user = f"""Fact-check this claim using the search results below.

CLAIM: "{claim_text}"

GOOGLE SEARCH RESULTS (as of {current_year}):
{search_text}

Respond ONLY with this JSON (no extra text, no markdown):
{{
    "verdict": "Verified|Inaccurate|False|Unverified",
    "confidence": "High|Medium|Low",
    "explanation": "2-3 sentences explaining your verdict citing the search results",
    "correct_fact": "The correct fact with specific numbers if claim is wrong, else null",
    "search_query_used": "{search_query}"
}}"""

    response = groq_call(system, user, max_tokens=800)

    result = {
        "verdict": "Unverified",
        "confidence": "Low",
        "explanation": "Could not verify automatically.",
        "correct_fact": None,
        "search_snippets": search_results[:3] if show_snippet else []
    }

    if response:
        clean = re.sub(r"```(?:json)?", "", response).strip().rstrip("`").strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                result.update(parsed)
                result["search_snippets"] = search_results[:3] if show_snippet else []
            except json.JSONDecodeError:
                pass

    return result


# ============================================
# UI — HERO SECTION
# ============================================
st.markdown("""
<div class="hero">
    <h1>✅ FactCheck AI</h1>
    <p style="color: #94a3b8; font-size: 1.1rem; margin: 0 0 1rem 0;">
        Automated Claim Verification with Live Web Search
    </p>
    <div style="display: inline-flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center;">
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px; font-size: 0.85rem;">⚡ Groq LPU Inference</span>
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px; font-size: 0.85rem;">🔍 Google Web Search</span>
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px; font-size: 0.85rem;">🤖 LLaMA 3.3 70B</span>
        <span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.3rem 1rem; border-radius: 50px; font-size: 0.85rem;">📊 Real-time Facts</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Steps
st.markdown("""
<div class="steps">
    <div class="step-card"><div class="step-number">1</div><strong style="color:#e2e8f0;">Upload PDF</strong><br><span style="font-size:0.8rem;">Any text-based PDF</span></div>
    <div class="step-card"><div class="step-number">2</div><strong style="color:#e2e8f0;">AI Extracts Claims</strong><br><span style="font-size:0.8rem;">LLM identifies verifiable facts</span></div>
    <div class="step-card"><div class="step-number">3</div><strong style="color:#e2e8f0;">Live Web Verify</strong><br><span style="font-size:0.8rem;">Google search cross-reference</span></div>
    <div class="step-card"><div class="step-number">4</div><strong style="color:#e2e8f0;">Detailed Report</strong><br><span style="font-size:0.8rem;">Verdicts + correct facts</span></div>
</div>
""", unsafe_allow_html=True)

# Upload Area
uploaded_file = st.file_uploader(
    "📄 Upload PDF Document",
    type=["pdf"],
    help="Upload any PDF containing statistics, dates, or factual claims. Works great on marketing docs, reports, and press releases."
)

# Analyze Button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    analyze_btn = st.button("🚀 Start Fact-Checking", use_container_width=True, type="primary")

# ============================================
# PROCESSING PIPELINE
# ============================================
if analyze_btn:
    if not uploaded_file:
        st.error("❌ Please upload a PDF file first.")
        st.stop()

    st.info("🌐 **LIVE WEB SEARCH ENABLED** — Cross-referencing claims against real-time Google results")

    # Step 1: Extract PDF text
    with st.spinner("📄 Reading PDF and extracting text..."):
        try:
            pdf_text = extract_pdf_text(uploaded_file)
        except Exception as e:
            st.error(f"❌ PDF reading error: {e}")
            st.stop()

    if not pdf_text.strip():
        st.error("⚠️ No text found in this PDF. Please ensure it's a text-based (not scanned/image) PDF.")
        st.stop()

    char_count = len(pdf_text)
    st.success(f"✅ Extracted **{char_count:,} characters** from {uploaded_file.name}")

    # Step 2: Extract claims using LLM
    with st.spinner("🤖 AI is identifying verifiable claims..."):
        claims = extract_claims_with_llm(pdf_text, max_claims=max_claims)

    if not claims:
        st.error("⚠️ No verifiable claims found. Make sure your PDF contains statistics, numbers, or factual assertions.")
        st.stop()

    st.success(f"✅ Identified **{len(claims)} verifiable claims** — Starting web verification...")

    # Step 3: Verify each claim
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, claim_obj in enumerate(claims):
        claim_txt = claim_obj["claim"]
        status_text.info(f"🌐 Verifying {i+1}/{len(claims)}: *{claim_txt[:80]}{'...' if len(claim_txt)>80 else ''}*")

        result = verify_claim(claim_txt, show_snippet=show_snippets)
        result["claim"] = claim_txt
        result["category"] = claim_obj.get("category", "statistic")
        results.append(result)

        progress_bar.progress((i + 1) / len(claims))
        time.sleep(1.2)  # Rate limit safety

    status_text.empty()
    progress_bar.empty()

    # ============================================
    # DISPLAY RESULTS
    # ============================================
    st.markdown("---")
    st.markdown("## 📊 Fact-Check Report")
    col_date, col_file = st.columns(2)
    with col_date:
        st.caption(f"📅 Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}")
    with col_file:
        st.caption(f"📄 File: {uploaded_file.name} | 🌐 Web Search: ✅ Enabled")

    # Summary Stats
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        verdict = r.get("verdict", "Unverified")
        if verdict not in counts:
            verdict = "Unverified"
        counts[verdict] += 1

    total = len(results)
    accuracy_score = round((counts["Verified"] / total) * 100) if total else 0
    flag_score = round(((counts["Inaccurate"] + counts["False"]) / total) * 100) if total else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#10b981;">✅ {counts["Verified"]}</div><div>Verified</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#f59e0b;">⚠️ {counts["Inaccurate"]}</div><div>Inaccurate</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#ef4444;">❌ {counts["False"]}</div><div>False</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#6366f1;">❓ {counts["Unverified"]}</div><div>Unverified</div></div>', unsafe_allow_html=True)
    with col5:
        color = "#10b981" if flag_score < 30 else "#f59e0b" if flag_score < 60 else "#ef4444"
        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:{color};">🚩 {flag_score}%</div><div>Flag Rate</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ============================================
    # DETAILED RESULTS TABS
    # ============================================
    st.markdown("### 🔎 Detailed Analysis")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"📋 All ({total})",
        f"✅ Verified ({counts['Verified']})",
        f"⚠️ Inaccurate ({counts['Inaccurate']})",
        f"❌ False ({counts['False']})",
        f"❓ Unverified ({counts['Unverified']})"
    ])

    verdict_icon = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "❓"}

    def render_claim_cards(items):
        if not items:
            st.info("No claims in this category.")
            return
        for item in items:
            v = item.get("verdict", "Unverified")
            if v not in verdict_icon:
                v = "Unverified"
            icon = verdict_icon[v]
            cls = v.lower()
            conf = item.get("confidence", "Low")
            cat = item.get("category", "statistic").upper()

            correct_html = ""
            cf = item.get("correct_fact")
            if cf and str(cf).lower() not in ["none", "null", "", "n/a"]:
                correct_html = f'<div class="correct-fact">💡 <strong>CORRECT FACT:</strong> {html.escape(str(cf))}</div>'

            snippet_html = ""
            if show_snippets and item.get("search_snippets"):
                snip = item["search_snippets"][0]
                snippet_html = f'''<div class="search-snippet">🔍 Source: <em>{html.escape(snip.get("title",""))}</em> — {html.escape(snip.get("snippet","")[:200])}</div>'''

            st.markdown(f"""
            <div class="claim-card {cls}">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                    <span class="badge bg-{cls}">{icon} {v}</span>
                    <span style="font-size: 0.72rem; color: #64748b;">{conf} confidence | {cat}</span>
                </div>
                <p style="margin-top: 0.8rem; color: #e2e8f0;"><strong>"{html.escape(str(item['claim']))}"</strong></p>
                <p style="color: #94a3b8; font-size: 0.9rem; margin: 0.3rem 0;">{html.escape(str(item.get('explanation', 'No explanation provided.')))}</p>
                {correct_html}
                {snippet_html}
            </div>
            """, unsafe_allow_html=True)

    for tab, verdict_filter in zip(
        [tab1, tab2, tab3, tab4, tab5],
        ["All", "Verified", "Inaccurate", "False", "Unverified"]
    ):
        with tab:
            filtered = results if verdict_filter == "All" else [
                r for r in results if r.get("verdict", "Unverified") == verdict_filter
            ]
            render_claim_cards(filtered)

    # ============================================
    # DOWNLOAD REPORT
    # ============================================
    st.markdown("---")
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "file_name": uploaded_file.name,
        "total_claims": total,
        "web_search_enabled": True,
        "summary": {**counts, "flag_rate_percent": flag_score},
        "results": [
            {
                "id": i + 1,
                "claim": r["claim"],
                "category": r.get("category", "statistic"),
                "verdict": r.get("verdict", "Unverified"),
                "confidence": r.get("confidence", "Low"),
                "explanation": r.get("explanation", ""),
                "correct_fact": r.get("correct_fact")
            }
            for i, r in enumerate(results)
        ]
    }

    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
    with col_dl2:
        st.download_button(
            label="📥 Download Full Report (JSON)",
            data=json.dumps(report_data, indent=2, ensure_ascii=False),
            file_name=f"factcheck_{uploaded_file.name.replace('.pdf','')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    st.balloons()
    st.success(f"✅ Fact-checking complete! Flagged **{counts['Inaccurate'] + counts['False']}** problematic claims out of {total} total.")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; font-size: 0.72rem; color: #475569; padding: 1rem;">
    🔍 <strong>FactCheck AI</strong> — Automated Truth Layer &nbsp;|&nbsp;
    ✅ AI Claim Extraction &nbsp;|&nbsp;
    🌐 Live Google Search via Serper &nbsp;|&nbsp;
    📊 Verified / Inaccurate / False Verdicts &nbsp;|&nbsp;
    💡 Correct Facts Provided
</div>
""", unsafe_allow_html=True)
