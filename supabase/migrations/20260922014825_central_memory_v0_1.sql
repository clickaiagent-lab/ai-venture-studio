-- AVS Central Memory v0.1
-- Target: Supabase/Postgres
-- Scope: minimal structured memory for Campaign #001 and first AVS operating loop.

create extension if not exists pgcrypto;

create or replace function public.avs_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.avs_campaigns (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  name text not null,
  vertical text,
  objective text,
  status text not null default 'PLANNED'
    check (status in ('PLANNED','ACTIVE','PAUSED','COMPLETED','KILLED')),
  owner text,
  start_date date,
  end_date date,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.avs_opportunities (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  title text not null,
  problem_statement text not null,
  icp text,
  buyer text,
  workflow text,
  current_workaround text,
  impact text,
  lifecycle_stage text not null default 'DISCOVERED'
    check (lifecycle_stage in (
      'DISCOVERED','RESEARCHING','SHORTLISTED','VALIDATING',
      'BUILD_CANDIDATE','BUILDING','PILOT','LIVE','ARCHIVED'
    )),
  portfolio_state text not null default 'RESEARCH'
    check (portfolio_state in (
      'PRIMARY','SECONDARY','RESEARCH','PARKED','KILLED',
      'SCALE-1','SCALE-2','SCALE-3'
    )),
  opportunity_score numeric(5,2),
  score_coverage numeric(5,2),
  key_unknowns jsonb not null default '[]'::jsonb,
  owner text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.avs_experiments (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  opportunity_id uuid not null references public.avs_opportunities(id) on delete cascade,
  hypothesis_statement text not null,
  experiment_type text not null,
  method text,
  target_sample integer,
  qualified_sample_criteria jsonb,
  primary_metric text,
  baseline jsonb,
  success_threshold text,
  failure_threshold text,
  status text not null default 'DRAFT'
    check (status in ('DRAFT','READY','RUNNING','COMPLETED','STOPPED')),
  run_validity text
    check (run_validity is null or run_validity in ('VALID','INVALID','PARTIAL')),
  outcome text
    check (outcome is null or outcome in ('PASSED','FAILED','INCONCLUSIVE','INVALID_RUN','STOPPED')),
  result_summary text,
  cost numeric(12,2),
  owner text,
  start_date date,
  end_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.avs_contacts (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid references public.avs_campaigns(id) on delete set null,
  opportunity_id uuid references public.avs_opportunities(id) on delete set null,
  contact_type text not null default 'PERSON'
    check (contact_type in ('PERSON','ORGANIZATION')),
  company_name text,
  person_name text,
  role text,
  contact_reference text,
  source text,
  source_url text,
  relationship_stage text not null default 'PROSPECT'
    check (relationship_stage in (
      'PROSPECT','CONTACTED','REPLIED','INTERVIEWED','DEMO',
      'PILOT','ACTIVE_USER','PAYING','LOST'
    )),
  last_contact_at timestamptz,
  next_action text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.avs_builds (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  opportunity_id uuid not null references public.avs_opportunities(id) on delete cascade,
  experiment_id uuid references public.avs_experiments(id) on delete set null,
  version text not null default 'v0.1',
  status text not null default 'PLANNED'
    check (status in ('PLANNED','BUILDING','INTERNAL_TEST','PILOT_READY','PILOT','LIVE','ARCHIVED')),
  execution_engine text,
  product_surface text,
  build_brief_url text,
  build_packet_url text,
  repo_url text,
  deployment_url text,
  test_status text,
  pilot_ready boolean not null default false,
  cost_guardrail jsonb,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.avs_interactions (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid references public.avs_campaigns(id) on delete set null,
  contact_id uuid references public.avs_contacts(id) on delete set null,
  opportunity_id uuid references public.avs_opportunities(id) on delete set null,
  experiment_id uuid references public.avs_experiments(id) on delete set null,
  build_id uuid references public.avs_builds(id) on delete set null,
  channel text,
  interaction_type text not null,
  direction text check (direction is null or direction in ('INBOUND','OUTBOUND','INTERNAL')),
  occurred_at timestamptz not null default now(),
  summary text,
  raw_asset_url text,
  outcome text,
  evidence_candidate boolean not null default false,
  created_by_type text not null default 'HUMAN'
    check (created_by_type in ('HUMAN','AGENT','AUTOMATION','IMPORT')),
  created_by_id text,
  created_at timestamptz not null default now()
);

create table if not exists public.avs_evidence (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid references public.avs_campaigns(id) on delete set null,
  opportunity_id uuid references public.avs_opportunities(id) on delete set null,
  experiment_id uuid references public.avs_experiments(id) on delete set null,
  interaction_id uuid references public.avs_interactions(id) on delete set null,
  claim_statement text,
  evidence_purpose text,
  evidence_type text,
  direction text not null default 'NEUTRAL'
    check (direction in ('SUPPORTS','CONTRADICTS','NEUTRAL')),
  strength smallint check (strength is null or strength between 0 and 3),
  extracted_fact text not null,
  source_reference text,
  reviewed_by text,
  reviewed_at timestamptz,
  created_by_type text not null default 'HUMAN'
    check (created_by_type in ('HUMAN','AGENT','AUTOMATION','IMPORT')),
  created_by_id text,
  created_at timestamptz not null default now()
);

create table if not exists public.avs_decisions (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid references public.avs_campaigns(id) on delete set null,
  opportunity_id uuid references public.avs_opportunities(id) on delete set null,
  experiment_id uuid references public.avs_experiments(id) on delete set null,
  build_id uuid references public.avs_builds(id) on delete set null,
  decision_stage text not null,
  decision_value text not null,
  reason text not null,
  evidence_refs uuid[] not null default '{}'::uuid[],
  metric_snapshot jsonb,
  decided_by text not null,
  decided_at timestamptz not null default now(),
  next_action text,
  created_at timestamptz not null default now()
);

create table if not exists public.avs_learnings (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid references public.avs_campaigns(id) on delete set null,
  opportunity_id uuid references public.avs_opportunities(id) on delete set null,
  decision_id uuid references public.avs_decisions(id) on delete set null,
  category text,
  statement text not null,
  evidence_summary text,
  scope text,
  next_use text,
  confidence smallint check (confidence is null or confidence between 0 and 3),
  status text not null default 'ACTIVE'
    check (status in ('ACTIVE','SUPERSEDED','RETIRED')),
  supersedes_learning_id uuid references public.avs_learnings(id) on delete set null,
  review_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.avs_assets (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid references public.avs_campaigns(id) on delete set null,
  opportunity_id uuid references public.avs_opportunities(id) on delete set null,
  related_learning_id uuid references public.avs_learnings(id) on delete set null,
  asset_type text not null,
  title text not null,
  provider text,
  external_object_id text,
  canonical_location text not null,
  version text,
  status text not null default 'ACTIVE'
    check (status in ('ACTIVE','REUSABLE','PRODUCT_ONLY','ARCHIVED')),
  reusable_scope text,
  last_used_at timestamptz,
  next_use text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_avs_opportunities_campaign on public.avs_opportunities(campaign_id);
create index if not exists idx_avs_opportunities_lifecycle on public.avs_opportunities(lifecycle_stage);
create index if not exists idx_avs_experiments_opportunity on public.avs_experiments(opportunity_id);
create index if not exists idx_avs_contacts_opportunity on public.avs_contacts(opportunity_id);
create index if not exists idx_avs_contacts_stage on public.avs_contacts(relationship_stage);
create index if not exists idx_avs_builds_opportunity on public.avs_builds(opportunity_id);
create index if not exists idx_avs_interactions_contact on public.avs_interactions(contact_id);
create index if not exists idx_avs_interactions_opportunity on public.avs_interactions(opportunity_id);
create index if not exists idx_avs_interactions_occurred on public.avs_interactions(occurred_at desc);
create index if not exists idx_avs_evidence_opportunity on public.avs_evidence(opportunity_id);
create index if not exists idx_avs_evidence_experiment on public.avs_evidence(experiment_id);
create index if not exists idx_avs_decisions_opportunity on public.avs_decisions(opportunity_id);
create index if not exists idx_avs_learnings_campaign on public.avs_learnings(campaign_id);
create index if not exists idx_avs_assets_campaign on public.avs_assets(campaign_id);

drop trigger if exists trg_avs_campaigns_updated_at on public.avs_campaigns;
create trigger trg_avs_campaigns_updated_at before update on public.avs_campaigns
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_avs_opportunities_updated_at on public.avs_opportunities;
create trigger trg_avs_opportunities_updated_at before update on public.avs_opportunities
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_avs_experiments_updated_at on public.avs_experiments;
create trigger trg_avs_experiments_updated_at before update on public.avs_experiments
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_avs_contacts_updated_at on public.avs_contacts;
create trigger trg_avs_contacts_updated_at before update on public.avs_contacts
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_avs_builds_updated_at on public.avs_builds;
create trigger trg_avs_builds_updated_at before update on public.avs_builds
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_avs_learnings_updated_at on public.avs_learnings;
create trigger trg_avs_learnings_updated_at before update on public.avs_learnings
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_avs_assets_updated_at on public.avs_assets;
create trigger trg_avs_assets_updated_at before update on public.avs_assets
for each row execute function public.avs_set_updated_at();

alter table public.avs_campaigns enable row level security;
alter table public.avs_opportunities enable row level security;
alter table public.avs_experiments enable row level security;
alter table public.avs_contacts enable row level security;
alter table public.avs_builds enable row level security;
alter table public.avs_interactions enable row level security;
alter table public.avs_evidence enable row level security;
alter table public.avs_decisions enable row level security;
alter table public.avs_learnings enable row level security;
alter table public.avs_assets enable row level security;
