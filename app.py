import streamlit as st
import pdfplumber
import requests
import json
import re
import time

# ============================================
# CONFIG — replace with your own keys
# ============================================
GROQ_API_KEY = "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"
SERPER_API_KEY = "c04f1c3f9bcd7ef89ffe4e6264e672901cd94112"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(page_title="FactCheck AI", page_icon="✅", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #1a1a4a, #24243e); }
.hero { text-align: center; padding: 2rem; background: rgba(255,255,255,0.05);
        border-radius: 30px; margin-bottom: 2rem; }
.hero h1 { font-size: 2.5rem; background: linear-gradient(135deg, #fff, #6366f1);
           -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.claim-card { background: rgba(255,255,255,0.08); border-radius: 16px; padding: 1rem;
              margin-bottom: 1rem; border-left: 4px solid; }
.verified   { border-left-color: #10b981; }
.inaccurate { border-left-color: #f59e0b; }
.false      { border-left-color: #ef4444; }
.unverified { border-left-color: #6366f1; }
.stat-card  { background: rgba(255,255,255,0.08); border-radius: 20px;
              padding: 1rem; text-align: center; }
.stat-number { font-size: 2rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ✅ System Status")
    st.success("✅ Groq AI — Active")
    st.success("✅ Serper API — Live Search")

# ============================================
# HELPERS
# ============================================

def serper_search(query: str) -> str:
    """Return top-5 search snippets for a query, or empty string on failure."""
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(url, headers=headers,
                             json={"q": query, "num": 5}, timeout=20)
        resp.raise_for_status()
        snippets = [
            item.get("snippet", "")
            for item in resp.json().get("organic", [])[:5]
            if item.get("snippet")
        ]
        return "\n\n".join(snippets)
    except Exception:
        return ""


def call_groq(prompt: str, retries: int = 3) -> str:
    """Call Groq API with exponential back-off on rate limits."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 600,
    }
    for attempt in range(retries):
        try:
            resp = requests.post(GROQ_API_URL, headers=headers,
                                 json=body, timeout=45)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)          # 5s, 10s, 15s
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(3)
    return ""


def extract_claims_with_ai(text: str) -> list[str]:
    """Use Groq to extract factual claims from raw text."""
    prompt = f"""Extract every specific, verifiable factual claim from the text below.
Focus on: statistics, numbers, dates, names, financial figures, technical facts.
Return ONLY a JSON array of strings. No preamble, no markdown fences.

TEXT:
{text[:6000]}"""
    raw = call_groq(prompt)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            claims = json.loads(match.group())
            return [c.strip() for c in claims if isinstance(c, str) and len(c) > 10][:15]
        except json.JSONDecodeError:
            pass
    # Fallback: numbered-line pattern
    return extract_claims_regex(text)


def extract_claims_regex(text: str) -> list[str]:
    """Simple regex fallback — picks up numbered lines with or without quotes."""
    patterns = [
        r'\d+\.\s*"([^"]{10,})"',      # 1. "quoted claim"
        r'\d+\.\s*([A-Z][^.\n]{10,}\.)', # 1. Sentence starting with capital.
    ]
    claims = []
    for p in patterns:
        for m in re.finditer(p, text):
            c = m.group(1).strip()
            if c not in claims:
                claims.append(c)
    return claims[:15]


def verify_claim(claim: str) -> dict:
    """Verify a single claim against live web data."""
    search_results = serper_search(claim)

    prompt = f"""Fact-check the claim below using the provided search results.

CLAIM: "{claim}"

SEARCH RESULTS:
{search_results or "No results available — use your knowledge."}

Respond with ONLY a valid JSON object (no markdown, no extra text):
{{
  "verdict": "Verified|Inaccurate|False|Unverified",
  "confidence": "High|Medium|Low",
  "explanation": "One concise sentence.",
  "correct_fact": "The accurate figure/fact, or null"
}}"""

    try:
        raw = call_groq(prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "verdict": "Unverified",
        "confidence": "Low",
        "explanation": "Could not verify at this time.",
        "correct_fact": None,
    }


def extract_pdf_text(file) -> str:
    with pdfplumber.open(file) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


# ============================================
# UI
# ============================================
st.markdown("""
<div class="hero">
    <h1>✅ FactCheck AI</h1>
    <p style="color:#a5b4fc">Upload PDF → Live Web Search → Get Verdicts</p>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload a PDF document", type=["pdf"])

if st.button("🔍 Start Fact-Checking", use_container_width=True):
    if not uploaded:
        st.error("Please upload a PDF first.")
        st.stop()

    start = time.time()

    # --- Extract text ---
    with st.spinner("Reading PDF…"):
        text = extract_pdf_text(uploaded)
    if not text.strip():
        st.error("Could not extract text from this PDF. Is it a scanned image?")
        st.stop()
    st.success(f"✅ Extracted {len(text):,} characters")

    # --- Extract claims ---
    with st.spinner("Identifying factual claims…"):
        claims = extract_claims_with_ai(text)

    if not claims:
        st.warning("No specific claims found. Make sure the PDF contains numbered statements or statistics.")
        st.stop()
    st.success(f"✅ Found {len(claims)} claims")

    with st.expander("View extracted claims"):
        for i, c in enumerate(claims, 1):
            st.write(f"{i}. {c}")

    # --- Verify claims ---
    results = []
    progress = st.progress(0)
    status = st.empty()

    for i, claim in enumerate(claims):
        status.info(f"Verifying {i + 1}/{len(claims)}: {claim[:60]}…")
        result = verify_claim(claim)
        result["claim"] = claim
        results.append(result)
        progress.progress((i + 1) / len(claims))
        time.sleep(2)   # respectful delay between API calls

    status.empty()
    elapsed = time.time() - start

    # --- Summary stats ---
    st.markdown("---")
    st.markdown("## 📊 Fact-Check Report")
    st.caption(f"Completed in {elapsed:.1f}s")

    counts = {"Verified": 0, "Inaccurate": 0, "False": 0, "Unverified": 0}
    for r in results:
        v = r.get("verdict", "Unverified")
        counts[v] = counts.get(v, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#10b981'>✅ {counts['Verified']}</div><div>Verified</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#f59e0b'>⚠️ {counts['Inaccurate']}</div><div>Inaccurate</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#ef4444'>❌ {counts['False']}</div><div>False</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='stat-card'><div class='stat-number' style='color:#6366f1'>❓ {counts['Unverified']}</div><div>Unverified</div></div>", unsafe_allow_html=True)

    # --- Claim cards ---
    st.markdown("### Claim-by-claim verdicts")
    ICONS = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "❓"}

    for item in results:
        v = item.get("verdict", "Unverified")
        icon = ICONS.get(v, "❓")
        css_cls = v.lower()
        correct_html = ""
        cf = item.get("correct_fact")
        if cf and cf not in (None, "null", ""):
            correct_html = f"<p style='color:#34d399;margin-top:6px'><strong>✅ Correct fact:</strong> {cf}</p>"

        st.markdown(f"""
        <div class="claim-card {css_cls}">
            <span style="background:rgba(99,102,241,0.2);padding:0.2rem 0.8rem;border-radius:20px;font-size:0.85rem">
                {icon} {v} &nbsp;·&nbsp; {item.get('confidence','Low')} confidence
            </span>
            <p style="margin-top:8px"><strong>"{item['claim']}"</strong></p>
            <p style="color:#cbd5e1">{item.get('explanation', '')}</p>
            {correct_html}
        </div>
        """, unsafe_allow_html=True)

    st.balloons()
    st.success(f"✅ Done in {elapsed:.1f}s!")
