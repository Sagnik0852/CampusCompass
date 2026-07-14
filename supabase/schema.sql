-- CampusCompass schema
-- Applied to Supabase project: CampusCompass (qulaznpzslfevxjzsvwg)

create table if not exists postings (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('internshala','wellfound','linkedin','careers','unstop','other')),
  source_url text not null unique,          -- dedupe key
  scraped_at timestamptz not null default now(),
  posted_at date,                            -- date the posting went live (extracted)
  title text,
  company text,
  role_category text check (role_category in ('pm','growth','analyst','swe','other')),
  location text,                             -- raw location string
  city text,                                 -- normalized city
  is_remote boolean default false,
  stipend_min_inr integer,                   -- monthly, INR
  stipend_max_inr integer,
  duration_months numeric,
  yoe_required numeric default 0,            -- "experience creep": YoE asked of interns
  ppo_offered boolean,                       -- pre-placement offer mentioned
  skills text[] not null default '{}',       -- normalized lowercase skill tags
  perks text[] default '{}',
  raw_text text,                             -- original posting text (for re-extraction)
  extraction_model text,
  extraction_json jsonb                      -- full Claude output, for audit
);

create index if not exists idx_postings_role_date on postings (role_category, posted_at);
create index if not exists idx_postings_city on postings (city);
create index if not exists idx_postings_skills on postings using gin (skills);
create index if not exists idx_postings_scraped on postings (scraped_at);

-- ── Analytics views ───────────────────────────────────────────────

-- Skill mentions per week per role (feeds the trend chart + "SQL up 40%" claims)
create or replace view v_skill_weekly as
select
  date_trunc('week', coalesce(posted_at, scraped_at::date))::date as week,
  role_category,
  unnest(skills) as skill,
  count(*) as mentions
from postings
group by 1, 2, 3;

-- Stipend stats by city and role
create or replace view v_stipend_by_city as
select
  city,
  role_category,
  count(*) as n,
  percentile_cont(0.25) within group (order by stipend_min_inr) as p25,
  percentile_cont(0.5)  within group (order by stipend_min_inr) as median,
  percentile_cont(0.75) within group (order by stipend_min_inr) as p75,
  avg(stipend_min_inr)::int as mean
from postings
where stipend_min_inr is not null
group by 1, 2;

-- Quarter-over-quarter skill growth (the headline-stat generator)
create or replace view v_skill_qoq as
with q as (
  select
    date_trunc('quarter', coalesce(posted_at, scraped_at::date))::date as quarter,
    role_category,
    unnest(skills) as skill,
    count(*) as mentions
  from postings
  group by 1, 2, 3
)
select
  quarter, role_category, skill, mentions,
  lag(mentions) over (partition by role_category, skill order by quarter) as prev_mentions,
  round(100.0 * (mentions - lag(mentions) over (partition by role_category, skill order by quarter))
        / nullif(lag(mentions) over (partition by role_category, skill order by quarter), 0), 1) as pct_change
from q;

-- YoE creep: average experience asked from "interns", by quarter
create or replace view v_yoe_creep as
select
  date_trunc('quarter', coalesce(posted_at, scraped_at::date))::date as quarter,
  role_category,
  round(avg(yoe_required)::numeric, 2) as avg_yoe,
  count(*) as n
from postings
group by 1, 2;

-- Weekly digest source: last 7 days summary rows
create or replace view v_last7_summary as
select
  role_category,
  count(*) as new_postings,
  round(avg(stipend_min_inr))::int as avg_stipend,
  array(
    select s from (
      select unnest(skills) as s, count(*) c
      from postings p2
      where p2.role_category = p.role_category
        and p2.scraped_at > now() - interval '7 days'
      group by 1 order by c desc limit 5
    ) t
  ) as top_skills
from postings p
where scraped_at > now() - interval '7 days'
group by role_category;

-- ── Security ──────────────────────────────────────────────────────
-- RLS on; anonymous (dashboard) gets read-only, writes require service key.
alter table postings enable row level security;

create policy "public read" on postings
  for select to anon using (true);

-- ── Company registry (migration 2: careers-page / ATS scanning) ───
-- Most startups run careers pages on an ATS with a public JSON API
-- (Lever, Greenhouse, Ashby). The ATS workflow scans every active row daily.
create table if not exists companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  ats_provider text not null check (ats_provider in ('lever','greenhouse','ashby')),
  ats_slug text not null,
  active boolean not null default true,
  notes text,
  added_at timestamptz not null default now(),
  unique (ats_provider, ats_slug)
);

alter table companies enable row level security;
create policy "public read companies" on companies for select to anon using (true);

-- migrations 3+4 (already applied): role_category also allows 'swe';
-- source also allows 'careers' and 'unstop'
alter table postings drop constraint if exists postings_role_category_check;
alter table postings add constraint postings_role_category_check
  check (role_category in ('pm','growth','analyst','swe','other'));
alter table postings drop constraint if exists postings_source_check;
alter table postings add constraint postings_source_check
  check (source in ('internshala','wellfound','linkedin','careers','unstop','other'));
