# ✅ FactCheck AI — Automated Truth Layer

Automated fact-checking web app that extracts claims from PDFs and verifies them against live web data.

## 🚀 How it Works
1. **Upload** any PDF (marketing docs, reports, press releases)
2. **AI Extracts** specific verifiable claims using LLaMA 3.3 70B
3. **Live Search** cross-references each claim against Google
4. **Report** flags claims as Verified / Inaccurate / False / Unverified

## 🛠 Tech Stack
- **Frontend**: Streamlit
- **LLM**: Groq (LLaMA 3.3 70B Versatile) — for claim extraction + fact reasoning
- **Search**: Serper API (Google Search)
- **PDF**: pdfplumber

---

## 🌐 Deploy on Streamlit Cloud (Free, Recommended)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "FactCheck AI app"
git remote add origin https://github.com/YOUR_USERNAME/factcheck-ai.git
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Connect your GitHub repo
4. Set **Main file path**: `app.py`
5. Under **Advanced settings → Secrets**, add:
```toml
GROQ_API_KEY = "your_groq_key_here"
SERPER_API_KEY = "your_serper_key_here"
```
6. Click **Deploy** — your live URL will be:
   `https://your-app-name.streamlit.app`

---

## 🌐 Alternative: Deploy on Render

### Option A: Web Service
1. Create account at [render.com](https://render.com)
2. New → **Web Service** → Connect GitHub repo
3. Settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Add environment variables: `GROQ_API_KEY`, `SERPER_API_KEY`
5. Deploy!

---

## 🔑 Getting API Keys

### Groq API (Free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → API Keys → Create Key

### Serper API (Free tier: 2500 searches/month)
1. Go to [serper.dev](https://serper.dev)
2. Sign up → Get API Key

---

## 🔒 Security Note
Never commit API keys directly in code. Use:
- **Streamlit Cloud**: Secrets management (TOML format)
- **Render**: Environment variables panel
- **Local**: `.env` file + python-dotenv

---

## Local Development
```bash
pip install -r requirements.txt
export GROQ_API_KEY="your_key"
export SERPER_API_KEY="your_key"
streamlit run app.py
```
