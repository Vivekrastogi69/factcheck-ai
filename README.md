# 🔍 FactCheck AI — Automated PDF Fact-Checking Agent

A Streamlit web app that reads any PDF, extracts verifiable claims, searches the live web, and flags each claim as **Verified**, **Inaccurate**, or **False**.

## 🚀 Live Demo
> Deploy to Streamlit Cloud (see below) and paste your URL here.

---

## ✨ Features

| Feature | Detail |
|---|---|
| 📄 PDF Upload | Drag-and-drop any PDF |
| 🤖 AI Claim Extraction | Claude extracts stats, dates, figures, research claims |
| 🌐 Live Web Verification | Claude's built-in web search cross-references each claim |
| 🏷️ Verdict Labels | Verified ✅ · Inaccurate ⚠️ · False ❌ · Unverified ❓ |
| 📊 Summary Dashboard | Count cards + filterable tabs |
| ⬇️ JSON Export | Full report download |

---

## 🛠️ Tech Stack

- **Frontend & Backend**: [Streamlit](https://streamlit.io/)
- **AI Model**: Claude Sonnet (Anthropic API)
- **Web Search**: Claude's native `web_search_20250305` tool
- **PDF Parsing**: pdfplumber

---

## 📦 Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/factcheck-ai
cd factcheck-ai

pip install -r requirements.txt

streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

You'll be prompted to enter your **Anthropic API Key** in the app UI. Get one at [console.anthropic.com](https://console.anthropic.com).

---

## ☁️ Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → select your repo → set `app.py` as the main file
4. Click **Deploy** — done! 🎉

> No secrets needed — users enter their own API key in the UI.

---

## 📁 Project Structure

```
factcheck-ai/
├── app.py            # Main Streamlit application
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## 🧪 Evaluation / Trap Document Test

Upload any PDF with intentional lies or outdated statistics. The app will:
1. Extract all verifiable claims automatically
2. Search the live web for each one
3. Flag outdated/wrong claims with the **correct real fact**

---

## 📝 License

MIT — free to use, modify, and deploy.
