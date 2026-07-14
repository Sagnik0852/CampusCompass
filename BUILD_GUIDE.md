# CampusCompass — Build Guide

Last updated: 13 Jul 2026. Reflects the current state of the repo — everything buildable without your logins is already done. This guide is now purely **what you do next, in order**.

---

## ✅ Already done (nothing to redo)

| What | Detail |
|---|---|
| Supabase project | **CampusCompass**, org Sagnik0852's Org, region ap-south-1 (Mumbai), free tier. URL: `https://qulaznpzslfevxjzsvwg.supabase.co` |
| Database schema | `postings` table (15 fields), `companies` registry, 5 analytics views, RLS (public = read-only). 4 migrations applied. Reference copy: `supabase/schema.sql` — do NOT re-run it |
| Sources verified live | Internshala (5 search pages), Unstop public API (~10k internships), CRED (Lever) + Postman (Greenhouse) careers boards, your 4 Google Alerts RSS feeds |
| Roles covered | PM, Growth/Marketing, Analyst, **SWE** |
| 5 n8n workflows | Written, validated, LinkedIn feeds already wired in. Only credentials need attaching after import |
| Dashboard, prompts, scripts | `dashboard/app.py`, extraction/digest prompts, seed/test/verify scripts — all syntax-checked |
| Ruled out | LinkedIn direct scraping & Naukri (both block servers). LinkedIn goes via your RSS feeds instead |

Your total remaining work: **~2 hours**, split into 9 steps. Steps 1–7 get the whole pipeline live; 8–9 make it public.

---

## Step 1 · API keys → .env (~15 min)

1. **Anthropic key**: [console.anthropic.com](https://console.anthropic.com) → API Keys → Create. Add **$5 credit** (Billing) — extraction runs on Haiku; this lasts months.
2. **Supabase service key**: [supabase.com/dashboard](https://supabase.com/dashboard) → **CampusCompass** project → Project Settings → API Keys → copy the **service_role (secret)** key. This bypasses row security: never commit it, never use it in the dashboard.
3. In the project folder:
   ```bash
   cd ~/CampusCompass
   cp .env.example .env
   ```
   Open `.env`, fill in `ANTHROPIC_API_KEY` and `SUPABASE_SERVICE_KEY`. (`SUPABASE_URL` and the anon key are already filled in.)

## Step 2 · Test the extraction prompt (~10 min)

```bash
cd ~/CampusCompass
python3 -m venv .venv        # macOS has no bare "python" — use python3 here
source .venv/bin/activate    # after this, plain "python" works (inside the venv)
pip install anthropic requests python-dotenv
python scripts/test_extraction.py
```

Note: run everything from the `CampusCompass` folder, and re-run `source .venv/bin/activate` in any new terminal window before using `python`.

Expected: clean JSON with `stipend_min_inr: 20000`, `skills` containing `sql`/`figma`/`a/b testing`, `yoe_required: 0.5`. If it drifts, tune `prompts/extraction_prompt.md` (the same prompt lives in each workflow's "Build Claude request" node).

## Step 3 · Seed demo data + dashboard locally (~10 min)

Don't wait days for real data — the seed has realistic trends baked in (SQL rising in PM, "ai tools" climbing, SWE at ₹28k median) so every chart demos properly:

```bash
pip install -r dashboard/requirements.txt
python scripts/seed_sample_data.py
streamlit run dashboard/app.py
```

Check: 4 roles in the sidebar filter, headline movers showing % changes, stipend box plots.

## Step 4 · n8n account + credentials (~20 min)

1. Sign up at [n8n.io](https://n8n.io) (cloud free trial — decide later between paid cloud ~$20/mo or self-hosting on Railway ~$5/mo).
2. Create **3 credentials** (sidebar → Credentials → Add). **Names must match exactly** — the workflows reference them by name:

| Type | Name (exact) | Values |
|---|---|---|
| Supabase API | `Supabase CampusCompass` | Host: `https://qulaznpzslfevxjzsvwg.supabase.co` · Key: your **service_role** key |
| Header Auth | `Anthropic x-api-key` | Header name: `x-api-key` · Value: your Anthropic key |
| Telegram API | `CampusCompass Bot` | Bot token — created in Step 6 (do this credential last) |

## Step 5 · Import + activate the 4 scraper workflows (~30 min)

Import each file (Workflows → ⋯ → Import from File), open any node with a ⚠️ credential warning and select the matching credential, **test-run manually** ("Execute workflow"), then **activate** (toggle top-right).

| Workflow file | Schedule | Test-run success looks like |
|---|---|---|
| `daily_scrape_extract.json` (Internshala) | 8:00 daily | ~25 links per search page parsed → new rows in Supabase → Table Editor → postings |
| `unstop_scan.json` | 8:30 daily | 7 API calls → dozens of open internships → rows with `source='unstop'` |
| `linkedin_rss_scan.json` | 8:15 daily | Your 4 feeds read. **Zero items is normal for the first days** — new alerts populate as Google indexes postings |
| `ats_careers_scan.json` | 9:00 daily | CRED + Postman boards fetched; intern-matching postings inserted (may be 0 — big companies don't always have open internships) |

Troubleshooting:
- **Internshala "Parse posting links" returns 0** → markup changed or bot-check page. Look at "Fetch search page" output HTML, adjust the one regex in that node. Deliberately the only fragile spot.
- **Supabase insert errors** → check the credential uses the **service_role** key, not anon.
- **Claude node 401** → header name must be exactly `x-api-key`.

## Step 6 · Telegram bot + weekly digest (~20 min)

1. In Telegram: **@BotFather** → `/newbot` → e.g. "CampusCompass Digest Bot" → save the token.
2. Create a **public channel** (e.g. `@campuscompass_digest`) → add your bot as **admin** with post permission.
3. In n8n: create the `CampusCompass Bot` Telegram credential with the token.
4. Import `weekly_digest.json`, attach all 3 credentials, open **"Send to Telegram"** and set `chatId` to your channel username.
5. Test-run — with seeded data you get a real digest in the channel immediately. Activate (Sundays 6pm).

## Step 7 · Grow the ATS company registry (~15 min)

```bash
python scripts/verify_companies.py --dry-run   # probe ~45 Indian startups, look first
python scripts/verify_companies.py             # write hits to Supabase
python scripts/verify_companies.py "Atlan" "Jar"   # probe any company you care about
```

Expect roughly a third to have public boards (Lever/Greenhouse/Ashby); Keka/Darwinbox companies get skipped. The ATS workflow picks up new registry rows automatically on its next run. Add companies your seniors interned at.

**Pipeline is now fully live.** Give it ~1 week of real data, then:

## Step 8 · Deploy the dashboard publicly (~30 min)

1. Push the folder to GitHub (public is fine — `.gitignore` excludes `.env`; double-check no service key is committed).
2. [share.streamlit.io](https://share.streamlit.io) → New app → your repo → main file: `dashboard/app.py`.
3. App settings → Secrets:
   ```toml
   SUPABASE_URL = "https://qulaznpzslfevxjzsvwg.supabase.co"
   SUPABASE_ANON_KEY = "<anon key from .env.example>"
   ```
   Anon key only — it's read-only by design.
4. Put the resulting `*.streamlit.app` link in the Telegram channel description.

## Step 9 · Swap seed data for real data (~2 min)

After ~2 weeks of real scraping:
```bash
python scripts/seed_sample_data.py --wipe
```

---

## Distribution playbook (the actual growth story)

The resume line is "200+ subscribers", not "built a scraper":

1. **Week 1**: drop the channel in batch/placement-prep groups with ONE surprising stat screenshot ("median growth-intern stipend in Bangalore is ₹17k"). Numbers travel; "check out my project" doesn't.
2. **Every digest** ends with the dashboard link + "forward to one friend prepping for internships".
3. **Monthly**: one LinkedIn analysis post from the data ("What 800 internship postings say about the SWE skills gap") linking the channel — doubles as recruiter bait.
4. Track subscriber count weekly; the growth curve is itself an interview artifact.

## Maintenance (as needed)

- **n8n error alerts**: Settings → Error Workflow → a 2-node workflow that Telegrams *you* on failure, so a silent breakage doesn't cost a month of data.
- **Extraction QA**: monthly, sample 10 rows, compare `extraction_json` vs `raw_text`. Prompt fixes are free — re-extract from stored `raw_text` without re-scraping.
- **LinkedIn feeds dry after a week?** Loosen alert queries (drop `India` or a quoted phrase) at google.com/alerts.
- **DB size**: free tier = 500MB; `raw_text` is the heavy column (~5KB/posting → fine to ~50k postings). Null out `raw_text` older than 6 months if needed.

## Costs

| Item | Cost |
|---|---|
| Supabase free tier | ₹0 |
| Claude API (Haiku extraction ~50–80 postings/day + 1 Sonnet digest/week) | ~₹100–200/mo |
| n8n | ₹0 self-host · ~₹450/mo Railway · n8n cloud pricing |
| Streamlit Community Cloud · Telegram | ₹0 |

## Architecture

```
 n8n daily ──┬─ 8:00  Internshala (5 search pages, HTML scrape)
             ├─ 8:15  LinkedIn (your 4 Google Alerts RSS feeds)
             ├─ 8:30  Unstop (public JSON API, 7 role searches)
             └─ 9:00  Careers pages (companies table → Lever/Greenhouse/Ashby APIs)
                        │
              dedupe vs DB → Claude Haiku (JSON extraction, 15 fields)
                        │
                    Supabase (postings + companies + 5 views, RLS)
                        ├──▶ Streamlit dashboard (anon key, read-only)
                        └──▶ n8n Sun 6pm: stats → Claude Sonnet → Telegram channel
```

## Resume bullets (fill in real numbers)

- Built a labor-market intelligence pipeline (n8n · Claude · Supabase · Streamlit) tracking N internship postings/month across PM/Growth/Analyst/SWE roles from 4 source types — portals, Unstop's API, LinkedIn RSS, and company careers pages via ATS APIs (Lever/Greenhouse/Ashby); automated LLM extraction of 15 structured fields at >95% parse rate.
- Grew a weekly data digest to N subscribers in my batch; dashboard surfaced findings like "X% rise in SQL requirements for PM internships in one quarter".
