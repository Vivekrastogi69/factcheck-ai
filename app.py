import streamlit as st
import pdfplumber
import requests
import json
import re
import time
import html as html_lib

GROQ_API_KEY   = "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"
SERPER_API_KEY = "c04f1c3f9bcd7ef89ffe4e6264e672901cd94112"
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"

st.set_page_config(page_title="FactCheck AI", page_icon="🔍", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif!important;}
.stApp{background:#080B14;color:#E2E8F0;}
[data-testid="stSidebar"]{background:#0D1117!important;border-right:1px solid #1E2D3D!important;}
.hero-section{background:linear-gradient(135deg,#0D1117 0%,#111827 50%,#0D1117 100%);border:1px solid #1E2D3D;border-radius:20px;padding:3rem 2rem;text-align:center;margin-bottom:2rem;position:relative;overflow:hidden;}
.hero-section::before{content:'';position:absolute;top:-50%;left:50%;transform:translateX(-50%);width:600px;height:300px;background:radial-gradient(ellipse,rgba(99,102,241,0.15) 0%,transparent 70%);pointer-events:none;}
.hero-badge{display:inline-block;background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);color:#818CF8;padding:0.3rem 1rem;border-radius:100px;font-size:0.75rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:1rem;}
.hero-title{font-size:3rem;font-weight:700;background:linear-gradient(135deg,#FFFFFF 0%,#818CF8 50%,#C084FC 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0.5rem 0;line-height:1.1;}
.hero-sub{color:#64748B;font-size:1rem;margin-top:0.5rem;}
.stButton>button{background:linear-gradient(135deg,#6366F1,#8B5CF6)!important;color:white!important;border:none!important;border-radius:12px!important;padding:0.75rem 2rem!important;font-family:'Space Grotesk',sans-serif!important;font-size:1rem!important;font-weight:600!important;letter-spacing:0.02em!important;box-shadow:0 4px 24px rgba(99,102,241,0.3)!important;}
.stats-container{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0;}
.stat-box{background:#0D1117;border:1px solid #1E2D3D;border-radius:16px;padding:1.25rem;text-align:center;position:relative;overflow:hidden;}
.stat-box::before{content:'';position:absolute;inset:0;opacity:0.05;border-radius:16px;}
.stat-box.verified::before{background:#10B981;}
.stat-box.inaccurate::before{background:#F59E0B;}
.stat-box.false::before{background:#EF4444;}
.stat-box.unverified::before{background:#6366F1;}
.stat-num{font-size:2.5rem;font-weight:700;line-height:1;margin-bottom:0.25rem;}
.stat-num.verified{color:#10B981;}
.stat-num.inaccurate{color:#F59E0B;}
.stat-num.false{color:#EF4444;}
.stat-num.unverified{color:#818CF8;}
.stat-label{font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;color:#475569;font-weight:600;}
.claim-card{background:#0D1117;border:1px solid #1E2D3D;border-radius:16px;padding:1.5rem;margin-bottom:1rem;border-left:4px solid;}
.claim-card.verified{border-left-color:#10B981;}
.claim-card.inaccurate{border-left-color:#F59E0B;}
.claim-card.false{border-left-color:#EF4444;}
.claim-card.unverified{border-left-color:#6366F1;}
.verdict-pill{display:inline-flex;align-items:center;gap:0.4rem;padding:0.3rem 0.9rem;border-radius:100px;font-size:0.75rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:0.75rem;}
.pill-verified{background:rgba(16,185,129,0.1);color:#10B981;border:1px solid rgba(16,185,129,0.3);}
.pill-inaccurate{background:rgba(245,158,11,0.1);color:#F59E0B;border:1px solid rgba(245,158,11,0.3);}
.pill-false{background:rgba(239,68,68,0.1);color:#EF4444;border:1px solid rgba(239,68,68,0.3);}
.pill-unverified{background:rgba(99,102,241,0.1);color:#818CF8;border:1px solid rgba(99,102,241,0.3);}
.claim-text{font-family:'JetBrains Mono',monospace;font-size:0.88rem;color:#E2E8F0;background:rgba(255,255,255,0.03);border:1px solid #1E2D3D;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.75rem;line-height:1.6;}
.claim-exp{font-size:0.9rem;color:#94A3B8;line-height:1.7;}
.correct-fact{margin-top:0.75rem;padding:0.6rem 1rem;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);border-radius:8px;font-size:0.85rem;color:#34D399;}
.correct-label{font-weight:700;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;display:block;margin-bottom:0.2rem;color:#10B981;}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;background:#10B981;box-shadow:0 0 8px #10B981;animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}
.stProgress>div>div>div{background:linear-gradient(135deg,#6366F1,#8B5CF6)!important;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0;">
    <div style="font-size:1.2rem;font-weight:700;color:#E2E8F0;margin-bottom:1.5rem;">🔍 FactCheck AI</div>
    <div style="margin-bottom:0.6rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="status-dot"></span>
        <span style="font-size:0.85rem;color:#94A3B8;">Groq LLM — Active</span>
    </div>
    <div style="margin-bottom:1.5rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="status-dot"></span>
        <span style="font-size:0.85rem;color:#94A3B8;">Serper Web Search — Live</span>
    </div>
    <div style="border-top:1px solid #1E2D3D;padding-top:1rem;">
        <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin-bottom:0.75rem;">How it works</div>
        <div style="font-size:0.82rem;color:#64748B;line-height:1.8;">
            1. 📄 Extract full claims from PDF<br>
            2. 🌐 Live web search per claim<br>
            3. 🤖 AI verdict + evidence<br>
            4. 📊 Report with correct facts
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="hero-section">
    <div class="hero-badge">AI-Powered Truth Layer</div>
    <div class="hero-title">FactCheck AI</div>
    <div class="hero-sub">Upload a PDF → Live Web Search → Instant Verdict on Every Claim</div>
</div>
""", unsafe_allow_html=True)


def serper_search(query):
    try:
        r = requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 6}, timeout=20)
        r.raise_for_status()
        return "\n\n".join(
            f"[{i.get('title','')}] {i.get('snippet','')}"
            for i in r.json().get("organic", [])[:6] if i.get("snippet")
        )
    except Exception:
        return ""


def call_groq(prompt, max_tokens=800, retries=4):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": max_tokens}
    delay = 4
    for attempt in range(retries):
        try:
            r = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=50)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            if r.status_code == 429:
                time.sleep(delay); delay = min(delay * 2, 30); continue
            r.raise_for_status()
        except requests.RequestException:
            if attempt == retries - 1: raise
            time.sleep(3)
    return ""


def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def extract_claims_ai(text):
    prompt = f"""You are a claim extractor for a professional fact-checking system.

Extract every SPECIFIC, VERIFIABLE factual claim from the document below.

STRICT RULES:
- Each claim MUST be a COMPLETE SENTENCE: subject + verb + exact figure/fact + context
- GOOD example: "Tesla sold 2.5 million vehicles in 2024"
- BAD example: "2.5 million" or "sold vehicles" (fragments are INVALID)
- Include the full entity name in every claim (never orphaned numbers)
- Keep exact numbers, dates, names as written in the document
- Maximum 15 claims

Return ONLY a valid JSON array of strings. No markdown. No backticks. No explanation.
Example output: ["Tesla sold 2.5 million vehicles in 2024.", "Apple revenue in 2024 was $500 billion."]

DOCUMENT:
{text[:8000]}"""

    raw = call_groq(prompt, max_tokens=1200)
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            claims = json.loads(match.group())
            good = []
            for c in claims:
                c = str(c).strip().strip('"')
                if len(c) > 20 and not re.match(r'^\$?[\d,.]+ ?(million|billion|thousand)?$', c, re.I):
                    good.append(c)
            return good[:15]
        except Exception:
            pass

    # Fallback regex
    claims = []
    for m in re.finditer(r'\d+\.\s*"?([A-Z][^.\n]{20,}\.?)"?', text):
        c = m.group(1).strip().strip('"')
        if c and c not in claims:
            claims.append(c)
    return claims[:15]


def verify_claim(claim):
    search_results = serper_search(claim)
    prompt = f"""You are a professional fact-checker. Verify the claim using the search results.

CLAIM: "{claim}"

LIVE WEB SEARCH RESULTS:
{search_results if search_results else "No results — use your training knowledge."}

VERDICT OPTIONS:
- "Verified"   = accurate, confirmed by evidence
- "Inaccurate" = right topic but wrong number/date/scale (outdated or exaggerated)
- "False"      = clearly wrong with contradicting evidence
- "Unverified" = cannot confirm or deny

Respond ONLY with valid JSON. No markdown. No backticks:
{{"verdict":"Verified|Inaccurate|False|Unverified","confidence":"High|Medium|Low","explanation":"One precise sentence citing evidence.","correct_fact":"Real accurate fact with context, or null"}}"""

    try:
        raw = call_groq(prompt, max_tokens=600)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if result.get("verdict") not in ("Verified", "Inaccurate", "False", "Unverified"):
                result["verdict"] = "Unverified"
            return result
    except Exception:
        pass

    return {"verdict": "Unverified", "confidence": "Low",
            "explanation": "Verification data could not be retrieved.", "correct_fact": None}


uploaded = st.file_uploader("Drop your PDF here or click to browse", type=["pdf"],
    help="Any text-based PDF — reports, articles, marketing docs, research papers")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run = st.button("🔍  Run Fact-Check", use_container_width=True)

if run:
    if not uploaded:
        st.error("Please upload a PDF file first.")
        st.stop()

    start_time = time.time()

    with st.spinner("📄 Reading PDF…"):
        raw_text = extract_pdf_text(uploaded)

    if not raw_text.strip():
        st.error("Could not extract text. The PDF may be a scanned image.")
        st.stop()

    st.success(f"✅ Extracted {len(raw_text):,} characters from **{uploaded.name}**")

    with st.spinner("🧠 Identifying factual claims with AI…"):
        claims = extract_claims_ai(raw_text)

    if not claims:
        st.error("No verifiable claims found.")
        st.stop()

    st.success(f"✅ Found **{len(claims)}** verifiable claims")

    with st.expander(f"📋 View all {len(claims)} extracted claims"):
        for i, c in enumerate(claims, 1):
            st.markdown(
                f"<div style='padding:0.4rem 0;color:#94A3B8;font-size:0.88rem;border-bottom:1px solid #1E2D3D'>"
                f"<span style='color:#6366F1;font-weight:700;margin-right:0.5rem'>{i}.</span>"
                f"{html_lib.escape(c)}</div>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:1.1rem;font-weight:700;color:#E2E8F0;margin:2rem 0 1rem 0;'>🌐 Verifying against live web data</div>",
        unsafe_allow_html=True)

    progress_bar = st.progress(0)
    status_text  = st.empty()
    results = []
    counts  = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    stats_ph = st.empty()

    def render_stats(c):
        stats_ph.markdown(f"""
        <div class="stats-container">
            <div class="stat-box verified"><div class="stat-num verified">{c['Verified']}</div><div class="stat-label">✅ Verified</div></div>
            <div class="stat-box inaccurate"><div class="stat-num inaccurate">{c['Inaccurate']}</div><div class="stat-label">⚠️ Inaccurate</div></div>
            <div class="stat-box false"><div class="stat-num false">{c['False']}</div><div class="stat-label">❌ False</div></div>
            <div class="stat-box unverified"><div class="stat-num unverified">{c['Unverified']}</div><div class="stat-label">❓ Unverified</div></div>
        </div>""", unsafe_allow_html=True)

    render_stats(counts)
    claims_container = st.container()
    all_cards_html = []

    ICONS = {"Verified":"✅","Inaccurate":"⚠️","False":"❌","Unverified":"❓"}
    PILL  = {"Verified":"pill-verified","Inaccurate":"pill-inaccurate","False":"pill-false","Unverified":"pill-unverified"}

    for i, claim in enumerate(claims):
        status_text.markdown(
            f"<div style='font-size:0.85rem;color:#64748B;margin-bottom:0.5rem'>"
            f"Verifying {i+1}/{len(claims)}: <em>{html_lib.escape(claim[:80])}…</em></div>",
            unsafe_allow_html=True)

        result = verify_claim(claim)
        result["claim"] = claim
        results.append(result)

        v = result.get("verdict", "Unverified")
        counts[v] = counts.get(v, 0) + 1
        render_stats(counts)

        cf = result.get("correct_fact")
        correct_html = ""
        if cf and str(cf).lower() not in ("null","none",""):
            correct_html = (f"<div class='correct-fact'>"
                f"<span class='correct-label'>✓ Correct fact</span>"
                f"{html_lib.escape(str(cf))}</div>")

        card_html = (
            f"<div class='claim-card {v.lower()}'>"
            f"<div class='verdict-pill {PILL.get(v,'pill-unverified')}'>{ICONS.get(v,'❓')} {v} &nbsp;·&nbsp; {result.get('confidence','Low')} confidence</div>"
            f"<div class='claim-text'>\"{html_lib.escape(claim)}\"</div>"
            f"<div class='claim-exp'>{html_lib.escape(result.get('explanation',''))}</div>"
            f"{correct_html}</div>")

        all_cards_html.append(card_html)
        with claims_container:
            st.markdown("".join(all_cards_html), unsafe_allow_html=True)

        progress_bar.progress((i + 1) / len(claims))
        time.sleep(2)

    status_text.empty()
    elapsed  = time.time() - start_time
    flagged  = counts["Inaccurate"] + counts["False"]
    accuracy = round(counts["Verified"] / len(results) * 100) if results else 0

    st.markdown(f"""
    <div style="background:#0D1117;border:1px solid #1E2D3D;border-radius:16px;padding:1.5rem 2rem;margin-top:1.5rem;text-align:center;">
        <div style="font-size:2rem;font-weight:700;color:#E2E8F0;margin-bottom:0.25rem;">{accuracy}% accuracy rate</div>
        <div style="color:#64748B;font-size:0.9rem;">{flagged} claim{"s" if flagged!=1 else ""} flagged &nbsp;·&nbsp; completed in {elapsed:.1f}s</div>
    </div>""", unsafe_allow_html=True)

    if flagged > 0:
        st.warning(f"⚠️ {flagged} claim(s) flagged — see correct facts in the cards above.")
    else:
        st.success("🎉 All verifiable claims check out!")
