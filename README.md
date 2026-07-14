# 🧭 CampusCompass

**Internship market intelligence for India — measured, not guessed.**

**📊 Live dashboard: [campuscompass.streamlit.app](https://campuscompass.streamlit.app/)** · 📬 Weekly digest: [@campuscompass_digest](https://t.me/campuscompass_digest) on Telegram

Students prep for PM, Growth, Analyst, and SWE internships by guessing what roles want. Nobody measures it. CampusCompass scrapes hundreds of live internship postings daily, has Claude extract 15 structured fields from each, and turns the mess into answers: *which skills are actually rising, what stipends really look like city by city, and how much experience "intern" roles quietly demand.*

## How it works

```
 n8n (daily) ──┬─ 8:00  Internshala        (5 search pages, HTML scrape)
               ├─ 8:15  LinkedIn           (Google Alerts RSS feeds)
               ├─ 8:30  Unstop             (public JSON API, 7 role searches)
               └─ 9:00  Company careers    (registry → Lever/Greenhouse/Ashby APIs)
                          │
                dedupe vs DB → Claude Haiku extracts 15 structured fields
                          │      (skills, stipend, city, YoE asked, PPO, ...)
                          ▼
                Supabase Postgres (postings + companies registry + analytics views)
                          ├──▶ Streamlit dashboard  (public, read-only)
                          └──▶ n8n (Sun 6pm): stats → Claude Sonnet → Telegram digest
```

The careers-page layer is the differentiator: most startups run hiring on an ATS (Lever / Greenhouse / Ashby) with public JSON APIs. A registry of verified companies (Meesho, PhonePe, Groww, Slice, Dream Sports, CRED, Postman, ...) is scanned daily — internships get caught here **days before they reach portals**.

## What the dashboard answers

- **Headline movers** — "SQL mentions in PM postings up X% this quarter"
- **Skill demand over time** — weekly mention trends per skill, filterable by role
- **Stipends by city** — distribution box plots, not averages that hide the spread
- **Skills that travel together** — co-occurrence heatmap: if you're learning X, what pairs with it
- **Experience creep** — how much prior experience "intern" postings ask for, tracked over time

## Stack

| Layer | Tool |
|---|---|
| Orchestration / scraping | n8n (5 importable workflows in `n8n/`) |
| Structured extraction | Claude Haiku (temperature 0, strict JSON schema) |
| Digest writing | Claude Sonnet |
| Storage + analytics views | Supabase (Postgres, RLS: public reads only) |
| Dashboard | Streamlit + Plotly |
| Distribution | Telegram Bot API |

Running cost: ~₹100–200/month (Claude API). Everything else is free tier.

## Repo layout

```
├── BUILD_GUIDE.md              # step-by-step: rebuild this from zero in 2 weekends
├── n8n/                        # 5 importable workflows (scrapers ×4 + weekly digest)
├── supabase/schema.sql         # tables, indexes, analytics views, RLS policies
├── prompts/                    # Claude extraction + digest prompts, documented
├── dashboard/app.py            # the Streamlit dashboard
└── scripts/
    ├── seed_sample_data.py     # realistic demo data for development
    ├── test_extraction.py      # test the extraction prompt before deploying
    └── verify_companies.py     # probe companies for public ATS boards → registry
```

## Build your own

Full instructions in [`BUILD_GUIDE.md`](BUILD_GUIDE.md). Short version: create a free Supabase project, apply `supabase/schema.sql`, import the `n8n/` workflows, add three credentials (Supabase, Anthropic, Telegram), activate. The dashboard deploys free on Streamlit Community Cloud.

## Design decisions worth stealing

- **Store `raw_text` + full model output per posting** — prompt improvements can re-extract history without re-scraping.
- **Dedupe by URL *before* the LLM call** — the cheapest token is the one never spent.
- **Fragility is quarantined** — the only brittle piece (Internshala's markup) lives in one regex in one node; APIs and RSS do the rest.
- **Anon key + RLS for the public dashboard** — writes require the service key, which never leaves the pipeline.

---

Built by [Sagnik Paul](https://github.com/Sagnik0852) · data collected for educational/research use, low request volumes, no paywalled content.
