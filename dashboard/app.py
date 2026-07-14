"""CampusCompass — internship market intelligence dashboard.

Run:  streamlit run dashboard/app.py
Env:  SUPABASE_URL + SUPABASE_ANON_KEY (.env or Streamlit secrets)
"""
import os
from datetime import date, timedelta
from itertools import combinations

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="CampusCompass", page_icon="🧭", layout="wide")

def _conf(key: str) -> str:
    """Streamlit secrets if present (cloud), else .env/environment (local)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:  # no secrets.toml locally — that's fine
        pass
    return os.environ.get(key, "")


SUPABASE_URL = _conf("SUPABASE_URL").rstrip("/")
ANON_KEY = _conf("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not ANON_KEY:
    st.error("Set SUPABASE_URL and SUPABASE_ANON_KEY (in .env locally, or Streamlit secrets when deployed).")
    st.stop()

ROLE_LABELS = {"pm": "Product", "growth": "Growth/Marketing", "analyst": "Analyst", "swe": "Software Engg"}


@st.cache_data(ttl=900)
def load_postings() -> pd.DataFrame:
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    cols = ("source,source_url,scraped_at,posted_at,title,company,role_category,"
            "city,is_remote,stipend_min_inr,stipend_max_inr,duration_months,"
            "yoe_required,ppo_offered,skills")
    rows, offset, page = [], 0, 1000
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/postings",
            headers={**headers, "Range": f"{offset}-{offset + page - 1}"},
            params={"select": cols, "order": "scraped_at.desc"},
            timeout=30,
        )
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["posted_at"].fillna(df["scraped_at"].str[:10]))
    df["week"] = df["date"].dt.to_period("W").dt.start_time
    df["skills"] = df["skills"].apply(lambda s: s if isinstance(s, list) else [])
    return df


df = load_postings()

st.title("🧭 CampusCompass")
st.caption("What PM / Growth / Analyst / SWE internships actually ask for — measured, not guessed. Updated daily.")

if df.empty:
    st.warning("No data yet. Run `python scripts/seed_sample_data.py` for demo data, or wait for the n8n scraper's first run.")
    st.stop()

# ── Sidebar filters ─────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    roles = st.multiselect(
        "Role", options=list(ROLE_LABELS), default=list(ROLE_LABELS),
        format_func=lambda r: ROLE_LABELS.get(r, r),
    )
    window = st.selectbox("Time window", ["Last 3 months", "Last 6 months", "All time"], index=1)
    st.divider()
    st.caption(f"{len(df):,} postings tracked · latest: {df['date'].max():%d %b %Y}")

cutoff = {"Last 3 months": 90, "Last 6 months": 180, "All time": 10_000}[window]
f = df[df["role_category"].isin(roles) & (df["date"] >= pd.Timestamp(date.today() - timedelta(days=cutoff)))]

if f.empty:
    st.warning("No postings match the current filters.")
    st.stop()

# ── KPI row ─────────────────────────────────────────────────────
this_week = f[f["date"] >= pd.Timestamp(date.today() - timedelta(days=7))]
paid = f[f["stipend_min_inr"].notna() & (f["stipend_min_inr"] > 0)]
top_skill = f.explode("skills")["skills"].mode()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Postings (window)", f"{len(f):,}")
c2.metric("New this week", f"{len(this_week):,}")
c3.metric("Median stipend", f"₹{int(paid['stipend_min_inr'].median()):,}/mo" if len(paid) else "—")
c4.metric("Most-asked skill", top_skill.iloc[0] if len(top_skill) else "—")

# ── Headline movers (the "SQL up 40%" generator) ────────────────
st.subheader("📈 Headline movers")
half = f["date"].min() + (f["date"].max() - f["date"].min()) / 2
ex = f.explode("skills").dropna(subset=["skills"])
recent = ex[ex["date"] >= half]["skills"].value_counts()
earlier = ex[ex["date"] < half]["skills"].value_counts()
movers = (
    pd.DataFrame({"recent": recent, "earlier": earlier}).fillna(0)
    .query("recent + earlier >= 10")
    .assign(pct=lambda d: (d["recent"] - d["earlier"]) / d["earlier"].clip(lower=1) * 100)
    .sort_values("pct", key=abs, ascending=False).head(6)
)
if movers.empty:
    st.info("Not enough data yet for trend claims.")
else:
    mcols = st.columns(min(3, len(movers)))
    for i, (skill, row) in enumerate(movers.iterrows()):
        arrow = "▲" if row["pct"] >= 0 else "▼"
        mcols[i % len(mcols)].metric(
            skill, f"{int(row['recent'])} mentions",
            f"{arrow} {abs(row['pct']):.0f}% vs earlier period",
            delta_color="normal" if row["pct"] >= 0 else "inverse",
        )

# ── Skill trends over time ──────────────────────────────────────
st.subheader("Skill demand over time")
weekly = ex.groupby(["week", "skills"]).size().reset_index(name="mentions")
top_n = ex["skills"].value_counts().head(8).index.tolist()
pick = st.multiselect("Skills to plot", sorted(ex["skills"].unique()), default=top_n[:5])
if pick:
    fig = px.line(
        weekly[weekly["skills"].isin(pick)], x="week", y="mentions", color="skills",
        labels={"week": "", "mentions": "mentions / week", "skills": "skill"},
    )
    fig.update_layout(height=380, legend_title=None)
    st.plotly_chart(fig, use_container_width=True)

# ── Stipends ────────────────────────────────────────────────────
st.subheader("💰 Stipends by city")
sc = paid[paid["city"].notna()]
if len(sc) >= 10:
    order = sc.groupby("city")["stipend_min_inr"].median().sort_values(ascending=False).index
    fig = px.box(
        sc, x="city", y="stipend_min_inr", color="role_category",
        category_orders={"city": list(order)},
        labels={"stipend_min_inr": "monthly stipend (INR)", "city": "", "role_category": "role"},
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough paid postings with city data yet.")

# ── Skill co-occurrence ─────────────────────────────────────────
st.subheader("🔗 Skills that travel together")
top_co = ex["skills"].value_counts().head(12).index.tolist()
pairs = {}
for sk in f["skills"]:
    for a, b in combinations(sorted(set(sk) & set(top_co)), 2):
        pairs[(a, b)] = pairs.get((a, b), 0) + 1
if pairs:
    mat = pd.DataFrame(0, index=top_co, columns=top_co)
    for (a, b), n in pairs.items():
        mat.loc[a, b] = n
        mat.loc[b, a] = n
    fig = px.imshow(mat, text_auto=True, color_continuous_scale="Blues", aspect="auto")
    fig.update_layout(height=460, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Read: if you're learning the row skill, the darkest column is the highest-leverage pairing.")

# ── YoE creep ───────────────────────────────────────────────────
st.subheader("📊 Experience creep")
st.caption("Average years of prior experience asked of *interns*, by month.")
yoe = f.assign(month=f["date"].dt.to_period("M").dt.start_time).groupby(["month", "role_category"])["yoe_required"].mean().reset_index()
fig = px.line(
    yoe, x="month", y="yoe_required", color="role_category",
    labels={"month": "", "yoe_required": "avg YoE asked", "role_category": "role"},
)
fig.update_layout(height=320)
st.plotly_chart(fig, use_container_width=True)

# ── Raw explorer ────────────────────────────────────────────────
with st.expander("🔍 Browse raw postings"):
    show = f[["date", "title", "company", "role_category", "city", "stipend_min_inr",
              "stipend_max_inr", "skills", "source", "source_url"]].sort_values("date", ascending=False)
    st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()
st.caption("Built by Sagnik · data scraped daily via n8n, structured by Claude, stored in Supabase. "
           "Weekly digest → Telegram: @YOUR_CHANNEL_USERNAME")
