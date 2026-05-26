import streamlit as st
import pdfplumber
import requests
import json
import re
import time
import html as html_lib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# CONFIG
# ============================================================
try:
    GROQ_API_KEY   = st.secrets["GROQ_API_KEY"]
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except Exception:
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "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")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY",  "c04f1c3f9bcd7ef89ffe4e6264e672901cd94112")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"   # fastest Groq model

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="FactCheck AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS — main area only, no sidebar HTML
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
.stApp { background: #080B14; color: #E2E8F0; }
[data-testid="stSidebar"] {
    background: #0D1117 !important;
    border-right: 1px solid #1E2D3D !important;
}

/* Hero */
.hero-section {
    background: linear-gradient(135deg, #0D1117 0%, #111827 50%, #0D1117 100%);
    border: 1px solid #1E2D3D; border-radius: 20px;
    padding: 3rem 2rem; text-align: center;
    margin-bottom: 2rem; position: relative; overflow: hidden;
}
.hero-section::before {
    content: ''; position: absolute; top: -50%; left: 50%;
    transform: translateX(-50%); width: 600px; height: 300px;
    background: radial-gradient(ellipse, rgba(99,102,241,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.hero-badge {
    display: inline-block; background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3); color: #818CF8;
    padding: 0.3rem 1rem; border-radius: 100px; font-size: 0.75rem;
    font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 1rem;
}
.hero-title {
    font-size: 3rem; font-weight: 700;
    background: linear-gradient(135deg, #FFFFFF 0%, #818CF8 50%, #C084FC 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0.5rem 0; line-height: 1.1;
}
.hero-sub { color: #64748B; font-size: 1rem; margin-top: 0.5rem; }

/* Button */
.stButton > button {
    background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; padding: 0.75rem 2rem !important;
    font-size: 1rem !important; font-weight: 600 !important;
    box-shadow: 0 4px 24px rgba(99,102,241,0.3) !important;
    width: 100% !important;
}
.stButton > button:hover {
    box-shadow: 0 8px 32px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
}

/* Stats */
.stats-container {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1rem; margin: 1.5rem 0;
}
.stat-box {
    background: #0D1117; border: 1px solid #1E2D3D;
    border-radius: 16px; padding: 1.25rem; text-align: center;
    position: relative; overflow: hidden;
}
.stat-box::before { content: ''; position: absolute; inset: 0; opacity: 0.05; border-radius: 16px; }
.stat-box.verified::before   { background: #10B981; }
.stat-box.inaccurate::before { background: #F59E0B; }
.stat-box.false::before      { background: #EF4444; }
.stat-box.unverified::before { background: #6366F1; }
.stat-num { font-size: 2.5rem; font-weight: 700; line-height: 1; margin-bottom: 0.25rem; }
.stat-num.verified   { color: #10B981; }
.stat-num.inaccurate { color: #F59E0B; }
.stat-num.false      { color: #EF4444; }
.stat-num.unverified { color: #818CF8; }
.stat-label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; font-weight: 600; }

/* Claim cards */
.claim-card {
    background: #0D1117; border: 1px solid #1E2D3D;
    border-radius: 16px; padding: 1.5rem;
    margin-bottom: 1rem; border-left: 4px solid;
}
.claim-card.verified   { border-left-color: #10B981; }
.claim-card.inaccurate { border-left-color: #F59E0B; }
.claim-card.false      { border-left-color: #EF4444; }
.claim-card.unverified { border-left-color: #6366F1; }
.verdict-pill {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.3rem 0.9rem; border-radius: 100px;
    font-size: 0.75rem; font-weight: 700;
    letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 0.75rem;
}
.pill-verified   { background: rgba(16,185,129,0.1); color: #10B981; border: 1px solid rgba(16,185,129,0.3); }
.pill-inaccurate { background: rgba(245,158,11,0.1); color: #F59E0B; border: 1px solid rgba(245,158,11,0.3); }
.pill-false      { background: rgba(239,68,68,0.1);  color: #EF4444; border: 1px solid rgba(239,68,68,0.3); }
.pill-unverified { background: rgba(99,102,241,0.1); color: #818CF8; border: 1px solid rgba(99,102,241,0.3); }
.claim-text {
    font-family: 'JetBrains Mono', monospace; font-size: 0.88rem; color: #E2E8F0;
    background: rgba(255,255,255,0.03); border: 1px solid #1E2D3D;
    border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.75rem; line-height: 1.6;
}
.claim-exp { font-size: 0.9rem; color: #94A3B8; line-height: 1.7; }
.correct-fact {
    margin-top: 0.75rem; padding: 0.6rem 1rem;
    background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2);
    border-radius: 8px; font-size: 0.85rem; color: #34D399;
}
.correct-label {
    font-weight: 700; font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.08em; display: block; margin-bottom: 0.2rem; color: #10B981;
}
.stProgress > div > div > div { background: linear-gradient(135deg, #6366F1, #8B5CF6) !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR — using native Streamlit (no HTML, no render issues)
# ============================================================
with st.sidebar:
    st.markdown("### 🔍 FactCheck AI")
    st.success("🟢 Groq LLM — Active")
    st.success("🟢 Serper Search — Live")

    st.divider()

    st.markdown("**⚙️ How it works**")
    st.markdown("""
1. 📄 Extract claims from PDF
2. 🌐 Live Google search per claim
3. 🤖 AI judges verdict + evidence
4. 📊 Report with correct facts
""")

    st.divider()

    st.markdown("**📊 Verdict Guide**")
    st.markdown("""
✅ **Verified** — Confirmed accurate  
⚠️ **Inaccurate** — Wrong number/date  
❌ **False** — No evidence found  
❓ **Unverified** — Cannot confirm  
""")

    st.divider()
    st.caption("Powered by Groq · Serper · Streamlit")

# ============================================================
# HERO
# ============================================================
st.markdown("""
<div class="hero-section">
    <div class="hero-badge">✦ AI-Powered Truth Layer</div>
    <div class="hero-title">FactCheck AI</div>
    <div class="hero-sub">Upload any PDF → Live Web Search → Instant Verdict on Every Claim</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def serper_search(query: str) -> str:
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 6}, timeout=20,
        )
        r.raise_for_status()
        snippets = [
            f"[{item.get('title','')}] {item.get('snippet','')}"
            for item in r.json().get("organic", [])[:6] if item.get("snippet")
        ]
        return "\n\n".join(snippets)
    except Exception:
        return ""


def call_groq(prompt: str, max_tokens: int = 800, retries: int = 4) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    delay = 4
    for attempt in range(retries):
        try:
            r = requests.post(GROQ_API_URL, headers=headers, json=body, timeout=50)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            if r.status_code == 429:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            r.raise_for_status()
        except requests.RequestException:
            if attempt == retries - 1:
                return ""
            time.sleep(3)
    return ""


def extract_pdf_text(file) -> str:
    try:
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""


def extract_claims_ai(text: str) -> list:
    prompt = f"""Extract verifiable factual claims from this document.

RULES:
- Complete sentences only: "Tesla sold 2.5M vehicles in 2024" ✅ | "2.5M" ❌
- Include entity name + number/date + context in every claim
- Max 15 claims

Return ONLY a JSON array. Example: ["Claim one.", "Claim two."]

TEXT:
{text[:3000]}"""

    raw = call_groq(prompt, max_tokens=800)
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            claims = json.loads(match.group())
            valid = []
            for c in claims:
                c = str(c).strip().strip('"').strip("'")
                is_fragment = re.match(r'^\$?[\d,.]+ ?(million|billion|thousand|%)?$', c, re.I)
                if len(c) > 20 and not is_fragment:
                    valid.append(c)
            return valid[:15]
        except Exception:
            pass

    # Regex fallback
    claims = []
    for m in re.finditer(r'\d+[\.\)]\s*"?([A-Z][^.\n]{20,}\.?)"?', text):
        c = m.group(1).strip()
        if c and c not in claims:
            claims.append(c)
    return claims[:15]


def verify_claim(claim: str) -> dict:
    search_results = serper_search(claim)
    prompt = f"""Fact-check this claim using the search results below.

CLAIM: "{claim}"

SEARCH RESULTS:
{search_results[:2000] if search_results else "No results — use training knowledge."}

Verdict: Verified=accurate | Inaccurate=wrong number/date | False=contradicted | Unverified=unclear

JSON only, no markdown:
{{"verdict":"Verified|Inaccurate|False|Unverified","confidence":"High|Medium|Low","explanation":"One sentence.","correct_fact":"Real fact or null"}}"""

    try:
        raw = call_groq(prompt, max_tokens=300)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if result.get("verdict") not in ("Verified", "Inaccurate", "False", "Unverified"):
                result["verdict"] = "Unverified"
            cf = result.get("correct_fact", "")
            if str(cf).lower().strip() in ("null", "none", "", "n/a"):
                result["correct_fact"] = None
            return result
    except Exception:
        pass

    return {
        "verdict": "Unverified", "confidence": "Low",
        "explanation": "Could not retrieve verification data.", "correct_fact": None,
    }


# ============================================================
# MAIN UI
# ============================================================
st.info("📋 **Supported:** Any text-based PDF (reports, articles, marketing docs).  ⚠️ **Not supported:** Scanned/image PDFs.")

uploaded = st.file_uploader(
    "Drop your PDF here or click to browse",
    type=["pdf"],
    help="Text-based PDFs only. Max 200MB.",
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run = st.button("🔍  Run Fact-Check", use_container_width=True)

# ============================================================
# PIPELINE
# ============================================================
if run:
    if not uploaded:
        st.error("⚠️ Please upload a PDF file first.")
        st.stop()

    start_time = time.time()

    # Step 1 — Read PDF
    with st.spinner("📄 Reading PDF…"):
        raw_text = extract_pdf_text(uploaded)

    char_count = len(raw_text.strip())

    if char_count == 0:
        st.error("❌ No text found. This PDF is likely a scanned image. Please use a text-based PDF where you can select and copy text.")
        st.stop()

    if char_count < 500:
        st.error(
            f"❌ Only **{char_count} characters** extracted — too little to fact-check.\n\n"
            "**Possible reasons:** scanned image PDF · nearly empty file · wrong file uploaded.\n\n"
            "Please upload a text-based PDF with actual written content."
        )
        st.stop()

    st.success(f"✅ Extracted **{char_count:,} characters** from `{uploaded.name}`")

    # Step 2 — Extract Claims
    with st.spinner("🧠 Identifying factual claims with AI… (15–30 seconds)"):
        claims = extract_claims_ai(raw_text)

    if not claims:
        st.error(
            "❌ No verifiable claims found.\n\n"
            "Make sure the PDF has specific **statistics, numbers, dates, or named facts** — not just general text."
        )
        st.stop()

    st.success(f"✅ Found **{len(claims)} verifiable claims**")

    with st.expander(f"📋 View all {len(claims)} extracted claims", expanded=False):
        for i, c in enumerate(claims, 1):
            st.markdown(
                f"<div style='padding:0.5rem 0;color:#94A3B8;font-size:0.88rem;"
                f"border-bottom:1px solid #1E2D3D;line-height:1.6;'>"
                f"<span style='color:#6366F1;font-weight:700;margin-right:0.75rem;'>{i}.</span>"
                f"{html_lib.escape(c)}</div>",
                unsafe_allow_html=True,
            )

    # Step 3 — Verify
    st.markdown(
        f"<div style='font-size:1.1rem;font-weight:700;color:#E2E8F0;margin:2rem 0 0.25rem;'>"
        f"🌐 Verifying {len(claims)} claims against live web data</div>"
        f"<div style='font-size:0.85rem;color:#475569;margin-bottom:1rem;'>"
        f"Estimated time: {len(claims)*4}–{len(claims)*6} seconds</div>",
        unsafe_allow_html=True,
    )

    progress_bar = st.progress(0)
    status_text  = st.empty()
    counts  = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    stats_ph = st.empty()

    def render_stats(c):
        stats_ph.markdown(f"""
        <div class="stats-container">
            <div class="stat-box verified">
                <div class="stat-num verified">{c['Verified']}</div>
                <div class="stat-label">✅ Verified</div>
            </div>
            <div class="stat-box inaccurate">
                <div class="stat-num inaccurate">{c['Inaccurate']}</div>
                <div class="stat-label">⚠️ Inaccurate</div>
            </div>
            <div class="stat-box false">
                <div class="stat-num false">{c['False']}</div>
                <div class="stat-label">❌ False</div>
            </div>
            <div class="stat-box unverified">
                <div class="stat-num unverified">{c['Unverified']}</div>
                <div class="stat-label">❓ Unverified</div>
            </div>
        </div>""", unsafe_allow_html=True)

    render_stats(counts)
    claims_container = st.container()
    all_cards_html   = []

    ICONS = {"Verified":"✅","Inaccurate":"⚠️","False":"❌","Unverified":"❓"}
    PILLS = {"Verified":"pill-verified","Inaccurate":"pill-inaccurate",
             "False":"pill-false","Unverified":"pill-unverified"}

    # ── Parallel verification — all claims at once ──
    status_text.markdown(
        "<div style='font-size:0.85rem;color:#64748B;padding:0.4rem 0;'>"
        "⚡ Verifying all claims in parallel…</div>",
        unsafe_allow_html=True,
    )

    results = [None] * len(claims)

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {executor.submit(verify_claim, claim): i for i, claim in enumerate(claims)}
        done_count = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
            except Exception:
                result = {"verdict": "Unverified", "confidence": "Low",
                          "explanation": "Verification failed.", "correct_fact": None}
            result["claim"] = claims[idx]
            results[idx] = result

            v = result.get("verdict", "Unverified")
            counts[v] = counts.get(v, 0) + 1
            done_count += 1
            render_stats(counts)
            progress_bar.progress(done_count / len(claims))

    status_text.empty()

    # Render all cards in order
    for result in results:
        v  = result.get("verdict", "Unverified")
        cf = result.get("correct_fact")
        correct_html = ""
        if cf and str(cf).strip().lower() not in ("null", "none", "", "n/a"):
            correct_html = (
                f"<div class='correct-fact'>"
                f"<span class='correct-label'>✓ Correct fact</span>"
                f"{html_lib.escape(str(cf))}</div>"
            )
        card_html = (
            f"<div class='claim-card {v.lower()}'>"
            f"<div class='verdict-pill {PILLS.get(v,'pill-unverified')}'>"
            f"{ICONS.get(v,'❓')} {v} &nbsp;·&nbsp; {result.get('confidence','Low')} confidence</div>"
            f"<div class='claim-text'>\"{html_lib.escape(result['claim'])}\"</div>"
            f"<div class='claim-exp'>{html_lib.escape(result.get('explanation',''))}</div>"
            f"{correct_html}</div>"
        )
        all_cards_html.append(card_html)

    with claims_container:
        st.markdown("".join(all_cards_html), unsafe_allow_html=True)

    # Step 4 — Final Summary
    elapsed  = time.time() - start_time
    total    = len(results)
    flagged  = counts["Inaccurate"] + counts["False"]
    verified = counts["Verified"]
    accuracy = round(verified / total * 100) if total else 0
    acc_color = "#10B981" if accuracy >= 70 else "#F59E0B" if accuracy >= 40 else "#EF4444"

    st.markdown(f"""
    <div style="background:#0D1117;border:1px solid #1E2D3D;border-radius:20px;
                padding:2rem;margin-top:2rem;text-align:center;">
        <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;
                    color:#475569;margin-bottom:0.5rem;">Final Report</div>
        <div style="font-size:3rem;font-weight:700;color:{acc_color};line-height:1;margin-bottom:0.5rem;">
            {accuracy}%</div>
        <div style="font-size:1rem;color:#94A3B8;margin-bottom:0.25rem;">accuracy rate</div>
        <div style="font-size:0.85rem;color:#475569;margin-top:0.5rem;">
            {verified} verified &nbsp;·&nbsp; {flagged} flagged &nbsp;·&nbsp;
            {counts['Unverified']} unverified &nbsp;·&nbsp; {elapsed:.1f}s
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if flagged > 0:
        st.warning(f"⚠️ **{flagged} claim{'s' if flagged!=1 else ''} flagged** as Inaccurate or False — see correct facts in green above.")
    elif verified == total:
        st.success(f"🎉 All {total} claims verified as accurate!")
    else:
        st.info(f"✅ {verified} of {total} claims verified. {counts['Unverified']} could not be confirmed.")
