# CampusCompass — Internship Market Intelligence

Students prep for internships by guessing what roles want. Nobody measures it. CampusCompass does.

**What it does:** an n8n pipeline scrapes new PM / Growth / Analyst / SWE internship postings daily (Internshala, Unstop, company careers pages via ATS APIs), Claude extracts structured fields (skills, stipend, location, YoE creep), everything lands in Supabase, and a Streamlit dashboard surfaces trends — *"PM internships mentioning SQL are up 40% this quarter"*, stipend distributions by city, skill co-occurrence. A weekly digest auto-posts to a Telegram channel.

## Stack

| Layer | Tool |
|---|---|
| Orchestration / scraping | n8n (cloud or self-hosted) |
| Structured extraction | Claude API (Haiku for cost) |
| Storage | Supabase (Postgres) |
| Dashboard | Streamlit |
| Distribution | Telegram Bot API |

## Repo layout

```
CampusCompass/
├── BUILD_GUIDE.md            ← start here: step-by-step build instructions
├── supabase/
│   └── schema.sql            # tables, indexes, analytics views
├── n8n/
│   ├── daily_scrape_extract.json   # importable workflow: Internshala scrape → Claude → Supabase
│   ├── ats_careers_scan.json       # importable workflow: company careers pages (Lever/Greenhouse/Ashby APIs) → Claude → Supabase
│   ├── unstop_scan.json            # importable workflow: Unstop public API → Claude → Supabase
│   ├── linkedin_rss_scan.json      # importable workflow: LinkedIn via Google Alerts RSS → Claude → Supabase
│   └── weekly_digest.json          # importable workflow: stats → Claude → Telegram
├── prompts/
│   ├── extraction_prompt.md  # Claude structured-extraction prompt
│   └── digest_prompt.md      # Claude weekly-digest prompt
├── dashboard/
│   ├── app.py                # Streamlit dashboard
│   └── requirements.txt
├── scripts/
│   ├── seed_sample_data.py   # generate realistic fake postings for dev/demo
│   ├── verify_companies.py   # find companies with public ATS boards → companies table
│   └── test_extraction.py    # test the Claude extraction prompt locally
└── .env.example
```

## Quick start

1. Read `BUILD_GUIDE.md` — it's ordered by weekend.
2. Copy `.env.example` → `.env`, fill in keys.
3. `pip install -r dashboard/requirements.txt`
4. `python scripts/seed_sample_data.py` (demo data so the dashboard isn't empty)
5. `streamlit run dashboard/app.py`

## Status

- [x] Supabase project provisioned + schema applied (incl. companies registry)
- [x] ATS careers-page layer: CRED (Lever) + Postman (Greenhouse) verified live; run `scripts/verify_companies.py` to grow the registry
- [x] Unstop public API verified live (~10k internships); SWE role added everywhere
- [x] LinkedIn/Naukri assessed: both block server-side scraping — LinkedIn via Google Alerts RSS instead (guide Step 9), Naukri skipped (Unstop covers student internships better)
- [ ] n8n workflows imported & credentialed
- [ ] Telegram bot + channel created
- [ ] Dashboard deployed (Streamlit Community Cloud)
- [ ] First weekly digest sent
