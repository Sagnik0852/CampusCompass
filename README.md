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

- [x] Supabase provisioned + schema applied (postings, companies registry, 5 analytics views)
- [x] All 4 scraper workflows live in n8n — 289 real postings collected on day one (193 Unstop, 96 Internshala)
- [x] ATS registry: 10 companies with live boards verified (Meesho, PhonePe, Slice, Groww, Dream Sports, Hevo, Atlan, CRED, Postman, Pocket FM)
- [x] LinkedIn via Google Alerts RSS wired (feeds populating); Naukri assessed & skipped — blocks server scraping, Unstop covers the segment
- [x] Telegram bot + channel live, weekly digest generating from real data
- [ ] Dashboard deployed to Streamlit Community Cloud
- [ ] Seed/demo data wiped (after first week of real data)
- [ ] 200+ digest subscribers
