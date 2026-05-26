import streamlit as st
import pdfplumber
import requests
import json
import re
import time
import html as html_lib
import os

# ============================================================
# CONFIG — Streamlit Secrets > Env Vars > Hardcoded fallback
# ============================================================
try:
    GROQ_API_KEY   = st.secrets["GROQ_API_KEY"]
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except Exception:
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "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")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY",  "c04f1c3f9bcd7ef89ffe4e6264e672901cd94112")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

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
# CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
.stApp { background: #080B14; color: #E2E8F0; }
[data-testid="stSidebar"] { background: #0D1117 !important; border-right: 1px solid #1E2D3D !important; }

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
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1rem !important; font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 24px rgba(99,102,241,0.3) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    box-shadow: 0 8px 32px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
}

/* Stats grid */
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
.pill-false      { background: rgba(239,68,68,0.1);  color: #EF4444; border: 1px solid rgba(239,68,68,0.3);  }
.pill-unverified { background: rgba(99,102,241,0.1); color: #818CF8; border: 1px solid rgba(99,102,241,0.3); }

.claim-text {
    font-family: 'JetBrains Mono', monospace; font-size: 0.88rem; color: #E2E8F0;
    background: rgba(255,255,255,0.03); border: 1px solid #1E2D3D;
    border-radius: 8px; padding: 0.75rem 1rem;
    margin-bottom: 0.75rem; line-height: 1.6;
}
.claim-exp  { font-size: 0.9rem; color: #94A3B8; line-height: 1.7; }
.correct-fact {
    margin-top: 0.75rem; padding: 0.6rem 1rem;
    background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2);
    border-radius: 8px; font-size: 0.85rem; color: #34D399;
}
.correct-label {
    font-weight: 700; font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.08em; display: block; margin-bottom: 0.2rem; color: #10B981;
}

/* Sidebar dot */
.status-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    background: #10B981; box-shadow: 0 0 8px #10B981; animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Progress bar */
.stProgress > div > div > div { background: linear-gradient(135deg, #6366F1, #8B5CF6) !important; }

/* Expander */
.streamlit-expanderHeader {
    background: #0D1117 !important; border: 1px solid #1E2D3D !important;
    border-radius: 12px !important; color: #94A3B8 !important;
}

/* Success / Warning / Error */
.stSuccess, .stInfo { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0;">
        <div style="font-size:1.25rem;font-weight:700;color:#E2E8F0;margin-bottom:1.5rem;">🔍 FactCheck AI</div>

        <div style="margin-bottom:0.6rem;display:flex;align-items:center;gap:0.6rem;">
            <span class="status-dot"></span>
            <span style="font-size:0.85rem;color:#94A3B8;">Groq LLM — Active</span>
        </div>
        <div style="margin-bottom:1.5rem;display:flex;align-items:center;gap:0.6rem;">
            <span class="status-dot"></span>
            <span style="font-size:0.85rem;color:#94A3B8;">Serper Web Search — Live</span>
        </div>

        <div style="border-top:1px solid #1E2D3D;padding-top:1rem;margin-bottom:1.5rem;">
            <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin-bottom:0.75rem;">How it works</div>
            <div style="font-size:0.82rem;color:#64748B;line-height:2;">
                1. 📄 Extract full claims from PDF<br>
                2. 🌐 Live Google search per claim<br>
                3. 🤖 AI verdict + evidence<br>
                4. 📊 Report with correct facts
            </div>
        </div>

        <div style="border-top:1px solid #1E2D3D;padding-top:1rem;">
            <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin-bottom:0.75rem;">Verdict Guide</div>
            <div style="font-size:0.82rem;line-height:2.2;">
                <span style="color:#10B981;">✅ Verified</span> — Confirmed accurate<br>
                <span style="color:#F59E0B;">⚠️ Inaccurate</span> — Wrong number/date<br>
                <span style="color:#EF4444;">❌ False</span> — No evidence found<br>
                <span style="color:#818CF8;">❓ Unverified</span> — Cannot confirm
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
    """Search Google via Serper and return top snippets."""
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 6},
            timeout=20,
        )
        r.raise_for_status()
        snippets = [
            f"[{item.get('title', '')}] {item.get('snippet', '')}"
            for item in r.json().get("organic", [])[:6]
            if item.get("snippet")
        ]
        return "\n\n".join(snippets)
    except Exception:
        return ""


def call_groq(prompt: str, max_tokens: int = 800, retries: int = 4) -> str:
    """Call Groq API with exponential back-off on rate limits."""
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
    """Extract all text from a PDF using pdfplumber."""
    try:
        with pdfplumber.open(file) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages_text)
    except Exception as e:
        return ""


def extract_claims_ai(text: str) -> list:
    """
    Use LLaMA 3.3 70B to extract complete, verifiable factual claims.
    Returns full sentences — never bare numbers or fragments.
    """
    prompt = f"""You are a claim extractor for a professional fact-checking system.

Your task: Extract every SPECIFIC, VERIFIABLE factual claim from the document below.

STRICT RULES:
- Each claim MUST be a COMPLETE SENTENCE: subject + verb + exact figure/fact + context
- GOOD: "Tesla sold 2.5 million vehicles globally in 2024"
- BAD: "2.5 million" or "sold vehicles" — fragments are INVALID and will be rejected
- Always include the full entity name (company, person, country) — never orphaned numbers
- Preserve exact numbers, dates, percentages, and names exactly as written
- Extract maximum 15 claims

Return ONLY a valid JSON array of strings. No markdown, no backticks, no explanation.
Format: ["Claim one here.", "Claim two here.", "Claim three here."]

DOCUMENT TEXT:
{text[:8000]}"""

    raw = call_groq(prompt, max_tokens=1500)

    # Try to parse JSON array from response
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            claims = json.loads(match.group())
            valid = []
            for c in claims:
                c = str(c).strip().strip('"').strip("'")
                # Must be a full sentence (>20 chars) and not a bare number
                is_fragment = re.match(r'^\$?[\d,.]+ ?(million|billion|thousand|%)?$', c, re.I)
                if len(c) > 20 and not is_fragment:
                    valid.append(c)
            return valid[:15]
        except (json.JSONDecodeError, Exception):
            pass

    # Regex fallback — numbered lines (handles "1. Claim" and '1. "Claim"')
    claims = []
    patterns = [
        r'\d+[\.\)]\s*"([^"]{20,})"',
        r'\d+[\.\)]\s*([A-Z][^.\n]{20,}\.)',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            c = m.group(1).strip()
            if c and c not in claims:
                claims.append(c)
    return claims[:15]


def verify_claim(claim: str) -> dict:
    """
    Verify a single claim against live web data.
    Returns verdict, confidence, explanation, and correct_fact.
    """
    search_results = serper_search(claim)

    prompt = f"""You are a professional fact-checker with access to live web search results.

CLAIM TO VERIFY: "{claim}"

LIVE WEB SEARCH RESULTS:
{search_results if search_results else "No search results available — use your training knowledge to verify."}

INSTRUCTIONS:
1. Carefully compare the claim against the search evidence
2. Choose the most accurate verdict:
   - "Verified"   = claim is accurate and directly supported by evidence
   - "Inaccurate" = right topic but wrong number, date, or scale (e.g. outdated/exaggerated stat)
   - "False"      = claim is clearly wrong, evidence directly contradicts it
   - "Unverified" = insufficient evidence to confirm or deny

3. If verdict is Inaccurate or False, provide the REAL correct fact.

Respond ONLY with a valid JSON object. No markdown, no backticks, nothing else:
{{"verdict":"Verified|Inaccurate|False|Unverified","confidence":"High|Medium|Low","explanation":"One precise sentence citing specific evidence or numbers.","correct_fact":"The accurate real-world fact with context, or null if Verified/Unverified"}}"""

    try:
        raw = call_groq(prompt, max_tokens=600)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            # Validate verdict
            if result.get("verdict") not in ("Verified", "Inaccurate", "False", "Unverified"):
                result["verdict"] = "Unverified"
            # Clean up correct_fact
            cf = result.get("correct_fact", "")
            if str(cf).lower() in ("null", "none", "", "n/a"):
                result["correct_fact"] = None
            return result
    except Exception:
        pass

    return {
        "verdict": "Unverified",
        "confidence": "Low",
        "explanation": "Could not retrieve verification data for this claim.",
        "correct_fact": None,
    }


# ============================================================
# MAIN UI — Upload + Run
# ============================================================
st.markdown("""
<div style="background:#0D1117;border:1px solid #1E2D3D;border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;">
    <div style="font-size:0.9rem;color:#64748B;line-height:1.8;">
        📋 <strong style="color:#94A3B8;">Supported PDFs:</strong> Any text-based PDF — annual reports, research papers, marketing docs, press releases, articles.<br>
        ⚠️ <strong style="color:#94A3B8;">Not supported:</strong> Scanned/image PDFs (no selectable text).
    </div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Drop your PDF here or click to browse",
    type=["pdf"],
    help="Text-based PDFs only. Max 200MB.",
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run = st.button("🔍  Run Fact-Check", use_container_width=True)

# ============================================================
# RUN PIPELINE
# ============================================================
if run:
    if not uploaded:
        st.error("⚠️ Please upload a PDF file first.")
        st.stop()

    start_time = time.time()

    # ── Step 1: Extract PDF Text ──
    with st.spinner("📄 Reading PDF…"):
        raw_text = extract_pdf_text(uploaded)

    char_count = len(raw_text.strip())

    if char_count == 0:
        st.error("❌ Could not extract any text from this PDF. It may be a scanned/image-based PDF. Please use a text-based PDF where you can select/copy text.")
        st.stop()

    if char_count < 500:
        st.error(
            f"❌ Only **{char_count} characters** extracted from this PDF — too little to fact-check.\n\n"
            f"**Possible reasons:**\n"
            f"- PDF is a scanned image (not supported)\n"
            f"- PDF is nearly empty\n"
            f"- Wrong file uploaded\n\n"
            f"Please upload a text-based PDF with actual written content."
        )
        st.stop()

    st.success(f"✅ Extracted **{char_count:,} characters** from `{uploaded.name}`")

    # ── Step 2: Extract Claims ──
    with st.spinner("🧠 Identifying factual claims with AI… (15–30 seconds)"):
        claims = extract_claims_ai(raw_text)

    if not claims:
        st.error(
            "❌ No verifiable claims found in this PDF.\n\n"
            "**Make sure your PDF contains:**\n"
            "- Specific statistics or numbers\n"
            "- Named companies, people, or countries\n"
            "- Dates or financial figures\n\n"
            "General text without specific facts cannot be fact-checked."
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

    # ── Step 3: Verify Each Claim ──
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:700;color:#E2E8F0;margin:2rem 0 0.5rem 0;'>"
        "🌐 Verifying claims against live web data</div>"
        "<div style='font-size:0.85rem;color:#475569;margin-bottom:1rem;'>"
        f"Checking {len(claims)} claims — approximately {len(claims) * 4}–{len(claims) * 6} seconds</div>",
        unsafe_allow_html=True,
    )

    progress_bar = st.progress(0)
    status_text  = st.empty()

    results = []
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

    ICONS = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "❓"}
    PILLS = {
        "Verified":   "pill-verified",
        "Inaccurate": "pill-inaccurate",
        "False":      "pill-false",
        "Unverified": "pill-unverified",
    }

    for i, claim in enumerate(claims):
        status_text.markdown(
            f"<div style='font-size:0.85rem;color:#64748B;padding:0.5rem 0;'>"
            f"🔎 Verifying {i+1} of {len(claims)}: "
            f"<em style='color:#94A3B8;'>{html_lib.escape(claim[:90])}…</em></div>",
            unsafe_allow_html=True,
        )

        result = verify_claim(claim)
        result["claim"] = claim
        results.append(result)

        v = result.get("verdict", "Unverified")
        counts[v] = counts.get(v, 0) + 1
        render_stats(counts)

        # Build correct fact block
        cf = result.get("correct_fact")
        correct_html = ""
        if cf and str(cf).strip().lower() not in ("null", "none", "", "n/a"):
            correct_html = (
                f"<div class='correct-fact'>"
                f"<span class='correct-label'>✓ Correct fact</span>"
                f"{html_lib.escape(str(cf))}"
                f"</div>"
            )

        # Build claim card
        card_html = (
            f"<div class='claim-card {v.lower()}'>"
            f"<div class='verdict-pill {PILLS.get(v, 'pill-unverified')}'>"
            f"{ICONS.get(v, '❓')} {v} &nbsp;·&nbsp; {result.get('confidence', 'Low')} confidence"
            f"</div>"
            f"<div class='claim-text'>\"{html_lib.escape(claim)}\"</div>"
            f"<div class='claim-exp'>{html_lib.escape(result.get('explanation', ''))}</div>"
            f"{correct_html}"
            f"</div>"
        )
        all_cards_html.append(card_html)

        with claims_container:
            st.markdown("".join(all_cards_html), unsafe_allow_html=True)

        progress_bar.progress((i + 1) / len(claims))
        time.sleep(2)  # Prevent Groq rate limiting

    status_text.empty()

    # ── Step 4: Final Summary ──
    elapsed  = time.time() - start_time
    total    = len(results)
    flagged  = counts["Inaccurate"] + counts["False"]
    verified = counts["Verified"]
    accuracy = round(verified / total * 100) if total else 0

    # Color for accuracy
    acc_color = "#10B981" if accuracy >= 70 else "#F59E0B" if accuracy >= 40 else "#EF4444"

    st.markdown(f"""
    <div style="background:#0D1117;border:1px solid #1E2D3D;border-radius:20px;
                padding:2rem;margin-top:2rem;text-align:center;">
        <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;
                    color:#475569;margin-bottom:0.5rem;">Final Report</div>
        <div style="font-size:3rem;font-weight:700;color:{acc_color};line-height:1;margin-bottom:0.5rem;">
            {accuracy}%
        </div>
        <div style="font-size:1rem;color:#94A3B8;margin-bottom:0.25rem;">accuracy rate</div>
        <div style="font-size:0.85rem;color:#475569;margin-top:0.5rem;">
            {verified} verified &nbsp;·&nbsp;
            {flagged} flagged &nbsp;·&nbsp;
            {counts['Unverified']} unverified &nbsp;·&nbsp;
            completed in {elapsed:.1f}s
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if flagged > 0:
        st.warning(
            f"⚠️ **{flagged} claim{'s' if flagged != 1 else ''} flagged** as Inaccurate or False. "
            f"See the correct facts highlighted in green inside each card above."
        )
    elif verified == total:
        st.success(f"🎉 All {total} claims verified as accurate!")
    else:
        st.info(f"✅ {verified} of {total} claims verified. {counts['Unverified']} could not be confirmed.")
