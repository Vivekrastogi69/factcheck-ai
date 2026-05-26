# 🔍 FactCheck AI — Automated Truth Layer

> An AI-powered fact-checking web app that extracts claims from PDFs and verifies them against live web data in real-time.

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Streamlit-FF4B4B?style=for-the-badge)](https://factcheck-ai-awpq2na5bgfenfjac34ruw.streamlit.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Source_Code-181717?style=for-the-badge&logo=github)](https://github.com/Vivekrastogi69/factcheck-ai/blob/main/app.py)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Vivek_Rastogi-0A66C2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/vivek-rastogi-78401430b/)

---

## 🎥 Demo Video

https://www.linkedin.com/posts/vivek-rastogi-78401430b_ai-productmanagement-factchecking-ugcPost-7464867372890398720--G1h/?utm_source=share&utm_medium=member_desktop&rcm=ACoAAE7YoFQBtnp4zwgU42L_px6gNqDmkH8pn3c

> 📌 Watch the full working demo: PDF upload → Claim extraction → Live verification → Results report

---

## 🌐 Live Links

| Resource | Link |
|----------|------|
| 🚀 Live Web App | [factcheck-ai-awpq2na5bgfenfjac34ruw.streamlit.app](https://factcheck-ai-awpq2na5bgfenfjac34ruw.streamlit.app/) |
| 💻 GitHub Repository | [github.com/Vivekrastogi69/factcheck-ai](https://github.com/Vivekrastogi69/factcheck-ai/blob/main/app.py) |
| 👤 Author (LinkedIn) | [linkedin.com/in/vivek-rastogi-78401430b](https://www.linkedin.com/in/vivek-rastogi-78401430b/) |

---

## ✨ Features

- 📄 **Upload any PDF** — marketing docs, reports, press releases, articles
- 🤖 **AI Claim Extraction** — LLaMA 3.3 70B identifies specific verifiable claims (stats, dates, figures)
- 🌐 **Live Web Search** — cross-references each claim against Google via Serper API
- 🚨 **Smart Classification** — flags claims as:
  - ✅ **Verified** — claim checks out
  - ⚠️ **Inaccurate** — partially wrong or outdated
  - ❌ **False** — contradicted by evidence
  - ❓ **Unverified** — insufficient data found
- 📊 **Summary Dashboard** — visual breakdown of all claim results
- 📜 **History Tracking** — keeps log of all past analyses
- 📥 **Export Reports** — download results as JSON

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit |
| **LLM** | Groq — LLaMA 3.3 70B Versatile |
| **Search** | Serper API (Google Search) |
| **PDF Parsing** | pdfplumber |
| **Deployment** | Streamlit Cloud |
| **Language** | Python |

---

## 📋 How It Works

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Upload    │────▶│   Extract   │────▶│  Live Search │────▶│   Report    │
│     PDF     │     │   Claims    │     │  (Serper)    │     │  Results    │
└─────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    Stats, Dates,          Google Search        Verified ✅
                    Financial data         cross-check          Inaccurate ⚠️
                                                                False ❌
```

**Step-by-step:**

1. **Upload PDF** — user uploads any document
2. **Extract Text** — pdfplumber parses all readable content
3. **Identify Claims** — Groq LLM picks out verifiable claims (statistics, dates, figures)
4. **Live Web Search** — Serper API queries Google for current facts
5. **Analyze & Verify** — LLM compares claims against real search results
6. **Display Results** — classified output with explanations and source links

---

## 📊 Sample Output

```
📊 SUMMARY
├── Total Claims: 10
├── Verified:    9 ✅
├── Inaccurate:  1 ⚠️
└── False:       0 ❌

🔎 DETAILED RESULTS

⚠️ INACCURATE
"At present, there is no drug that can prevent and treat the disease"
→ This claim is outdated. Treatments like Paxlovid, Remdesivir,
  and vaccines have been developed and approved since 2020.
📎 Sources: fda.gov | who.int

✅ VERIFIED
"Eating garlic does not prevent COVID-19"
→ Verified: No scientific evidence supports this claim.
📎 Sources: who.int | cdc.gov
```

---

## 📦 Local Installation

```bash
# Clone the repository
git clone https://github.com/Vivekrastogi69/factcheck-ai.git
cd factcheck-ai

# Install dependencies
pip install -r requirements.txt

# Set API keys
export GROQ_API_KEY="your_groq_key_here"
export SERPER_API_KEY="your_serper_key_here"

# Run the app
streamlit run app.py
```

---

## 🔑 API Keys Required

| Service | Purpose | Free Tier | Get It |
|---------|---------|-----------|--------|
| **Groq API** | LLM for claim extraction & reasoning | 30 req/min | [console.groq.com](https://console.groq.com) |
| **Serper API** | Google Search for live fact-checking | 2,500 searches/month | [serper.dev](https://serper.dev) |

---

## 🌐 Deployment

### Streamlit Cloud (Recommended — Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New App**
3. Connect your GitHub repo, set main file to `app.py`
4. Add secrets under **Advanced Settings**:

```toml
GROQ_API_KEY = "your_groq_key_here"
SERPER_API_KEY = "your_serper_key_here"
```

5. Click **Deploy** — your live URL will be: `https://your-app-name.streamlit.app`

### Render (Alternative)

1. Create account at [render.com](https://render.com)
2. New → **Web Service** → Connect GitHub repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Add environment variables: `GROQ_API_KEY`, `SERPER_API_KEY`

---

## 📁 Project Structure

```
factcheck-ai/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # Documentation
└── .streamlit/
    └── secrets.toml       # API keys (git-ignored)
```

---

## 🔒 Security Note

Never commit API keys directly in code. Use:
- **Streamlit Cloud** → Secrets management (TOML format)
- **Render** → Environment variables panel
- **Local** → `.env` file + `python-dotenv`

---

## 📈 Future Enhancements

- [ ] Support for DOCX and TXT file formats
- [ ] Multiple language support
- [ ] Real-time web search with more sources
- [ ] PDF highlighting of problematic claims
- [ ] Batch document processing
- [ ] Export to CSV / Excel

---

## 👨‍💻 Author

**Vivek Rastogi**  
Product Management Trainee Candidate — Cog Culture Assessment

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://www.linkedin.com/in/vivek-rastogi-78401430b/)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=flat&logo=github)](https://github.com/Vivekrastogi69/factcheck-ai)

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) — high-speed LLM inference
- [Serper](https://serper.dev) — real-time Google Search API
- [Streamlit](https://streamlit.io) — easy Python web app deployment

---

## 📄 License

MIT License — Free for educational and evaluation purposes.

---

*Built with ❤️ for Cog Culture Product Management Trainee Assessment*
