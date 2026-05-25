# 🔍 FactCheck AI

A Streamlit web app for automated PDF fact-checking.

Flow:

1. Upload PDF
2. Verify claims against the live web
3. Review the verdict report

This version is designed to match the assignment more closely:

- Extracts factual claims from the uploaded PDF
- Attempts live web verification first
- Flags claims as Verified, Inaccurate, False, or Unverified
- Falls back gracefully if live search quota is unavailable

## Features

- PDF upload interface
- Server-side Gemini key only
- Live-web-first fact-check mode
- Corrected fact field for outdated or wrong claims
- JSON report download

## Modes

- `Live web fact-check`: best mode for trap documents with public stats, dates, technical claims, and company facts
- `Model-only fallback`: used when live search is unavailable but Gemini text analysis still works
- `Local fallback`: used only if AI analysis is unavailable

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

Configure the server-side key with Streamlit secrets or environment variables:

```toml
GEMINI_API_KEY = "your_key_here"
```

```bash
export GEMINI_API_KEY=your_key_here
export GEMINI_MODEL=gemini-3.5-flash
```

## Notes

- The app is strongest on public factual claims, not private resume-only claims.
- If the PDF contains personal claims like marks, CGPA, or internal project metrics with no public proof, those may appear as `Unverified`.
- For assignment evaluation, use a Gemini project with working web-search quota so the app can stay in `Live web fact-check` mode.

## Deployment

This app is ready for Streamlit Cloud style deployment:

- push the repo to GitHub
- add `GEMINI_API_KEY` in Streamlit Cloud secrets
- deploy `app.py` as the main file

## License

MIT
