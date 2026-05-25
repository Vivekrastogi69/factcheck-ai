import streamlit as st
import pdfplumber
import anthropic
import json
import re
import time
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactCheck AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0f1117; }

.hero {
    background: linear-gradient(135deg, #1a1f2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
    border: 1px solid #2d3561;
    text-align: center;
}
.hero h1 { color: #fff; font-size: 2.4rem; font-weight: 700; margin: 0; }
.hero p  { color: #94a3b8; font-size: 1rem; margin: 0.5rem 0 0; }

.claim-card {
    background: #1e2130;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    border-left: 4px solid #334155;
    transition: all 0.2s;
}
.claim-card.verified  { border-left-color: #10b981; background: #0d2b1f; }
.claim-card.inaccurate{ border-left-color: #f59e0b; background: #2b1f0d; }
.claim-card.false     { border-left-color: #ef4444; background: #2b0d0d; }
.claim-card.unverified{ border-left-color: #6366f1; background: #1a1b2e; }

.badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-verified  { background:#065f46; color:#6ee7b7; }
.badge-inaccurate{ background:#78350f; color:#fcd34d; }
.badge-false     { background:#7f1d1d; color:#fca5a5; }
.badge-unverified{ background:#312e81; color:#a5b4fc; }

.claim-text   { color:#e2e8f0; font-size:0.95rem; margin:0.4rem 0; }
.verdict-text { color:#94a3b8; font-size:0.85rem; margin-top:0.5rem; }
.correct-fact { color:#34d399; font-size:0.85rem; font-weight:500; margin-top:0.3rem; }
.source-link  { color:#60a5fa; font-size:0.78rem; }

.stat-box {
    background:#1e2130;
    border-radius:10px;
    padding:1rem;
    text-align:center;
    border:1px solid #2d3748;
}
.stat-num  { font-size:2rem; font-weight:700; }
.stat-label{ color:#94a3b8; font-size:0.8rem; margin-top:2px; }

.step-pill {
    display:inline-block;
    background:#1e2130;
    border:1px solid #334155;
    border-radius:999px;
    padding:4px 14px;
    font-size:0.78rem;
    color:#94a3b8;
    margin:3px;
}

.stButton > button {
    background: linear-gradient(135deg,#6366f1,#8b5cf6) !important;
    color:#fff !important;
    border:none !important;
    border-radius:8px !important;
    font-weight:600 !important;
    padding:0.6rem 2rem !important;
    font-size:1rem !important;
    transition:all 0.2s !important;
}
.stButton > button:hover { opacity:0.9; transform:translateY(-1px); }

.upload-area {
    background:#1e2130;
    border:2px dashed #334155;
    border-radius:12px;
    padding:2rem;
    text-align:center;
    margin-bottom:1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔍 FactCheck AI</h1>
  <p>Upload a PDF — AI extracts claims, searches the live web, and flags what's true, outdated, or false.</p>
</div>
""", unsafe_allow_html=True)

# ── How it works ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-bottom:1.5rem;">
  <span class="step-pill">📄 1. Upload PDF</span>
  <span class="step-pill">🤖 2. AI Extracts Claims</span>
  <span class="step-pill">🌐 3. Live Web Search</span>
  <span class="step-pill">🏷️ 4. Verdict Report</span>
</div>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_text_from_pdf(uploaded_file) -> str:
    with pdfplumber.open(uploaded_file) as pdf:
        pages_text = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
    return "\n\n".join(pages_text)


def extract_claims(client: anthropic.Anthropic, text: str) -> list[dict]:
    prompt = f"""You are a fact-extraction AI. Read the document below and extract ALL verifiable factual claims.

Focus on:
- Statistics and percentages
- Dates and time periods
- Financial figures (revenue, market cap, growth %)
- Technical specifications / version numbers
- Named research findings or survey results
- Population or user counts

Return ONLY a JSON array (no markdown, no explanation) with this schema:
[
  {{
    "id": 1,
    "claim": "Exact claim text",
    "category": "statistic|date|financial|technical|research|other",
    "source_context": "brief surrounding context"
  }}
]

Extract at least 5 and at most 20 claims.

DOCUMENT:
{text[:8000]}
"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).rstrip("```").strip()
    return json.loads(raw)


def verify_claim(client: anthropic.Anthropic, claim: dict) -> dict:
    prompt = f"""You are a fact-checking AI with access to web search.

Verify this claim using your web search tool, then return a JSON verdict.

CLAIM: "{claim['claim']}"
CATEGORY: {claim['category']}

Search for the most recent, authoritative data on this claim.

Return ONLY valid JSON (no markdown):
{{
  "verdict": "Verified" | "Inaccurate" | "False" | "Unverified",
  "confidence": "High" | "Medium" | "Low",
  "explanation": "Brief explanation of verdict (1-2 sentences)",
  "correct_fact": "The actual correct fact if claim is wrong, else null",
  "sources": ["source name or URL"]
}}

Verdict guide:
- Verified   = claim matches current data
- Inaccurate = claim was once true but is now outdated, or the number is wrong
- False      = claim has no credible support or contradicts evidence
- Unverified = insufficient public data to confirm or deny
"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    # Collect text blocks
    text_blocks = [b.text for b in response.content if b.type == "text"]
    raw = " ".join(text_blocks).strip()
    # Extract JSON
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        raw = match.group(0)
    try:
        result = json.loads(raw)
    except Exception:
        result = {
            "verdict": "Unverified",
            "confidence": "Low",
            "explanation": "Could not parse AI response.",
            "correct_fact": None,
            "sources": []
        }
    result["claim"] = claim["claim"]
    result["category"] = claim["category"]
    result["id"] = claim["id"]
    return result


def badge_html(verdict: str) -> str:
    mapping = {
        "Verified":   ("verified",   "✅ Verified"),
        "Inaccurate": ("inaccurate", "⚠️ Inaccurate"),
        "False":      ("false",      "❌ False"),
        "Unverified": ("unverified", "❓ Unverified"),
    }
    cls, label = mapping.get(verdict, ("unverified", verdict))
    return f'<span class="badge badge-{cls}">{label}</span>'


def render_claim_card(r: dict):
    verdict = r.get("verdict", "Unverified")
    cls_map = {"Verified":"verified","Inaccurate":"inaccurate","False":"false","Unverified":"unverified"}
    card_cls = cls_map.get(verdict, "unverified")
    correct = f'<p class="correct-fact">✅ Correct fact: {r["correct_fact"]}</p>' if r.get("correct_fact") else ""
    sources_html = ""
    if r.get("sources"):
        links = " · ".join(f'<span class="source-link">{s}</span>' for s in r["sources"][:3])
        sources_html = f'<p style="margin-top:0.4rem;">{links}</p>'
    conf_color = {"High":"#10b981","Medium":"#f59e0b","Low":"#ef4444"}.get(r.get("confidence",""), "#94a3b8")
    st.markdown(f"""
    <div class="claim-card {card_cls}">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
        {badge_html(verdict)}
        <span style="font-size:0.75rem;color:{conf_color};font-weight:600;">
          {r.get('confidence','?')} confidence &nbsp;·&nbsp; #{r.get('id','')} &nbsp;·&nbsp; {r.get('category','').upper()}
        </span>
      </div>
      <p class="claim-text">"{r['claim']}"</p>
      <p class="verdict-text">{r.get('explanation','')}</p>
      {correct}
      {sources_html}
    </div>
    """, unsafe_allow_html=True)


# ── Main UI ───────────────────────────────────────────────────────────────────

col_upload, col_info = st.columns([2, 1])

with col_upload:
    api_key = st.text_input(
        "🔑 Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Your key is used only for this session and never stored."
    )
    uploaded_file = st.file_uploader("📄 Upload PDF", type=["pdf"])

with col_info:
    st.markdown("""
    <div class="stat-box" style="margin-bottom:0.8rem;">
      <div class="stat-num" style="color:#6366f1;">3</div>
      <div class="stat-label">Verdict Types</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#1e2130;border-radius:10px;padding:1rem;border:1px solid #2d3748;font-size:0.82rem;color:#94a3b8;">
      <b style="color:#e2e8f0;">What gets checked?</b><br><br>
      📊 Statistics & percentages<br>
      📅 Dates & timelines<br>
      💰 Financial figures<br>
      🔧 Technical specs<br>
      🔬 Research findings
    </div>
    """, unsafe_allow_html=True)

# ── Run Button ────────────────────────────────────────────────────────────────
run = st.button("🚀 Start Fact-Check", use_container_width=True)

if run:
    if not api_key:
        st.error("Please enter your Anthropic API key.")
        st.stop()
    if not uploaded_file:
        st.error("Please upload a PDF file.")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)

    # ── Step 1: Extract text
    with st.spinner("📄 Extracting text from PDF…"):
        try:
            pdf_text = extract_text_from_pdf(uploaded_file)
        except Exception as e:
            st.error(f"PDF read error: {e}")
            st.stop()

    if not pdf_text.strip():
        st.error("No text found in PDF. Try a text-based PDF.")
        st.stop()

    st.success(f"✅ Extracted {len(pdf_text):,} characters from PDF")

    # ── Step 2: Extract claims
    with st.spinner("🤖 AI is extracting verifiable claims…"):
        try:
            claims = extract_claims(client, pdf_text)
        except Exception as e:
            st.error(f"Claim extraction failed: {e}")
            st.stop()

    st.info(f"🎯 Found **{len(claims)}** verifiable claims — starting web verification…")

    # ── Step 3: Verify each claim
    results = []
    progress = st.progress(0)
    status   = st.empty()

    for i, claim in enumerate(claims):
        status.markdown(f"🌐 Verifying claim {i+1}/{len(claims)}: *{claim['claim'][:80]}…*")
        try:
            r = verify_claim(client, claim)
        except Exception as e:
            r = {
                "id": claim["id"], "claim": claim["claim"],
                "category": claim["category"],
                "verdict": "Unverified", "confidence": "Low",
                "explanation": str(e), "correct_fact": None, "sources": []
            }
        results.append(r)
        progress.progress((i + 1) / len(claims))
        time.sleep(0.3)   # be nice to API rate limits

    status.empty()
    progress.empty()

    # ── Step 4: Summary stats
    st.markdown("---")
    st.markdown("## 📊 Fact-Check Report")
    st.markdown(f"*Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*")

    counts = {"Verified":0,"Inaccurate":0,"False":0,"Unverified":0}
    for r in results:
        v = r.get("verdict","Unverified")
        counts[v] = counts.get(v,0)+1

    c1,c2,c3,c4 = st.columns(4)
    for col, (label, color, icon) in zip(
        [c1,c2,c3,c4],
        [("Verified","#10b981","✅"),("Inaccurate","#f59e0b","⚠️"),
         ("False","#ef4444","❌"),("Unverified","#6366f1","❓")]
    ):
        with col:
            st.markdown(f"""
            <div class="stat-box">
              <div class="stat-num" style="color:{color};">{icon} {counts[label]}</div>
              <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    # ── Step 5: Detailed cards
    st.markdown("### 🔎 Detailed Results")

    tabs = st.tabs(["All Claims","✅ Verified","⚠️ Inaccurate","❌ False","❓ Unverified"])
    groups = {
        "All Claims":  results,
        "✅ Verified":   [r for r in results if r["verdict"]=="Verified"],
        "⚠️ Inaccurate": [r for r in results if r["verdict"]=="Inaccurate"],
        "❌ False":       [r for r in results if r["verdict"]=="False"],
        "❓ Unverified":  [r for r in results if r["verdict"]=="Unverified"],
    }
    for tab, (label, items) in zip(tabs, groups.items()):
        with tab:
            if not items:
                st.info(f"No claims in this category.")
            for r in items:
                render_claim_card(r)

    # ── Download JSON report
    report_json = json.dumps({
        "generated_at": datetime.now().isoformat(),
        "summary": counts,
        "results": results
    }, indent=2)
    st.download_button(
        "⬇️ Download Full Report (JSON)",
        data=report_json,
        file_name="factcheck_report.json",
        mime="application/json"
    )
